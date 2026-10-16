"""Credit accounting uses authored synthetic witnesses; no AI/provider is called."""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from credits import services
from credits.models import (
    CreditPolicy,
    Finalization,
    GlobalDay,
    Hold,
    LedgerEntry,
    Operation,
    SavedOutput,
    StudentDay,
    Wallet,
)
from django.db import DatabaseError, connection, transaction
from django.db.models import Sum
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, digest
from identity.services import issue, verify_email
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-credit-passphrase-529!"  # noqa: S105 -- authored public fixture.


@pytest.fixture(autouse=True)
def credit_settings(settings):
    settings.LOCAL = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]
    services.initialize_policy()


def account(*, role="STUDENT", grant=True, **changes):
    user = Account.objects.create_user(
        f"credits-{uuid.uuid4()}@example.invalid",
        PASSWORD,
        **{
            "birth_date": date(2000, 1, 1),
            "locale": "en",
            "state": "ACTIVE",
            "email_verified_at": timezone.now(),
            "role": role,
            **changes,
        },
    )
    if grant:
        services.grant_signup(user.pk)
    return user


def reserve(user, service="MATCHING_AI", *, key=None, input_id=None):
    fixture = input_id or services.create_synthetic_input(user.pk)
    return services.reserve(user.pk, service, key or str(uuid.uuid4()), fixture)


def payload(operation):
    return {"fixture_id": str(operation.fixture_id), "result": "SYNTHETIC_OK"}


def balances(user):
    wallet = Wallet.objects.get(owner=user)
    return wallet.posted_balance, wallet.reserved_balance


def conserved(user):
    posted, reserved = balances(user)
    assert posted == (
        LedgerEntry.objects.filter(owner=user).aggregate(value=Sum("amount"))["value"] or 0
    )
    assert reserved == (
        Hold.objects.filter(operation__owner=user, state="ACTIVE").aggregate(value=Sum("amount"))[
            "value"
        ]
        or 0
    )
    assert posted >= reserved >= 0


def replacement_policy(**changes):
    current = services.initialize_policy()
    values = {
        field: getattr(current, field)
        for field in [
            "signup_grant",
            "daily_spend_cap",
            "global_ai_cap",
            "matching_price",
            "cv_price",
            "document_price",
        ]
    }
    admin = account(role="ADMIN", grant=False, admin_scopes=["COST_POLICY"])
    now = timezone.now()
    proof = IdentitySession.objects.create(
        account=admin,
        digest=digest(str(uuid.uuid4())),
        epoch=admin.session_epoch,
        expires_at=now + timedelta(hours=1),
        mfa_verified_at=now,
    )
    return services.publish_policy(
        admin,
        proof,
        {**values, **changes, "reason": "Authored synthetic policy change."},
        current.version,
    )


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        (datetime(2026, 1, 10, 21, 59, 59, tzinfo=UTC), date(2026, 1, 10)),
        (datetime(2026, 1, 10, 22, 0, tzinfo=UTC), date(2026, 1, 11)),
        (datetime(2026, 7, 10, 20, 59, 59, tzinfo=UTC), date(2026, 7, 10)),
        (datetime(2026, 7, 10, 21, 0, tzinfo=UTC), date(2026, 7, 11)),
    ],
)
def test_hebron_day_uses_real_winter_and_summer_offsets(instant, expected):
    assert services.business_day(instant) == expected


def test_real_activation_grants_once_in_the_verification_transaction():
    user = account(grant=False, state="PENDING", email_verified_at=None)
    token = issue(user, "VERIFY_EMAIL")
    assert not Wallet.objects.filter(owner=user).exists()
    verify_email(token, None)
    user.refresh_from_db()
    assert user.state == "ACTIVE"
    entry = LedgerEntry.objects.get(owner=user, kind="SIGNUP_GRANT")
    assert entry.amount == 30 and balances(user) == (30, 0)
    assert services.grant_signup(user.pk).pk == entry.pk
    assert LedgerEntry.objects.filter(owner=user).count() == 1
    conserved(user)


