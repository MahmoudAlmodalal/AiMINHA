"""Gateway integration uses synthetic fixtures and never contacts a provider."""

import json
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from ai_gateway import services
from ai_gateway.adapters import AdapterResponse, MockAdapter
from ai_gateway.models import (
    Attempt,
    GatewayRequest,
    GatewayResult,
    ProviderApproval,
    ProviderConfig,
    QuotaWindow,
    RoutingEvent,
)
from credits import services as credits
from credits.models import GlobalDay, LedgerEntry, Operation, SavedOutput, Wallet
from django.db import DatabaseError, transaction
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, digest
from privacy.models import ConsentRecord, Disclosure, PrivacyAudit
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def local_gateway(settings):
    settings.LOCAL = True
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    credits.initialize_policy()


def student(**changes):
    user = Account.objects.create(
        email=f"gateway-{uuid.uuid4()}@example.invalid",
        birth_date=date(2000, 1, 1),
        state="ACTIVE",
        email_verified_at=timezone.now(),
        **changes,
    )
    if user.role == "STUDENT":
        credits.grant_signup(user.pk)
    return user


def config(
    *,
    provider="MOCK",
    classification="PUBLIC/SYNTHETIC",
    approval=True,
    quota_changes=None,
    approval_changes=None,
    **changes,
):
    now = timezone.now()
    scope = {
        "provider": provider,
        "model": "synthetic-grounded-v1",
        "classification": classification,
        "data_type": "SYNTHETIC_FIXTURE",
        "purpose": "SYNTHETIC_GROUNDING",
        "region": "LOCAL",
    }
    for key in tuple(scope):
        if key in changes:
            scope[key] = changes.pop(key)
    quota = changes.pop("quota", None) or QuotaWindow.objects.create(
        **{
            "provider": provider,
            "account_ref": uuid.uuid4(),
            "unit": "NEURONS" if provider == "CLOUDFLARE" else "REQUESTS",
            "starts_at": now - timedelta(hours=1),
            "ends_at": now + timedelta(hours=23),
            "hard_limit": 8000 if provider == "CLOUDFLARE" else 100,
            "observed_used": 0,
            "observed_at": now - timedelta(minutes=1),
            "valid_until": now + timedelta(hours=1),
            "measurement_ref": uuid.uuid4(),
            "free_only_confirmed": True,
            **(quota_changes or {}),
        }
    )
    evidence = None
    if approval:
        evidence = ProviderApproval.objects.create(
            **{
                **scope,
                "evidence_ref": uuid.uuid4(),
                "terms_ref": uuid.uuid4(),
                "private_controls_approved": classification == "STUDENT_PRIVATE",
                "approved_at": now - timedelta(minutes=1),
                "expires_at": now + timedelta(days=1),
                **(approval_changes or {}),
            }
        )
    return ProviderConfig.objects.create(
        **scope,
        approval=evidence,
        quota=quota,
        enabled=True,
        timeout_seconds=10,
        attempt_limit=2,
        max_units_per_attempt=1,
        **changes,
    )


def prepared(user, routes=None, *, key=None, language="en"):
    fixture = credits.create_synthetic_input(user.pk)
    operation = credits.reserve(user.pk, "MATCHING_AI", key or str(uuid.uuid4()), fixture)
    routes = routes or [config()]
    request = services.prepare(user.pk, operation.pk, [route.pk for route in routes], language)
    return request


def run(user, request, adapter=None):
    return services.run(user.pk, request.pk, {"MOCK": adapter or MockAdapter()})


def no_debit(user):
    assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()
    assert not GatewayResult.objects.filter(owner=user).exists()
    assert not SavedOutput.objects.filter(owner=user).exists()
    assert Wallet.objects.get(owner=user).posted_balance == 30


def authorize(user, route, *, classification=None, consent_version=None, origins=None):
    return services.authorize(
        user.pk,
        route.pk,
        classification or route.classification,
        user.consent_version if consent_version is None else consent_version,
        origins or ("SYNTHETIC_FIXTURE",),
    )


def test_success_saves_validated_grounding_and_debits_exactly_once():
    user = student()
    route = config()
    request = prepared(user, [route])
    mock = MockAdapter()
    result = run(user, request, mock)
    assert result.state == "SETTLED"
    assert mock.calls == 1
    assert GatewayResult.objects.filter(request=request, owner=user).count() == 1
    assert SavedOutput.objects.filter(operation=request.operation, owner=user).count() == 1
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").get().amount == -1
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (29, 0)
    assert GlobalDay.objects.get().admitted_operations == 1
    assert Attempt.objects.filter(request=request, state="SUCCEEDED").count() == 1
    route.quota.refresh_from_db()
    assert route.quota.reserved == 0 and route.quota.consumed == 1
    assert run(user, request, mock).pk == result.pk
    assert mock.calls == 1


