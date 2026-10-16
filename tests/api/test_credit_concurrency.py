"""Real PostgreSQL transaction schedules for isolated synthetic accounting."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from credits import services
from credits.models import Finalization, GlobalDay, LedgerEntry, Operation, SavedOutput, Wallet
from django.db import connections
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, digest

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def credit_policy(settings):
    settings.LOCAL = True
    services.initialize_policy()


def student():
    user = Account.objects.create(
        email=f"credit-race-{uuid.uuid4()}@example.invalid",
        birth_date=date(2000, 1, 1),
        locale="en",
        state="ACTIVE",
        email_verified_at=timezone.now(),
    )
    services.grant_signup(user.pk)
    return user


def race(*actions):
    barrier = Barrier(len(actions))

    def run(action):
        try:
            connections.close_all()
            barrier.wait(timeout=15)
            return action()
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(run, actions))


def reserve(user, *, service="MATCHING_AI", key=None, fixture=None):
    return services.reserve(
        user.pk,
        service,
        key or str(uuid.uuid4()),
        fixture or services.create_synthetic_input(user.pk),
    )


def witness(operation):
    return {"fixture_id": str(operation.fixture_id), "result": "SYNTHETIC_OK"}


def policy_command(**changes):
    current = services.initialize_policy()
    admin = Account.objects.create(
        email=f"credit-policy-{uuid.uuid4()}@example.invalid",
        birth_date=date(2000, 1, 1),
        state="ACTIVE",
        email_verified_at=timezone.now(),
        role="ADMIN",
        admin_scopes=["COST_POLICY"],
    )
    proof = IdentitySession.objects.create(
        account=admin,
        digest=digest(str(uuid.uuid4())),
        epoch=admin.session_epoch,
        expires_at=timezone.now() + timedelta(hours=1),
        mfa_verified_at=timezone.now(),
    )
    data = {
        **{name: getattr(current, name) for name in services.POLICY_FIELDS},
        **changes,
        "reason": "Synthetic concurrent policy command.",
    }
    return lambda: services.publish_policy(admin, proof, data, current.version)


def test_two_connections_cannot_double_grant():
    user = Account.objects.create(
        email="credit-grant-race@example.invalid",
        birth_date=date(2000, 1, 1),
        state="ACTIVE",
        email_verified_at=timezone.now(),
    )
    outcomes = race(
        lambda: services.grant_signup(user.pk).pk,
        lambda: services.grant_signup(user.pk).pk,
    )
    assert outcomes[0] == outcomes[1]
    wallet = Wallet.objects.get(owner=user)
    assert wallet.posted_balance == 30 and wallet.reserved_balance == 0
    assert LedgerEntry.objects.filter(owner=user, kind="SIGNUP_GRANT").count() == 1


def test_duplicate_requests_under_two_connections_create_one_operation():
    user = student()
    fixture, key = services.create_synthetic_input(user.pk), str(uuid.uuid4())
    outcomes = race(
        lambda: reserve(user, key=key, fixture=fixture).pk,
        lambda: reserve(user, key=key, fixture=fixture).pk,
    )
    assert outcomes[0] == outcomes[1]
    operation = Operation.objects.get(owner=user)
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    assert GlobalDay.objects.get(day=operation.captured_day).admitted_operations == 1


def test_competing_document_reservations_cannot_bypass_daily_cap():
    user = student()
    fixtures = [services.create_synthetic_input(user.pk) for _ in range(2)]
    outcomes = race(
        lambda: reserve(user, service="DOCUMENT_NEW", fixture=fixtures[0]).pk,
        lambda: reserve(user, service="DOCUMENT_NEW", fixture=fixtures[1]).pk,
    )
    assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
    assert Operation.objects.filter(owner=user).count() == 1
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (30, 6)


def test_global_limit_serializes_distinct_students_without_cross_tenant_mutation():
    policy_command(global_ai_cap=1)()
    one, two = student(), student()
    fixtures = [services.create_synthetic_input(user.pk) for user in [one, two]]
    outcomes = race(
        lambda: reserve(one, fixture=fixtures[0]).pk,
        lambda: reserve(two, fixture=fixtures[1]).pk,
    )
    assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
    operation = Operation.objects.get()
    assert GlobalDay.objects.get(day=operation.captured_day).admitted_operations == 1
    assert sorted(Wallet.objects.values_list("reserved_balance", flat=True)) == [0, 1]
    assert list(Wallet.objects.values_list("posted_balance", flat=True)) == [30, 30]


def test_concurrent_same_key_different_body_does_not_rebind_request():
    user = student()
    fixtures = [services.create_synthetic_input(user.pk) for _ in range(2)]
    key = str(uuid.uuid4())
    outcomes = race(
        lambda: reserve(user, key=key, fixture=fixtures[0]).pk,
        lambda: reserve(user, key=key, fixture=fixtures[1]).pk,
    )
    assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
    assert Operation.objects.filter(owner=user).count() == 1
    assert Wallet.objects.get(owner=user).reserved_balance == 1


def test_two_finalizers_debit_and_save_output_once():
    user = student()
    operation = reserve(user, service="CV_EXTRACTION")
    token = services.claim(user.pk, operation.pk)
    outcomes = race(
        lambda: services.settle(user.pk, operation.pk, token, witness(operation)).state,
        lambda: services.settle(user.pk, operation.pk, token, witness(operation)).state,
    )
    assert outcomes == ["SETTLED", "SETTLED"]
    assert SavedOutput.objects.filter(operation=operation).count() == 1
    assert Finalization.objects.filter(operation=operation).count() == 1
    assert LedgerEntry.objects.get(operation=operation, kind="DEBIT").amount == -4
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (26, 0)


def test_two_failure_releases_return_reservation_once_without_minting_credit():
    user = student()
    operation = reserve(user, service="DOCUMENT_NEW")
    token = services.claim(user.pk, operation.pk)
    outcomes = race(
        lambda: services.fail(user.pk, operation.pk, token).state,
        lambda: services.fail(user.pk, operation.pk, token).state,
    )
    assert outcomes == ["RELEASED", "RELEASED"]
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (30, 0)
    assert Finalization.objects.filter(operation=operation).count() == 1
    assert not LedgerEntry.objects.filter(operation=operation).exists()
    assert GlobalDay.objects.get(day=operation.captured_day).admitted_operations == 1


def test_settle_versus_failure_has_exactly_one_terminal_outcome():
    user = student()
    operation = reserve(user, service="CV_EXTRACTION")
    token = services.claim(user.pk, operation.pk)
    race(
        lambda: services.settle(user.pk, operation.pk, token, witness(operation)).state,
        lambda: services.fail(user.pk, operation.pk, token).state,
    )
    operation.refresh_from_db()
    final = Finalization.objects.get(operation=operation)
    wallet = Wallet.objects.get(owner=user)
    assert wallet.reserved_balance == 0
    assert final.outcome == operation.state
    if operation.state == "SETTLED":
        assert wallet.posted_balance == 26
        assert LedgerEntry.objects.filter(operation=operation, kind="DEBIT").count() == 1
        assert SavedOutput.objects.filter(operation=operation).count() == 1
    else:
        assert operation.state == "RELEASED" and wallet.posted_balance == 30
        assert not LedgerEntry.objects.filter(operation=operation).exists()
        assert not SavedOutput.objects.filter(operation=operation).exists()


def test_timeout_versus_settlement_never_releases_or_double_debits():
    user = student()
    operation = reserve(user)
    token = services.claim(user.pk, operation.pk)
    race(
        lambda: services.settle(user.pk, operation.pk, token, witness(operation)).state,
        lambda: services.mark_uncertain(user.pk, operation.pk, token).state,
    )
    operation.refresh_from_db()
    wallet = Wallet.objects.get(owner=user)
    assert operation.state in {"SETTLED", "RECONCILING"}
    if operation.state == "SETTLED":
        assert (wallet.posted_balance, wallet.reserved_balance) == (29, 0)
        assert LedgerEntry.objects.filter(operation=operation).count() == 1
    else:
        assert (wallet.posted_balance, wallet.reserved_balance) == (30, 1)
        assert not LedgerEntry.objects.filter(operation=operation).exists()


def test_price_policy_publication_race_captures_one_complete_immutable_price():
    user = student()
    fixture = services.create_synthetic_input(user.pk)
    publish = policy_command(matching_price=2)
    outcomes = race(
        lambda: publish().pk,
        lambda: reserve(user, fixture=fixture).pk,
    )
    assert all(isinstance(value, uuid.UUID) for value in outcomes)
    operation = Operation.objects.get(owner=user)
    assert operation.price in {1, 2}
    assert operation.price == operation.policy.matching_price
    captured_price = operation.price
    token = services.claim(user.pk, operation.pk)
    services.settle(user.pk, operation.pk, token, witness(operation))
    assert LedgerEntry.objects.get(operation=operation).amount == -captured_price
    assert Wallet.objects.get(owner=user).posted_balance == 30 - captured_price
    assert reserve(user).price == 2


def test_global_cap_policy_race_never_resets_count_or_admits_under_lowered_cap():
    policy_command(global_ai_cap=2)()
    one, two = student(), student()
    first = reserve(one)
    fixture = services.create_synthetic_input(two.pk)
    lower = policy_command(global_ai_cap=1)
    race(lambda: lower().pk, lambda: reserve(two, fixture=fixture).pk)
    current = services.initialize_policy()
    assert current.global_ai_cap == 1 and current.version == 3
    operations = list(Operation.objects.all())
    assert len(operations) in {1, 2}
    assert all(operation.policy.version < current.version for operation in operations)
    assert GlobalDay.objects.get(day=first.captured_day).admitted_operations == len(operations)
    with pytest.raises(IdentityError) as failure:
        reserve(two)
    assert failure.value.code == "GLOBAL_AI_CAP"
    assert GlobalDay.objects.get(day=first.captured_day).admitted_operations == len(operations)


def test_competing_policy_edits_use_compare_and_swap_instead_of_last_writer_wins():
    from credits.models import CreditPolicy

    one, two = policy_command(matching_price=2), policy_command(matching_price=3)
    outcomes = race(lambda: one().pk, lambda: two().pk)
    assert sum(isinstance(value, uuid.UUID) for value in outcomes) == 1
    assert outcomes.count("STALE_REVISION") == 1
    assert CreditPolicy.objects.count() == 2
    assert services.initialize_policy().matching_price in {2, 3}