def test_activation_grant_failure_rolls_back_activation_and_token_consumption():
    user = account(grant=False, state="PENDING", email_verified_at=None)
    token = issue(user, "VERIFY_EMAIL")
    with patch("credits.services.grant_signup", side_effect=DatabaseError("synthetic outage")):
        with pytest.raises(DatabaseError), transaction.atomic():
            verify_email(token, None)
    user.refresh_from_db()
    assert user.state == "PENDING" and user.email_verified_at is None
    assert not Wallet.objects.filter(owner=user).exists()
    verify_email(token, None)
    assert balances(user) == (30, 0)


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "PENDING"},
        {"email_verified_at": None},
        {"birth_date": date(2015, 1, 1)},
        {"state": "DELETION_PENDING"},
        {"state": "SUSPENDED"},
        {"state": "DELETED"},
        {"role": "ADMIN"},
    ],
)
def test_nonqualifying_identity_cannot_receive_grant(changes):
    user = account(grant=False, **changes)
    with pytest.raises(IdentityError):
        services.grant_signup(user.pk)
    assert not LedgerEntry.objects.filter(owner=user).exists()


def test_zero_signup_grant_consumes_entitlement_and_policy_cannot_regrant():
    zero = replacement_policy(signup_grant=0)
    user = account()
    entry = LedgerEntry.objects.get(owner=user, kind="SIGNUP_GRANT")
    assert entry.amount == 0 and entry.policy_id == zero.pk
    assert balances(user) == (0, 0)
    replacement_policy(signup_grant=60)
    assert services.grant_signup(user.pk).pk == entry.pk
    assert balances(user) == (0, 0)


def test_activation_grant_is_not_daily_refill_or_policy_top_up():
    user = account()
    grant = LedgerEntry.objects.get(owner=user, kind="SIGNUP_GRANT")
    replacement_policy(signup_grant=60)
    future = timezone.now() + timedelta(days=20)
    with patch("django.utils.timezone.now", return_value=future):
        assert services.grant_signup(user.pk).pk == grant.pk
    assert balances(user) == (30, 0)
    assert LedgerEntry.objects.filter(owner=user).count() == 1


@pytest.mark.parametrize(
    "service,price", [("MATCHING_AI", 1), ("CV_EXTRACTION", 4), ("DOCUMENT_NEW", 6)]
)
def test_default_prices_reserve_without_debit(service, price):
    user = account()
    operation = reserve(user, service)
    assert operation.state == "RESERVED" and operation.price == price
    assert operation.reserve_until - operation.created_at == timedelta(minutes=15)
    assert balances(user) == (30, price)
    assert LedgerEntry.objects.filter(owner=user).count() == 1
    assert not SavedOutput.objects.filter(operation=operation).exists()
    conserved(user)


def test_settlement_requires_exact_saved_validated_witness_and_debits_once():
    user = account()
    operation = reserve(user, "CV_EXTRACTION")
    fence = services.claim(user.pk, operation.pk)
    operation.refresh_from_db()
    assert operation.state == "RUNNING" and balances(user) == (30, 4)
    services.settle(user.pk, operation.pk, fence, payload(operation))
    operation.refresh_from_db()
    assert operation.state == "SETTLED" and balances(user) == (26, 0)
    output = SavedOutput.objects.get(operation=operation, owner=user)
    debit = LedgerEntry.objects.get(operation=operation, kind="DEBIT")
    assert debit.amount == -4
    assert output.payload == payload(operation) and output.validator_version
    final = Finalization.objects.get(operation=operation)
    assert final.output_id == output.pk and final.entry_id == debit.pk
    services.settle(user.pk, operation.pk, fence, payload(operation))
    assert SavedOutput.objects.filter(operation=operation).count() == 1
    assert LedgerEntry.objects.filter(operation=operation).count() == 1
    assert balances(user) == (26, 0)
    conserved(user)


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"result": "SYNTHETIC_OK"},
        {"fixture_id": str(uuid.uuid4()), "result": "SYNTHETIC_OK"},
        {"fixture_id": None, "result": "SYNTHETIC_OK"},
        {"fixture_id": "not-a-uuid", "result": "SYNTHETIC_OK"},
        {"result": "UNVERIFIED"},
        {"result": "SYNTHETIC_OK", "validated": True},
    ],
)
def test_unverified_or_substituted_output_never_charges(bad):
    user = account()
    operation = reserve(user)
    fence = services.claim(user.pk, operation.pk)
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, fence, bad)
    assert balances(user) == (30, 1)
    assert not SavedOutput.objects.filter(operation=operation).exists()
    assert not LedgerEntry.objects.filter(operation=operation).exists()
    assert not Finalization.objects.filter(operation=operation).exists()
    conserved(user)