@pytest.mark.parametrize("language", ["ar", "en"])
def test_requested_language_is_preserved_in_grounded_result(language):
    user = student()
    request = prepared(user, language=language)
    run(user, request)
    output = GatewayResult.objects.get(request=request).payload
    assert output["language"] == language
    assert output["claims"]
    assert all(claim["citations"] == ["fixture"] for claim in output["claims"])


def test_prepare_is_idempotent_for_the_same_immutable_operation_and_routes():
    user = student()
    route = config()
    request = prepared(user, [route])
    repeated = services.prepare(user.pk, request.operation_id, [route.pk], "en")
    assert repeated.pk == request.pk
    assert GatewayRequest.objects.filter(operation=request.operation).count() == 1
    assert GlobalDay.objects.get().admitted_operations == 1


def test_prepare_cannot_rebind_an_existing_operation_to_new_routes_or_language():
    user = student()
    first, second = config(), config(model="second-synthetic-model")
    request = prepared(user, [first])
    with pytest.raises(IdentityError):
        services.prepare(user.pk, request.operation_id, [second.pk], "en")
    with pytest.raises(IdentityError):
        services.prepare(user.pk, request.operation_id, [first.pk], "ar")
    request.refresh_from_db()
    assert request.route_ids == [str(first.pk)] and request.language == "en"


def test_cross_student_prepare_run_and_authorize_do_not_expose_owned_operation():
    owner, other = student(), student()
    request = prepared(owner)
    mock = MockAdapter()
    with pytest.raises(IdentityError):
        services.prepare(other.pk, request.operation_id, request.route_ids, "en")
    with pytest.raises(IdentityError):
        services.run(other.pk, request.pk, {"MOCK": mock})
    assert mock.calls == 0
    no_debit(owner)
    no_debit(other)


@pytest.mark.parametrize("classification", ["PROHIBITED", "UNKNOWN", "public", ""])
def test_prohibited_or_unknown_classification_never_authorizes(classification):
    user, route = student(), config()
    with pytest.raises(IdentityError):
        services.authorize(user.pk, route.pk, classification, 0, ("SYNTHETIC_FIXTURE",))
    assert not Attempt.objects.exists()
    no_debit(user)


@pytest.mark.parametrize("origins", [("STUDENT_PROFILE",), ("PUBLIC_CATALOG", "CV"), ("OTP",)])
def test_claimed_public_class_cannot_downgrade_private_or_prohibited_origins(origins):
    user, route = student(), config()
    with pytest.raises(IdentityError):
        authorize(user, route, origins=origins)
    assert not Attempt.objects.exists()


@pytest.mark.parametrize(
    "provider", ["MOCK", "CLOUDFLARE", "GROQ", "GEMINI_FREE", "OPENROUTER_FREE"]
)
def test_missing_individual_approval_blocks_every_provider(provider):
    user, route = student(), config(provider=provider, approval=False)
    with pytest.raises(IdentityError):
        authorize(user, route)
    assert not Attempt.objects.exists()


@pytest.mark.parametrize("provider", ["GEMINI_FREE", "OPENROUTER_FREE", "MOCK"])
def test_private_data_cannot_route_to_unpaid_public_providers_even_with_recorded_approval(provider):
    user = student()
    with pytest.raises(DatabaseError), transaction.atomic():
        config(provider=provider, classification="STUDENT_PRIVATE", data_type="CV")
    assert not Attempt.objects.exists()
    no_debit(user)


@pytest.mark.parametrize("provider", ["CLOUDFLARE", "GROQ"])
def test_generic_personal_ai_consent_is_not_a_scoped_private_pipeline_approval(provider):
    user = student()
    disclosure = Disclosure.objects.create(
        purpose="PERSONAL_AI", version=1, available=True, disclosure="Synthetic test notice."
    )
    Account.objects.filter(pk=user.pk).update(consent_version=1)
    ConsentRecord.objects.create(account=user, disclosure=disclosure, version=1, state="GRANTED")
    user.refresh_from_db()
    route = config(provider=provider, classification="STUDENT_PRIVATE", data_type="CV")
    with pytest.raises(IdentityError) as caught:
        authorize(user, route, origins=("CV",))
    assert caught.value.code == "SCOPED_PRIVATE_PIPELINE_UNAVAILABLE"
    assert not Attempt.objects.exists()
    no_debit(user)


