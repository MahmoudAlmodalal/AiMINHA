"""Real PostgreSQL schedules, with every provider call a local synthetic mock."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier, Event
from types import SimpleNamespace

import pytest
from ai_gateway import services
from ai_gateway.adapters import MockAdapter
from ai_gateway.models import (
    Attempt,
    GatewayRequest,
    GatewayResult,
    ProviderApproval,
    ProviderCircuit,
)
from credits import services as credits
from credits.models import GlobalDay, LedgerEntry, Operation, Wallet
from django.db import connections, transaction
from django.utils import timezone
from identity.security import IdentityError
from privacy.models import Disclosure
from privacy.services import record_consent
from test_ai_gateway import config, prepared, student

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def gateway_settings(settings):
    settings.LOCAL = True
    credits.initialize_policy()


def race(*actions):
    start = Barrier(len(actions))

    def worker(action):
        try:
            connections.close_all()
            start.wait(timeout=15)
            return action()
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(worker, actions))


def execute(user, request, mock):
    return services.run(user.pk, request.pk, {"MOCK": mock}).state


class PausedMock(MockAdapter):
    """Pause outside database locks to schedule revocation or worker fencing."""

    def __init__(self):
        super().__init__()
        self.dispatched, self.resume = Event(), Event()

    def execute(self, request, timeout_seconds):
        assert not connections["default"].in_atomic_block
        self.dispatched.set()
        assert self.resume.wait(timeout=15), "Synthetic test callback was not resumed"
        return super().execute(request, timeout_seconds)


def background(pool, user, request, mock):
    def worker():
        try:
            connections.close_all()
            return execute(user, request, mock)
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    return pool.submit(worker)


def test_duplicate_workers_cannot_dispatch_or_debit_the_same_operation_twice():
    user = student()
    request = prepared(user)
    mock = MockAdapter()
    race(lambda: execute(user, request, mock), lambda: execute(user, request, mock))
    assert mock.calls == 1
    assert GatewayRequest.objects.get(pk=request.pk).state == "SETTLED"
    assert Attempt.objects.filter(request=request).count() == 1
    assert GatewayResult.objects.filter(request=request).count() == 1
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").count() == 1
    assert GlobalDay.objects.get().admitted_operations == 1
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (29, 0)


def test_two_students_competing_for_last_request_cannot_overrun_capacity():
    one, two = student(), student()
    route = config(quota_changes={"hard_limit": 1})
    requests = [prepared(one, [route]), prepared(two, [route])]
    mock = MockAdapter()
    race(
        lambda: execute(one, requests[0], mock),
        lambda: execute(two, requests[1], mock),
    )
    assert mock.calls == 1
    assert GatewayRequest.objects.filter(state="SETTLED").count() == 1
    assert LedgerEntry.objects.filter(kind="DEBIT").count() == 1
    assert GlobalDay.objects.get().admitted_operations == 2
    route.quota.refresh_from_db()
    assert route.quota.consumed == 1 and route.quota.reserved == 0
    assert sorted(Wallet.objects.values_list("posted_balance", flat=True)) == [29, 30]


def test_cloudflare_shared_account_last_neuron_is_atomic_across_students_and_models():
    one, two = student(), student()
    primary = config(provider="CLOUDFLARE", quota_changes={"observed_used": 7999})
    second = config(provider="CLOUDFLARE", model="second-approved-model", quota=primary.quota)
    first_request, second_request = prepared(one, [primary]), prepared(two, [second])
    tokens = []
    for user, request in [(one, first_request), (two, second_request)]:
        with transaction.atomic():
            tokens.append(credits.claim(user.pk, request.operation_id))
            request.state = "RUNNING"
            request.save(update_fields=["state"])
    results = race(
        lambda: services.reserve_capacity(primary.pk, first_request.pk, 1, tokens[0]).pk,
        lambda: services.reserve_capacity(second.pk, second_request.pk, 1, tokens[1]).pk,
    )
    assert sum(isinstance(value, uuid.UUID) for value in results) == 1
    primary.quota.refresh_from_db()
    assert primary.quota.observed_used + primary.quota.reserved + primary.quota.consumed == 8000
    assert Attempt.objects.count() == 1
    assert not LedgerEntry.objects.filter(kind="DEBIT").exists()


def test_revocation_before_intent_prevents_dispatch_after_preparation():
    user = student()
    route = config()
    request = prepared(user, [route])
    ProviderApproval.objects.filter(pk=route.approval_id).update(revoked_at=timezone.now())
    mock = MockAdapter()
    race(lambda: execute(user, request, mock), lambda: execute(user, request, mock))
    assert mock.calls == 0
    assert not Attempt.objects.filter(request=request).exists()
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()


def test_consent_withdrawal_after_intent_prevents_acceptance_without_promising_recall():
    user = student()
    notice = Disclosure.objects.create(
        purpose="PERSONAL_AI",
        version=1,
        available=False,
        disclosure="Synthetic unavailable notice.",
    )
    request = prepared(user)
    mock = PausedMock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = background(pool, user, request, mock)
        try:
            assert mock.dispatched.wait(timeout=15)
            assert Attempt.objects.get(request=request).state == "DISPATCH_INTENT"
            # Completing while the adapter waits proves no network work holds
            # the account/consent database lock.
            result = record_consent(
                SimpleNamespace(
                    user=user,
                    headers={"If-Match": '"consent-0"'},
                    correlation_id=uuid.uuid4(),
                ),
                notice.pk,
                "REVOKE",
            )
            assert result["state"] == "REVOKED"
        finally:
            mock.resume.set()
        pending.result(timeout=15)
    assert mock.calls == 1
    assert GatewayRequest.objects.get(pk=request.pk).state == "RECONCILING"
    assert Operation.objects.get(pk=request.operation_id).state == "RECONCILING"
    assert not GatewayResult.objects.filter(request=request).exists()
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (30, 1)


def test_approval_revocation_during_an_inflight_mock_cannot_commit_billable_output():
    user, route = student(), config()
    request = prepared(user, [route])
    mock = PausedMock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = background(pool, user, request, mock)
        try:
            assert mock.dispatched.wait(timeout=15)
            ProviderApproval.objects.filter(pk=route.approval_id).update(revoked_at=timezone.now())
        finally:
            mock.resume.set()
        pending.result(timeout=15)
    assert GatewayRequest.objects.get(pk=request.pk).state == "RECONCILING"
    assert not GatewayResult.objects.filter(request=request).exists()
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()


@pytest.mark.parametrize(
    "changed",
    [
        {"email_verified_at": None},
        {"role": "ADMIN"},
        {"birth_date": date(2015, 1, 1)},
        {"state": "SUSPENDED"},
        {"state": "DELETION_PENDING"},
    ],
)
def test_owner_authority_changed_during_send_retains_funds_without_acceptance(changed):
    from identity.models import Account

    user, route = student(), config()
    request = prepared(user, [route])
    mock = PausedMock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = background(pool, user, request, mock)
        try:
            assert mock.dispatched.wait(timeout=15)
            Account.objects.filter(pk=user.pk).update(**changed)
        finally:
            mock.resume.set()
        pending.result(timeout=15)
    assert GatewayRequest.objects.get(pk=request.pk).state == "RECONCILING"
    assert Attempt.objects.get(request=request).state == "UNKNOWN"
    assert not GatewayResult.objects.filter(request=request).exists()
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (30, 1)


def test_expired_dispatch_lease_fences_a_late_success_and_retains_allowance():
    user, route = student(), config()
    request = prepared(user, [route])
    mock = PausedMock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = background(pool, user, request, mock)
        try:
            assert mock.dispatched.wait(timeout=15)
            attempt = Attempt.objects.get(request=request)
            assert services.expire_attempts(now=attempt.lease_until) == 1
        finally:
            mock.resume.set()
        pending.result(timeout=15)
    assert GatewayRequest.objects.get(pk=request.pk).state == "RECONCILING"
    assert Attempt.objects.get(request=request).state == "UNKNOWN"
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()
    route.quota.refresh_from_db()
    assert route.quota.reserved == 1 and route.quota.blocked_reason
    assert Wallet.objects.get(owner=user).reserved_balance == 1


def test_half_open_circuit_permits_only_one_concurrent_probe():
    user = student()
    route = config()
    # First operation contributes two failures, second one reaches threshold.
    for _ in range(2):
        request = prepared(user, [route])
        execute(user, request, MockAdapter(("UNAVAILABLE",) * 5))
    circuit = ProviderCircuit.objects.get()
    assert circuit.open_until is not None
    ProviderCircuit.objects.filter(pk=circuit.pk).update(
        open_until=timezone.now() - timedelta(seconds=1), probe_until=None
    )
    other = student()
    first, second = prepared(user, [route]), prepared(other, [route])
    mock = PausedMock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = background(pool, user, first, mock)
        try:
            assert mock.dispatched.wait(timeout=15)
            try:
                execute(other, second, mock)
            except IdentityError:
                pass
            assert Attempt.objects.filter(state="DISPATCH_INTENT").count() == 1
        finally:
            mock.resume.set()
        pending.result(timeout=15)
    assert mock.calls == 1
    assert GatewayRequest.objects.filter(pk__in=[first.pk, second.pk], state="SETTLED").count() == 1