def test_output_storage_failure_rolls_back_all_financial_effects():
    user = account()
    operation = reserve(user)
    fence = services.claim(user.pk, operation.pk)
    with patch.object(
        SavedOutput.objects, "create", side_effect=DatabaseError("synthetic save failure")
    ):
        with pytest.raises(DatabaseError), transaction.atomic():
            services.settle(user.pk, operation.pk, fence, payload(operation))
    assert balances(user) == (30, 1)
    assert not LedgerEntry.objects.filter(operation=operation).exists()
    assert not Finalization.objects.filter(operation=operation).exists()
    operation.refresh_from_db()
    assert operation.state == "RUNNING"
    conserved(user)


def test_settlement_cannot_create_output_before_claim_or_under_wrong_fence():
    user = account()
    operation = reserve(user)
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, "synthetic-invalid-fence", payload(operation))
    fence = services.claim(user.pk, operation.pk)
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, "synthetic-invalid-fence", payload(operation))
    assert balances(user) == (30, 1)
    services.settle(user.pk, operation.pk, fence, payload(operation))
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, fence, {**payload(operation), "result": "CHANGED"})
    assert balances(user) == (29, 0)


def test_proven_failure_releases_hold_once_without_positive_refund():
    user = account()
    operation = reserve(user, "DOCUMENT_NEW")
    fence = services.claim(user.pk, operation.pk)
    services.fail(user.pk, operation.pk, fence)
    services.fail(user.pk, operation.pk, fence)
    operation.refresh_from_db()
    assert operation.state == "RELEASED" and balances(user) == (30, 0)
    assert not LedgerEntry.objects.filter(operation=operation).exists()
    assert Finalization.objects.filter(operation=operation, outcome="RELEASED").count() == 1
    assert GlobalDay.objects.get(day=operation.captured_day).admitted_operations == 1
    day = StudentDay.objects.get(owner=user, day=operation.captured_day)
    assert day.reserved == day.spent == 0
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, fence, payload(operation))
    conserved(user)


def test_unknown_timeout_retains_reservation_and_cannot_restart_or_guess_failure():
    user = account()
    operation = reserve(user, "CV_EXTRACTION")
    fence = services.claim(user.pk, operation.pk)
    services.mark_uncertain(user.pk, operation.pk, fence)
    operation.refresh_from_db()
    assert operation.state == "RECONCILING" and balances(user) == (30, 4)
    assert operation.resolution_due_at - operation.reconciliation_started_at == timedelta(hours=24)
    with pytest.raises(IdentityError):
        services.claim(user.pk, operation.pk)
    with pytest.raises(IdentityError):
        services.fail(user.pk, operation.pk, fence)
    assert not Finalization.objects.filter(operation=operation).exists()
    conserved(user)


def test_exact_fifteen_minute_marker_and_twenty_four_hour_target_never_release():
    user = account()
    operation = reserve(user)
    services.mark_expired(operation.pk, now=operation.reserve_until - timedelta(microseconds=1))
    operation.refresh_from_db()
    assert operation.state == "RESERVED"
    services.mark_expired(operation.pk, now=operation.reserve_until)
    operation.refresh_from_db()
    assert operation.state == "RECONCILING" and balances(user) == (30, 1)
    due = operation.resolution_due_at
    services.mark_expired(operation.pk, now=due)
    services.mark_expired(operation.pk, now=due + timedelta(days=2))
    operation.refresh_from_db()
    assert operation.state == "RECONCILING" and operation.resolution_due_at == due
    assert (
        balances(user) == (30, 1) and not Finalization.objects.filter(operation=operation).exists()
    )