@pytest.mark.parametrize("provider", ["CLOUDFLARE", "GROQ", "GEMINI_FREE", "OPENROUTER_FREE"])
def test_real_adapter_execution_cannot_be_enabled_by_configuration_or_registry(provider):
    user = student()
    route = config(provider=provider)
    request = prepared(user, [route])
    mock = MockAdapter()
    try:
        services.run(user.pk, request.pk, {provider: mock})
    except IdentityError:
        pass
    assert mock.calls == 0
    assert not Attempt.objects.filter(request=request, state="SUCCEEDED").exists()
    no_debit(user)


@pytest.mark.parametrize("field", ["model", "classification", "data_type", "purpose", "region"])
def test_approval_scope_must_match_the_exact_configuration(field):
    route = config()
    with pytest.raises(DatabaseError), transaction.atomic():
        ProviderConfig.objects.filter(pk=route.pk).update(**{field: "DIFFERENT_SCOPE"})
    assert not Attempt.objects.exists()


@pytest.mark.parametrize("condition", ["expired", "future", "revoked"])
def test_inactive_approval_cannot_authorize(condition):
    user = student()
    now = timezone.now()
    changes = {}
    if condition == "expired":
        changes = {"approved_at": now - timedelta(days=2), "expires_at": now}
    elif condition == "future":
        changes = {"approved_at": now + timedelta(days=1), "expires_at": now + timedelta(days=2)}
    else:
        changes = {"revoked_at": now}
    route = config(approval_changes=changes)
    with pytest.raises(IdentityError):
        authorize(user, route)
    assert not Attempt.objects.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("measurement_ref", None),
        ("free_only_confirmed", False),
        ("blocked_reason", "UNKNOWN_OUTCOME"),
    ],
)
def test_unknown_capacity_or_paid_eligibility_never_dispatches(field, value):
    user, route = student(), config(quota_changes={field: value})
    request, mock = prepared(user, [route]), MockAdapter()
    try:
        run(user, request, mock)
    except IdentityError:
        pass
    assert mock.calls == 0
    no_debit(user)


@pytest.mark.parametrize("field", ["valid_until", "ends_at"])
def test_capacity_at_expiry_is_closed(field):
    user, route = student(), config(quota_changes={field: timezone.now()})
    with pytest.raises(IdentityError):
        authorize(user, route)
    assert not Attempt.objects.exists()


def test_exhausted_provider_capacity_does_not_dispatch_or_charge():
    user, route = student(), config(quota_changes={"observed_used": 100})
    request, mock = prepared(user, [route]), MockAdapter()
    try:
        run(user, request, mock)
    except IdentityError:
        pass
    assert mock.calls == 0
    no_debit(user)


@pytest.mark.parametrize("outcome", ["INVALID_OUTPUT", "UNSUPPORTED_CLAIM"])
def test_invalid_output_is_not_chargeable_success_and_never_uses_fallback(outcome):
    user = student()
    primary, fallback = config(), config(model="fallback-synthetic-v1")
    request = prepared(user, [primary, fallback])
    mock = MockAdapter((outcome, "SUCCESS"))
    result = run(user, request, mock)
    assert result.state == "RELEASED"
    assert mock.calls == 1
    assert Attempt.objects.filter(request=request, state="REJECTED").count() == 1
    assert Wallet.objects.get(owner=user).reserved_balance == 0
    no_debit(user)


@pytest.mark.parametrize("outcome", ["UNAVAILABLE", "RATE_LIMIT"])
def test_proven_nonexecution_allows_bounded_retry_without_a_second_logical_charge(outcome):
    user = student()
    route = config()
    request = prepared(user, [route])
    mock = MockAdapter((outcome, "SUCCESS"))
    result = run(user, request, mock)
    assert result.state == "SETTLED"
    assert mock.calls == 2
    assert Attempt.objects.filter(request=request).count() == 2
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").count() == 1
    assert GlobalDay.objects.get().admitted_operations == 1
    route.quota.refresh_from_db()
    assert route.quota.consumed == 2 and route.quota.reserved == 0