def test_idempotent_replay_preserves_identity_hold_input_and_price():
    user = account()
    fixture = services.create_synthetic_input(user.pk)
    key = str(uuid.uuid4())
    first = reserve(user, key=key, input_id=fixture)
    replacement_policy(matching_price=2)
    replay = reserve(user, key=key, input_id=fixture)
    assert replay.pk == first.pk and replay.price == 1
    assert balances(user) == (30, 1) and Operation.objects.filter(owner=user).count() == 1
    assert GlobalDay.objects.get(day=first.captured_day).admitted_operations == 1
    with pytest.raises(IdentityError):
        reserve(user, "CV_EXTRACTION", key=key, input_id=fixture)
    with pytest.raises(IdentityError):
        reserve(user, key=key)
    assert balances(user) == (30, 1)


def test_same_key_is_separately_scoped_to_two_students():
    one, two = account(), account()
    key = str(uuid.uuid4())
    first, second = reserve(one, key=key), reserve(two, key=key)
    assert first.pk != second.pk and balances(one) == balances(two) == (30, 1)
    assert GlobalDay.objects.get(day=first.captured_day).admitted_operations == 2


def test_snapshot_price_survives_policy_edit_and_limits_do_not_reset_usage():
    user = account()
    operation = reserve(user, "CV_EXTRACTION")
    fence = services.claim(user.pk, operation.pk)
    old_policy = operation.policy_id
    replacement_policy(cv_price=2, daily_spend_cap=3)
    with pytest.raises(IdentityError):
        reserve(user)
    services.settle(user.pk, operation.pk, fence, payload(operation))
    operation.refresh_from_db()
    assert operation.price == 4 and operation.policy_id == old_policy
    assert balances(user) == (26, 0)
    assert StudentDay.objects.filter(owner=user, day=operation.captured_day).count() == 1
    assert StudentDay.objects.get(owner=user, day=operation.captured_day).spent == 4
    with pytest.raises(IdentityError):
        reserve(user)


def test_reserve_checks_daily_spend_and_available_balance_separately():
    user = account()
    operation = reserve(user, "DOCUMENT_NEW")
    with pytest.raises(IdentityError):
        reserve(user)
    assert balances(user) == (30, 6)
    fence = services.claim(user.pk, operation.pk)
    services.fail(user.pk, operation.pk, fence)
    replacement_policy(signup_grant=0)
    empty = account()
    with pytest.raises(IdentityError):
        reserve(empty)
    assert balances(empty) == (0, 0)


def test_release_after_midnight_updates_original_bucket_without_refill():
    user = account()
    before = datetime(2026, 7, 10, 20, 59, 59, tzinfo=UTC)
    after = before + timedelta(seconds=2)
    with patch("django.utils.timezone.now", return_value=before):
        operation = reserve(user, "CV_EXTRACTION")
        fence = services.claim(user.pk, operation.pk)
    with patch("django.utils.timezone.now", return_value=after):
        services.fail(user.pk, operation.pk, fence)
        second = reserve(user, "CV_EXTRACTION")
    first_day = StudentDay.objects.get(owner=user, day=date(2026, 7, 10))
    next_day = StudentDay.objects.get(owner=user, day=date(2026, 7, 11))
    assert first_day.reserved == first_day.spent == 0
    assert next_day.reserved == 4 and next_day.spent == 0
    assert second.captured_day == date(2026, 7, 11) and balances(user) == (30, 4)
    assert LedgerEntry.objects.filter(owner=user, kind="SIGNUP_GRANT").count() == 1


@pytest.mark.parametrize("method", ["reserve", "claim", "settle", "fail", "mark_uncertain"])
def test_cross_user_accounting_commands_deny_without_mutation(method):
    owner, other = account(), account()
    fixture = services.create_synthetic_input(owner.pk)
    operation = reserve(owner, input_id=fixture)
    fence = services.claim(owner.pk, operation.pk)
    with pytest.raises(IdentityError):
        if method == "reserve":
            services.reserve(other.pk, "MATCHING_AI", str(uuid.uuid4()), fixture)
        elif method in {"settle"}:
            services.settle(other.pk, operation.pk, fence, payload(operation))
        elif method == "claim":
            services.claim(other.pk, operation.pk)
        else:
            getattr(services, method)(other.pk, operation.pk, fence)
    assert balances(owner) == (30, 1) and balances(other) == (30, 0)
    assert not LedgerEntry.objects.filter(operation=operation).exists()


@pytest.mark.parametrize("state", ["DELETION_PENDING", "SUSPENDED", "DELETED"])
def test_nonactive_lifecycle_freezes_new_spend_and_output_acceptance(state):
    user = account()
    operation = reserve(user)
    fence = services.claim(user.pk, operation.pk)
    Account.objects.filter(pk=user.pk).update(state=state)
    with pytest.raises(IdentityError):
        reserve(user)
    with pytest.raises(IdentityError):
        services.settle(user.pk, operation.pk, fence, payload(operation))
    assert balances(user) == (30, 1)
    assert not LedgerEntry.objects.filter(operation=operation).exists()


def test_synthetic_factories_and_execution_fail_closed_outside_local_mode(settings):
    user = account()
    operation = reserve(user)
    settings.LOCAL = False
    with pytest.raises(IdentityError):
        services.create_synthetic_input(user.pk)
    with pytest.raises(IdentityError):
        reserve(user, input_id=operation.fixture_id)
    with pytest.raises(IdentityError):
        services.claim(user.pk, operation.pk)
    assert balances(user) == (30, 1)


def csrf(client):
    response = client.get("/api/v1/session/csrf")
    assert response.status_code == 200, response.content
    return response.json()["csrf_token"]


def signed_client(user):
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        "/api/v1/session/login",
        {"email": user.email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf(client),
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 200, response.content
    return client


def policy_input(**changes):
    policy = services.initialize_policy()
    return {
        **{name: getattr(policy, name) for name in services.POLICY_FIELDS},
        "reason": "Authored synthetic policy API fixture.",
        **changes,
    }


def policy_admin_client(*, scopes=None, mfa=True):
    admin = account(
        role="ADMIN", grant=False, admin_scopes=["COST_POLICY"] if scopes is None else scopes
    )
    client = signed_client(admin)
    proof = IdentitySession.objects.get(digest=digest(client.session.session_key))
    if mfa:
        # Synthetic server-side proof only; public JSON cannot assert MFA.
        proof.mfa_verified_at = timezone.now()
        proof.save(update_fields=["mfa_verified_at"])
    return client, admin, proof


def policy_post(client, data, *, version=1, key=None, include_csrf=True):
    headers = {"HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4())}
    if version is not None:
        headers["HTTP_IF_MATCH"] = f'"{version}"'
    if include_csrf:
        headers["HTTP_X_CSRFTOKEN"] = csrf(client)
    return client.post("/api/v1/admin/policies/credits", data, format="json", **headers)


def test_policy_api_requires_csrf_current_version_and_idempotent_exact_body():
    client, _, _ = policy_admin_client()
    before = client.get("/api/v1/admin/policies/credits")
    assert before.status_code == 200 and before["ETag"] == '"1"'
    data = policy_input(matching_price=2)
    assert policy_post(client, data, include_csrf=False).status_code == 403
    assert policy_post(client, data, version=None).status_code == 412
    assert policy_post(client, data, version=99).status_code == 412
    key = str(uuid.uuid4())
    first = policy_post(client, data, key=key)
    assert first.status_code == 200, first.content
    assert first.json()["version"] == 2 and first.json()["prices"]["MATCHING_AI"] == 2
    replay = policy_post(client, data, key=key)
    assert replay.status_code == 200 and replay.json() == first.json()
    assert policy_post(client, {**data, "matching_price": 3}, key=key).status_code == 409
    assert policy_post(client, data, version=1).status_code == 412
    assert CreditPolicy.objects.count() == 2


@pytest.mark.parametrize("scopes,mfa", [([], True), (["PRIVACY"], True), (["COST_POLICY"], False)])
def test_cost_policy_admin_needs_exact_scope_and_current_server_mfa(scopes, mfa):
    client, _, _ = policy_admin_client(scopes=scopes, mfa=mfa)
    assert client.get("/api/v1/admin/policies/credits").status_code == 403
    assert policy_post(client, policy_input()).status_code == 403
    assert CreditPolicy.objects.count() == 1


def test_student_cannot_configure_credit_policy_or_claim_admin_mfa_in_json():
    client = signed_client(account())
    assert client.get("/api/v1/admin/policies/credits").status_code == 403
    assert policy_post(client, policy_input()).status_code == 403
    assert CreditPolicy.objects.count() == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"matching_price": 0},
        {"matching_price": True},
        {"daily_spend_cap": -1},
        {"global_ai_cap": 1_000_001},
        {"signup_grant": 2.5},
        {"reason": ""},
        {"owner_id": str(uuid.uuid4())},
        {"mfa_verified": True},
        {"timezone": "UTC"},
    ],
)
def test_policy_rejects_unbounded_fractional_or_authority_fields(changes):
    client, _, _ = policy_admin_client()
    assert policy_post(client, policy_input(**changes)).status_code == 400
    assert CreditPolicy.objects.count() == 1