def test_timeout_is_unknown_and_does_not_retry_release_or_fallback():
    user = student()
    primary, fallback = config(), config(model="fallback-after-timeout")
    request = prepared(user, [primary, fallback])
    mock = MockAdapter(("TIMEOUT", "SUCCESS"))
    result = run(user, request, mock)
    assert result.state == "RECONCILING"
    assert mock.calls == 1
    assert Operation.objects.get(pk=request.operation_id).state == "RECONCILING"
    assert Attempt.objects.filter(request=request, state="UNKNOWN").count() == 1
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    primary.quota.refresh_from_db()
    assert primary.quota.reserved == 1 and primary.quota.blocked_reason
    assert run(user, request, mock).state == "RECONCILING"
    assert mock.calls == 1
    no_debit(user)


def test_retries_stop_at_bounded_attempts_and_release_known_failure_once():
    user, route = student(), config()
    request = prepared(user, [route])
    mock = MockAdapter(("UNAVAILABLE",) * 10)
    result = run(user, request, mock)
    assert result.state == "RELEASED"
    assert mock.calls == 2
    assert Attempt.objects.filter(request=request).count() == 2
    assert Wallet.objects.get(owner=user).reserved_balance == 0
    assert run(user, request, mock).state == "RELEASED" and mock.calls == 2
    no_debit(user)


def test_missing_approval_fallback_is_skipped_without_dispatch():
    user = student()
    primary = config()
    fallback = config(model="unapproved-fallback", approval=False)
    request = prepared(user, [primary, fallback])
    mock = MockAdapter(("UNAVAILABLE",) * 10)
    run(user, request, mock)
    assert mock.calls <= 2
    assert not Attempt.objects.filter(request=request, config=fallback).exists()
    no_debit(user)


def test_changed_consent_before_dispatch_prevents_any_adapter_call():
    user = student()
    request = prepared(user)
    Account.objects.filter(pk=user.pk).update(consent_version=1)
    mock = MockAdapter()
    try:
        run(user, request, mock)
    except IdentityError:
        pass
    assert mock.calls == 0
    no_debit(user)


def test_nonlocal_execution_cannot_use_the_synthetic_fixture_port(settings):
    user = student()
    request = prepared(user)
    settings.LOCAL = False
    mock = MockAdapter()
    with pytest.raises(IdentityError):
        run(user, request, mock)
    assert mock.calls == 0
    no_debit(user)


def test_routing_events_and_privacy_audit_store_metadata_not_prompts_or_outputs(caplog):
    user = student()
    request = prepared(user)
    run(user, request)
    events = list(RoutingEvent.objects.filter(request=request).values())
    assert events
    rendered = (
        json.dumps(events, default=str)
        + json.dumps(list(PrivacyAudit.objects.filter(actor_id=user.pk).values()), default=str)
        + caplog.text
    )
    assert "Synthetic scholarship information." not in rendered
    assert "https://example.invalid/synthetic" not in rendered
    assert '"claims"' not in rendered
    assert user.email not in rendered
    assert all(event["provider"] == "MOCK" for event in events)
    assert any(event["approval_id"] is not None for event in events)
    assert all(event["consent_version"] == 0 for event in events)


def test_result_and_attempt_evidence_cannot_be_mutated_after_success():
    user = student()
    request = prepared(user)
    run(user, request)
    output = GatewayResult.objects.get(request=request)
    with pytest.raises(DatabaseError), transaction.atomic():
        GatewayResult.objects.filter(pk=output.pk).update(payload={"invented": "fact"})
    with pytest.raises(DatabaseError), transaction.atomic():
        RoutingEvent.objects.filter(request=request).update(code="REWRITTEN")
    with pytest.raises(DatabaseError), transaction.atomic():
        Attempt.objects.filter(request=request).update(estimate=0)


def test_gateway_cannot_dispatch_inside_an_outer_transaction():
    user = student()
    request, mock = prepared(user), MockAdapter()
    with transaction.atomic(), pytest.raises(IdentityError) as caught:
        run(user, request, mock)
    assert caught.value.code == "GATEWAY_TRANSACTION_BOUNDARY"
    assert mock.calls == 0 and not Attempt.objects.exists()
    no_debit(user)


@pytest.mark.parametrize("usage", [(2, "REQUESTS"), (1, "NEURONS"), (True, "REQUESTS")])
def test_untrustworthy_usage_keeps_capacity_and_credits_reconciling(usage):
    class WrongUsage(MockAdapter):
        def execute(self, request, timeout_seconds):
            response = super().execute(request, timeout_seconds)
            return AdapterResponse(response.output, *usage)

    user, route = student(), config()
    request = prepared(user, [route])
    assert run(user, request, WrongUsage()).state == "RECONCILING"
    assert Attempt.objects.get(request=request).state == "UNKNOWN"
    route.quota.refresh_from_db()
    assert route.quota.reserved == 1 and route.quota.blocked_reason
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    no_debit(user)