@pytest.mark.parametrize("offset", [timedelta(minutes=-15), timedelta(minutes=1)])
def test_policy_rejects_expired_or_future_server_mfa(offset):
    client, _, proof = policy_admin_client()
    IdentitySession.objects.filter(pk=proof.pk).update(mfa_verified_at=timezone.now() + offset)
    assert client.get("/api/v1/admin/policies/credits").status_code == 403
    assert policy_post(client, policy_input()).status_code == 403


def test_free_features_have_no_funded_operation_or_implicit_price_fallback():
    user = account()
    fixture = services.create_synthetic_input(user.pk)
    assert set(services.FREE_SERVICES) == {
        "BROWSING",
        "RULES_ELIGIBILITY",
        "MANUAL_EDITS",
        "SAME_VERSION_REEXPORT",
        "EXTENSION",
    }
    for free in services.FREE_SERVICES:
        with pytest.raises(IdentityError):
            services.reserve(user.pk, free, str(uuid.uuid4()), fixture)
    assert not Operation.objects.filter(owner=user).exists()
    assert balances(user) == (30, 0)


@pytest.mark.parametrize("key", ["", "short", "x" * 129, "with space-and-long-value", "ط" * 20])
def test_invalid_idempotency_keys_never_admit_or_reserve(key):
    user = account()
    fixture = services.create_synthetic_input(user.pk)
    with pytest.raises(IdentityError):
        services.reserve(user.pk, "MATCHING_AI", key, fixture)
    assert not Operation.objects.filter(owner=user).exists()
    assert balances(user) == (30, 0)


def test_worker_fence_expires_exactly_at_reservation_marker_without_charge():
    user = account()
    operation = reserve(user)
    token = services.claim(user.pk, operation.pk)
    with patch("django.utils.timezone.now", return_value=operation.reserve_until):
        with pytest.raises(IdentityError):
            services.settle(user.pk, operation.pk, token, payload(operation))
    services.mark_expired(operation.pk, operation.reserve_until)
    assert balances(user) == (30, 1)
    assert not LedgerEntry.objects.filter(operation=operation).exists()


@pytest.mark.parametrize("row", ["output", "entry", "finalization"])
def test_database_rejects_deleting_any_settled_evidence(row):
    user = account()
    operation = reserve(user)
    token = services.claim(user.pk, operation.pk)
    services.settle(user.pk, operation.pk, token, payload(operation))
    model = {"output": SavedOutput, "entry": LedgerEntry, "finalization": Finalization}[row]
    with pytest.raises(DatabaseError), transaction.atomic():
        model.objects.filter(operation=operation).delete()
        force_constraints()
    assert balances(user) == (29, 0)


def test_saved_output_without_atomic_acceptance_debit_and_finalization_is_rejected():
    user = account()
    operation = reserve(user)
    services.claim(user.pk, operation.pk)
    with pytest.raises(DatabaseError), transaction.atomic():
        SavedOutput.objects.create(
            operation=operation,
            owner=user,
            payload=payload(operation),
            content_hash=services.payload_hash(payload(operation)),
            validator_version="synthetic-v1",
        )
        force_constraints()
    assert balances(user) == (30, 1)
    assert not SavedOutput.objects.filter(operation=operation).exists()


def test_owner_wallet_reports_ledger_and_reservation_without_secrets():
    user = account()
    operation = reserve(user, "CV_EXTRACTION")
    client = signed_client(user)
    response = client.get("/api/v1/wallet")
    assert response.status_code == 200, response.content
    data = response.json()
    assert (data["posted_balance"], data["reserved_balance"], data["available_balance"]) == (
        30,
        4,
        26,
    )
    assert data["signup_grant"]["awarded"] and data["signup_grant"]["amount"] == 30
    assert data["daily"]["timezone"] == "Asia/Hebron"
    assert data["daily"]["cap"] == 6 and data["daily"]["remaining"] == 2
    assert data["global_daily"]["cap"] == 100
    assert data["policy"]["ai_execution_available"] is False
    assert data["policy"]["prices"] == {"MATCHING_AI": 1, "CV_EXTRACTION": 4, "DOCUMENT_NEW": 6}
    text = response.content.decode()
    assert user.email not in text and PASSWORD not in text and str(operation.fixture_id) not in text
    assert "no-store" in response["Cache-Control"]
    entries = client.get("/api/v1/wallet/entries").json()
    assert entries["total"] == 1 and entries["items"][0]["amount"] == 30


def test_operation_poll_is_owner_only_and_omits_execution_witnesses():
    user, other = account(), account()
    operation = reserve(user)
    owner_client, other_client = signed_client(user), signed_client(other)
    response = owner_client.get(f"/api/v1/operations/{operation.pk}")
    assert response.status_code == 200, response.content
    data = response.json()
    assert data["id"] == str(operation.pk) and data["state"] == "RESERVED"
    assert data["price"] == 1 and data["output_id"] is None
    assert not {
        "owner_id",
        "fixture_id",
        "key_digest",
        "request_digest",
        "fence_digest",
        "payload",
    } & set(data)
    assert other_client.get(f"/api/v1/operations/{operation.pk}").status_code == 403
    assert owner_client.get(f"/api/v1/operations/{uuid.uuid4()}").status_code == 403
    assert other_client.get("/api/v1/operations").json()["total"] == 0


@pytest.mark.parametrize("path", ["wallet", "wallet/entries", "operations"])
def test_wallet_and_operation_reads_deny_anonymous_and_admin(path):
    assert APIClient().get("/api/v1/" + path).status_code == 401
    admin = account(role="ADMIN", grant=False, admin_scopes=["COST_POLICY"])
    client = signed_client(admin)
    assert client.get("/api/v1/" + path).status_code == 403


@pytest.mark.parametrize("query", ["?owner_id=other", "?page=0", "?page_size=51", "?page_size=bad"])
def test_ledger_pagination_and_unknown_owner_filter_fail_strictly(query):
    client = signed_client(account())
    assert client.get("/api/v1/wallet/entries" + query).status_code == 400


def test_accounting_has_no_public_execution_or_balance_mutation_routes():
    user = account()
    client = signed_client(user)
    operation = reserve(user)
    for path in ["wallet", "operations", f"operations/{operation.pk}"]:
        response = client.post(
            "/api/v1/" + path,
            {"owner_id": str(user.pk), "amount": 100, "validated": True},
            format="json",
            HTTP_X_CSRFTOKEN=csrf(client),
        )
        assert response.status_code == 405, response.content
    assert balances(user) == (30, 1)


def force_constraints():
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize("table", ["ledger", "hold", "policy"])
def test_accounting_history_cannot_be_deleted_or_repriced(table):
    user = account()
    operation = reserve(user)
    with pytest.raises(DatabaseError), transaction.atomic():
        if table == "ledger":
            LedgerEntry.objects.filter(owner=user).delete()
        elif table == "hold":
            Hold.objects.filter(operation=operation).delete()
        else:
            CreditPolicy.objects.filter(pk=operation.policy_id).update(matching_price=100)
        force_constraints()
    assert balances(user) == (30, 1)
    conserved(user)


@pytest.mark.parametrize("mutation", ["posted", "reserved", "state", "student", "global"])
def test_database_rejects_projection_or_terminal_state_corruption(mutation):
    user = account()
    operation = reserve(user)
    with pytest.raises(DatabaseError), transaction.atomic():
        if mutation == "posted":
            Wallet.objects.filter(owner=user).update(posted_balance=100)
        elif mutation == "reserved":
            Wallet.objects.filter(owner=user).update(reserved_balance=0)
        elif mutation == "state":
            Operation.objects.filter(pk=operation.pk).update(state="SETTLED")
        elif mutation == "student":
            StudentDay.objects.filter(owner=user).update(reserved=0)
        else:
            GlobalDay.objects.filter(day=operation.captured_day).update(admitted_operations=0)
        force_constraints()
    assert balances(user) == (30, 1)
    conserved(user)