def test_adapter_exception_message_never_becomes_telemetry_or_a_billable_result(caplog):
    class CrashingMock(MockAdapter):
        def execute(self, request, timeout_seconds):
            raise RuntimeError("PRIVATE_SENTINEL@example.invalid secret-prompt-value")

    user = student()
    request = prepared(user)
    assert run(user, request, CrashingMock()).state == "RECONCILING"
    events = json.dumps(list(RoutingEvent.objects.values()), default=str)
    assert "PRIVATE_SENTINEL" not in events + caplog.text
    assert "secret-prompt-value" not in events + caplog.text
    no_debit(user)


def test_unknown_previous_window_blocks_a_fresh_window_for_the_same_provider_account():
    user, first = student(), config()
    request = prepared(user, [first])
    assert run(user, request, MockAdapter(("TIMEOUT",))).state == "RECONCILING"
    old = QuotaWindow.objects.get(pk=first.quota_id)
    later = old.ends_at + timedelta(seconds=1)
    fresh = QuotaWindow.objects.create(
        provider=old.provider,
        account_ref=old.account_ref,
        unit=old.unit,
        starts_at=old.ends_at,
        ends_at=old.ends_at + timedelta(days=1),
        hard_limit=100,
        observed_used=0,
        observed_at=later,
        valid_until=later + timedelta(hours=1),
        measurement_ref=uuid.uuid4(),
        free_only_confirmed=True,
    )
    with patch("ai_gateway.services.timezone.now", return_value=later):
        next_route = config(quota=fresh, model="next-window-model")
        next_request, mock = prepared(user, [next_route]), MockAdapter()
        assert run(user, next_request, mock).state == "RELEASED"
        assert mock.calls == 0
    old.refresh_from_db()
    assert old.reserved == 1 and old.blocked_reason
    assert not Attempt.objects.filter(request=next_request).exists()
    no_debit(user)


def test_current_global_stop_is_rechecked_before_dispatch_without_new_logical_counter():
    user = student()
    request = prepared(user)
    policy = credits.initialize_policy()
    assert policy.global_ai_cap == 100
    admin = student(role="ADMIN", admin_scopes=["COST_POLICY"])
    proof = IdentitySession.objects.create(
        account=admin,
        digest=digest(str(uuid.uuid4())),
        epoch=admin.session_epoch,
        expires_at=timezone.now() + timedelta(hours=1),
        mfa_verified_at=timezone.now(),
    )
    credits.publish_policy(
        admin,
        proof,
        {
            **{field: getattr(policy, field) for field in credits.POLICY_FIELDS},
            "global_ai_cap": 0,
            "reason": "Synthetic emergency AI stop.",
        },
        policy.version,
    )
    mock = MockAdapter()
    try:
        run(user, request, mock)
    except IdentityError:
        pass
    assert mock.calls == 0
    assert GlobalDay.objects.get().admitted_operations == 1
    no_debit(user)


@pytest.mark.parametrize("cap", [8001, 10000])
def test_cloudflare_experimental_guardrail_cannot_be_raised_to_full_free_allocation(cap):
    with pytest.raises(DatabaseError), transaction.atomic():
        config(provider="CLOUDFLARE", quota_changes={"hard_limit": cap})
    assert not Attempt.objects.exists()


@pytest.mark.parametrize(
    "changed",
    [
        {"state": "SUSPENDED"},
        {"state": "DELETION_PENDING"},
        {"email_verified_at": None},
        {"role": "ADMIN"},
    ],
)
def test_owner_authority_is_rechecked_after_preparation(changed):
    user = student()
    request = prepared(user)
    Account.objects.filter(pk=user.pk).update(**changed)
    mock = MockAdapter()
    with pytest.raises(IdentityError):
        run(user, request, mock)
    assert mock.calls == 0
    assert not Attempt.objects.exists()
    no_debit(user)


@pytest.mark.parametrize(
    "target",
    [
        "ai_gateway.services.GatewayResult.objects.create",
        "credits.services.SavedOutput.objects.create",
    ],
)
def test_unsaved_output_cannot_commit_a_debit_and_is_recoverable_by_expiry(target):
    user = student()
    request = prepared(user)
    with patch(target, side_effect=DatabaseError("Synthetic persistence outage")):
        with pytest.raises(DatabaseError):
            run(user, request)
    no_debit(user)
    attempt = Attempt.objects.get(request=request)
    assert attempt.state == "DISPATCH_INTENT"
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    assert services.expire_attempts(now=attempt.lease_until) == 1
    assert GatewayRequest.objects.get(pk=request.pk).state == "RECONCILING"
    no_debit(user)


def intent(user, route, request):
    with transaction.atomic():
        token = credits.claim(user.pk, request.operation_id)
        request.state = "RUNNING"
        request.save(update_fields=["state"])
        attempt = services.reserve_capacity(route.pk, request.pk, 1, token)
    return token, attempt


def test_database_rejects_unknown_attempt_with_a_running_credit_operation():
    user, route = student(), config()
    request = prepared(user, [route])
    _, attempt = intent(user, route, request)
    with pytest.raises(DatabaseError), transaction.atomic():
        Attempt.objects.filter(pk=attempt.pk).update(state="UNKNOWN")
        QuotaWindow.objects.filter(pk=route.quota_id).update(blocked_reason="USAGE_UNKNOWN")
    assert Attempt.objects.get(pk=attempt.pk).state == "DISPATCH_INTENT"
    assert Operation.objects.get(pk=request.operation_id).state == "RUNNING"
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    no_debit(user)


def test_database_rejects_release_with_an_unresolved_dispatch_intent():
    user, route = student(), config()
    request = prepared(user, [route])
    token, _ = intent(user, route, request)
    with pytest.raises(DatabaseError), transaction.atomic():
        credits.fail(user.pk, request.operation_id, token)
        GatewayRequest.objects.filter(pk=request.pk).update(state="RELEASED")
    assert GatewayRequest.objects.get(pk=request.pk).state == "RUNNING"
    assert Wallet.objects.get(owner=user).reserved_balance == 1
    no_debit(user)


def test_old_window_intent_lease_is_bounded_and_still_blocks_new_window_dispatch():
    user = student()
    now = timezone.now()
    first = config(quota_changes={"ends_at": now + timedelta(seconds=2)})
    first_request = prepared(user, [first])
    _, prior = intent(user, first, first_request)
    old = QuotaWindow.objects.get(pk=first.quota_id)
    later = old.ends_at + timedelta(seconds=1)
    assert prior.lease_until <= old.ends_at < later
    fresh = QuotaWindow.objects.create(
        provider=old.provider,
        account_ref=old.account_ref,
        unit=old.unit,
        starts_at=old.ends_at,
        ends_at=old.ends_at + timedelta(days=1),
        hard_limit=100,
        observed_used=0,
        observed_at=later,
        valid_until=later + timedelta(hours=1),
        measurement_ref=uuid.uuid4(),
        free_only_confirmed=True,
    )
    with patch("ai_gateway.services.timezone.now", return_value=later):
        next_route = config(quota=fresh, model="unexpired-old-window-model")
        next_request, mock = prepared(user, [next_route]), MockAdapter()
        assert run(user, next_request, mock).state == "RELEASED"
        assert mock.calls == 0
    assert not Attempt.objects.filter(request=next_request).exists()
    no_debit(user)


def signed_in_client(user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    now = timezone.now()
    IdentitySession.objects.create(
        account=user,
        digest=digest(client.session.session_key),
        epoch=user.session_epoch,
        expires_at=now + timedelta(days=1),
    )
    return client


def test_capabilities_expose_fail_closed_state_without_sensitive_configuration():
    user = student()
    response = signed_in_client(user).get("/api/v1/ai/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["live_execution_available"] is False
    assert body["mock_client_execution_available"] is False
    assert body["reason_codes"]
    assert "key" not in json.dumps(body).lower()
    assert "account_ref" not in json.dumps(body)


def test_anonymous_and_admin_cannot_use_student_gateway_capabilities():
    assert APIClient().get("/api/v1/ai/capabilities").status_code in {401, 403}
    admin = student(role="ADMIN")
    assert signed_in_client(admin).get("/api/v1/ai/capabilities").status_code == 403


def test_client_cannot_execute_configure_or_fabricate_approval_through_public_api():
    client = signed_in_client(student())
    for path in ["ai/operations", "ai/run", "ai/providers", "ai/approvals"]:
        assert client.post("/api/v1/" + path, {}, format="json").status_code in {403, 404, 405}
