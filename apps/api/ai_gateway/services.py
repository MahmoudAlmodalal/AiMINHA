"""Server-only synthetic orchestration; all real provider transports remain closed.

No raw prompt is persisted. Dispatch intent commits before adapter invocation;
unknown effects retain both physical capacity and financial reservations.
"""

import secrets
import time
from datetime import datetime, timedelta
from typing import Any

from credits import services as credits
from credits.models import GlobalDay
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from identity.models import Account
from identity.security import IdentityError, audit, digest, require_student
from privacy.services import has_consent

from ai_gateway.adapters import AdapterFailure, AdapterResponse, MockAdapter, ProviderAdapter
from ai_gateway.models import (
    Attempt,
    GatewayRequest,
    GatewayResult,
    ProviderApproval,
    ProviderCircuit,
    ProviderConfig,
    QuotaWindow,
    RoutingEvent,
)
from ai_gateway.validation import (
    AdapterRequest,
    Classification,
    GroundingEvidence,
    ValidationFailure,
    classify_origins,
    validate_output,
)

MAX_ATTEMPTS = 3
FAILURE_CODES = {
    "PROVIDER_UNAVAILABLE",
    "RATE_LIMITED",
    "PROVIDER_TIMEOUT",
    "REAL_TRANSPORT_UNAVAILABLE",
    "MOCK_SYNTHETIC_ONLY",
    "INVALID_TIMEOUT",
}


def _event(
    user: Account | None,
    config: ProviderConfig | None,
    code: str,
    request: GatewayRequest | None = None,
    classification: str = "PUBLIC/SYNTHETIC",
    consent_version: int | None = None,
) -> None:
    RoutingEvent.objects.create(
        owner=user,
        request=request,
        provider=config.provider if config else "",
        model=config.model if config else "",
        classification=classification,
        approval_id=config.approval_id if config else None,
        consent_version=consent_version,
        code=code,
    )
    audit(
        user,
        "ai_routing",
        "ALLOW" if code in {"DISPATCH_INTENT", "ACCEPTED"} else "DENY",
        resource=request.pk if request else None,
        reason=code,
    )


def _quota(config: ProviderConfig) -> QuotaWindow:
    return QuotaWindow.objects.select_for_update().get(pk=config.quota_id)


def _capacity(quota: QuotaWindow, estimate: int = 0) -> None:
    now = timezone.now()
    if (
        quota.blocked_reason
        or not quota.free_only_confirmed
        or not quota.measurement_ref
        or not quota.starts_at <= now < quota.ends_at
        or not quota.observed_at <= now < quota.valid_until
    ):
        raise IdentityError("CAPACITY_UNKNOWN", 503, "AI capacity cannot be verified")
    # Unknown calls survive their original window. A new window cannot hide them.
    if (
        Attempt.objects.filter(
            quota__provider=quota.provider,
            quota__account_ref=quota.account_ref,
            quota__unit=quota.unit,
            state="UNKNOWN",
        ).exists()
        or Attempt.objects.filter(
            quota__provider=quota.provider,
            quota__account_ref=quota.account_ref,
            quota__unit=quota.unit,
            state="DISPATCH_INTENT",
        )
        .filter(Q(lease_until__lte=now) | ~Q(quota_id=quota.pk))
        .exists()
    ):
        raise IdentityError("CAPACITY_UNKNOWN", 503, "AI capacity cannot be verified")
    ceiling = min(quota.hard_limit, 8000) if quota.provider == "CLOUDFLARE" else quota.hard_limit
    if quota.provider == "CLOUDFLARE" and quota.unit != "NEURONS":
        raise IdentityError("CAPACITY_UNKNOWN", 503, "AI capacity cannot be verified")
    if quota.observed_used + quota.consumed + quota.reserved + estimate > ceiling:
        raise IdentityError("PROVIDER_BUDGET_EXHAUSTED", 503, "AI capacity is exhausted")


def _check_route(
    user: Account,
    config: ProviderConfig,
    classification: str,
    consent_version: int,
    origins: tuple[str, ...],
    *,
    transport: bool = True,
    admission: bool = True,
) -> QuotaWindow:
    try:
        requested = Classification(classification)
    except ValueError:
        raise IdentityError(
            "INVALID_CLASSIFICATION", 400, "A valid input classification is required"
        ) from None
    floor = classify_origins(origins)
    if requested == Classification.PROHIBITED or floor == Classification.PROHIBITED:
        raise IdentityError("PROHIBITED_INPUT")
    if requested != floor:
        raise IdentityError("CLASSIFICATION_MISMATCH")
    if requested == Classification.STUDENT_PRIVATE and config.provider not in {
        "CLOUDFLARE",
        "GROQ",
    }:
        raise IdentityError("PRIVATE_PROVIDER_FORBIDDEN")
    if user.consent_version != consent_version:
        raise IdentityError("CONSENT_CHANGED")
    if requested == Classification.STUDENT_PRIVATE and not has_consent(
        user, "PERSONAL_AI", consent_version
    ):
        raise IdentityError("PERSONAL_AI_CONSENT_REQUIRED")
    if not config.enabled:
        raise IdentityError("PROVIDER_DISABLED", 503, "AI provider is unavailable")
    if config.classification != classification:
        raise IdentityError("PROVIDER_NOT_APPROVED", 503, "No approved AI route is available")
    quota = _quota(config)
    approval = ProviderApproval.objects.select_for_update().filter(pk=config.approval_id).first()
    now = timezone.now()
    names = ("provider", "model", "classification", "data_type", "purpose", "region")
    if (
        approval is None
        or any(getattr(config, name) != getattr(approval, name) for name in names)
        or approval.revoked_at is not None
        or not approval.approved_at <= now < approval.expires_at
        or (requested == Classification.STUDENT_PRIVATE and not approval.private_controls_approved)
    ):
        raise IdentityError("PROVIDER_NOT_APPROVED", 503, "No approved AI route is available")
    if requested == Classification.STUDENT_PRIVATE:
        # A generic PERSONAL_AI disclosure is not a provider/model/region/purpose bundle.
        raise IdentityError(
            "SCOPED_PRIVATE_PIPELINE_UNAVAILABLE", 503, "Private AI processing is unavailable"
        )
    _capacity(quota, config.max_units_per_attempt if admission else 0)
    if transport and config.provider != "MOCK":
        raise IdentityError("REAL_TRANSPORT_UNAVAILABLE", 503, "AI execution is unavailable")
    if config.provider == "MOCK" and (not settings.LOCAL or origins != ("SYNTHETIC_FIXTURE",)):
        raise IdentityError("MOCK_SYNTHETIC_ONLY")
    return quota


def authorize(
    owner_id: Any,
    config_id: Any,
    classification: str,
    consent_version: int,
    origins: tuple[str, ...],
) -> ProviderConfig:
    """Metadata-only preflight. A denial is committed before the safe error is raised."""
    failure = None
    with transaction.atomic():
        user = Account.objects.select_for_update().get(pk=owner_id)
        require_student(user)
        config = ProviderConfig.objects.filter(pk=config_id).first()
        if config is None:
            raise IdentityError("PROVIDER_NOT_APPROVED", 503, "No approved AI route is available")
        try:
            _check_route(user, config, classification, consent_version, origins)
        except IdentityError as error:
            failure = error
        _event(
            user,
            config,
            failure.code if failure else "ROUTE_ELIGIBLE",
            classification=classification
            if classification in tuple(Classification)
            else "PROHIBITED",
            consent_version=consent_version,
        )
    if failure:
        raise failure
    return config


@transaction.atomic
def prepare(
    owner_id: Any, operation_id: Any, route_ids: list[Any], language: str = "en"
) -> GatewayRequest:
    if not settings.LOCAL:
        raise IdentityError("REAL_TRANSPORT_UNAVAILABLE", 503, "AI execution is unavailable")
    user, op = credits.lock_for_gateway(owner_id, operation_id)
    if (
        not isinstance(route_ids, list)
        or not 1 <= len(route_ids) <= MAX_ATTEMPTS
        or len(set(map(str, route_ids))) != len(route_ids)
        or language not in {"en", "ar"}
    ):
        raise IdentityError("INVALID_GATEWAY_REQUEST", 400, "Invalid AI request")
    routes = [str(value) for value in route_ids]
    existing = GatewayRequest.objects.filter(operation=op, owner=user).first()
    if existing is not None:
        if existing.route_ids != routes or existing.language != language:
            raise IdentityError("IDEMPOTENCY_CONFLICT", 409, "Operation already configured")
        return existing
    if op.state != "RESERVED":
        raise IdentityError("OPERATION_NOT_CLAIMABLE", 409, "Operation cannot be dispatched")
    if ProviderConfig.objects.filter(pk__in=routes).count() != len(routes):
        raise IdentityError("PROVIDER_NOT_APPROVED", 503, "No approved AI route is available")
    return GatewayRequest.objects.create(
        owner=user,
        operation=op,
        route_ids=routes,
        language=language,
        consent_version=user.consent_version,
    )


def _request_lock(
    owner_id: Any, request_id: Any, *, active: bool = True
) -> tuple[Account, Any, GatewayRequest]:
    first = GatewayRequest.objects.filter(pk=request_id, owner_id=owner_id).first()
    if first is None:
        raise IdentityError("AI_REQUEST_ACCESS_DENIED")
    user, op = credits.lock_for_gateway(owner_id, first.operation_id, active=active)
    request = GatewayRequest.objects.select_for_update().get(pk=first.pk, owner=user)
    return user, op, request


def _circuit(config: ProviderConfig, quota: QuotaWindow) -> ProviderCircuit:
    scope = f"{config.provider}:{quota.account_ref}:{config.model}"
    item, _ = ProviderCircuit.objects.get_or_create(scope=scope)
    return ProviderCircuit.objects.select_for_update().get(pk=item.pk)


def _circuit_claim(config: ProviderConfig, quota: QuotaWindow) -> None:
    circuit = _circuit(config, quota)
    now = timezone.now()
    if circuit.open_until is not None:
        if now < circuit.open_until or (
            circuit.probe_until is not None and now < circuit.probe_until
        ):
            raise IdentityError("CIRCUIT_OPEN", 503, "AI provider is temporarily unavailable")
        circuit.probe_until = now + timedelta(seconds=config.timeout_seconds + 5)
        circuit.save(update_fields=["probe_until"])


def _circuit_finish(config: ProviderConfig, quota: QuotaWindow, success: bool) -> None:
    circuit = _circuit(config, quota)
    circuit.probe_until = None
    if success:
        circuit.failures, circuit.open_until = 0, None
    else:
        circuit.failures += 1
        if circuit.failures >= 3:
            circuit.open_until = timezone.now() + timedelta(seconds=30)
    circuit.save(update_fields=["probe_until", "failures", "open_until"])


def _current_global_stop(op: Any) -> None:
    # The operation was counted at financial admission. A current hard stop
    # disables new dispatch without re-counting it or changing its price.
    cap = credits.head_lock().policy.global_ai_cap
    day = credits.business_day(timezone.now())
    bucket = GlobalDay.objects.filter(day=day).first()
    usage = bucket.admitted_operations if bucket else 0
    if cap == 0 or usage > cap or (op.captured_day != day and usage >= cap):
        raise IdentityError("GLOBAL_AI_STOP", 503, "AI operation capacity is exhausted")


@transaction.atomic
def reserve_capacity(config_id: Any, request_id: Any, number: int, token: str) -> Attempt:
    """Bookkeeping boundary; reserving capacity grants no real transport authority."""
    first = GatewayRequest.objects.get(pk=request_id)
    user, op, request = _request_lock(first.owner_id, request_id)
    if request.state != "RUNNING" or op.state != "RUNNING" or timezone.now() >= op.reserve_until:
        raise IdentityError("OPERATION_NOT_RUNNING", 409, "Operation is awaiting reconciliation")
    _current_global_stop(op)
    if not token or not secrets.compare_digest(op.fence_digest, digest(token)):
        raise IdentityError("STALE_WORKER_FENCE", 409, "Operation claim is no longer current")
    if number != Attempt.objects.filter(request=request).count() + 1 or number > MAX_ATTEMPTS:
        raise IdentityError("ATTEMPT_LIMIT", 503, "AI attempt limit reached")
    config = ProviderConfig.objects.get(pk=config_id)
    if str(config.pk) not in request.route_ids:
        raise IdentityError("PROVIDER_NOT_APPROVED", 503, "No approved AI route is available")
    quota = _check_route(
        user,
        config,
        request.classification,
        request.consent_version,
        ("SYNTHETIC_FIXTURE",),
        transport=False,
    )
    if Attempt.objects.filter(request=request, state__in=["DISPATCH_INTENT", "UNKNOWN"]).exists():
        raise IdentityError("PRIOR_OUTCOME_UNCERTAIN", 409, "AI result is awaiting reconciliation")
    if Attempt.objects.filter(request=request, config=config).count() >= config.attempt_limit:
        raise IdentityError("ATTEMPT_LIMIT", 503, "AI attempt limit reached")
    _circuit_claim(config, quota)
    item = Attempt.objects.create(
        request=request,
        config=config,
        quota=quota,
        number=number,
        estimate=config.max_units_per_attempt,
        state="DISPATCH_INTENT",
        fence_digest=op.fence_digest,
        approval_id=config.approval_id,
        consent_version=request.consent_version,
        lease_until=min(
            op.reserve_until,
            quota.ends_at,
            quota.valid_until,
            timezone.now() + timedelta(seconds=config.timeout_seconds),
        ),
    )
    quota.reserved += item.estimate
    quota.save(update_fields=["reserved"])
    _event(user, config, "DISPATCH_INTENT", request, consent_version=request.consent_version)
    return item


def _synthetic_request(request: GatewayRequest, config: ProviderConfig) -> AdapterRequest:
    text = (
        "معلومة منحة اصطناعية."
        if request.language == "ar"
        else "Synthetic scholarship information."
    )
    return AdapterRequest(
        input_text="Untrusted synthetic scholarship text.",
        data_class=Classification.PUBLIC_SYNTHETIC,
        purpose=config.purpose,
        language=request.language,
        evidence=(GroundingEvidence("fixture", text, "https://example.invalid/synthetic"),),
        synthetic=True,
    )


def _unknown(
    user: Account,
    request: GatewayRequest,
    item: Attempt | None,
    config: ProviderConfig | None,
    code: str,
) -> GatewayRequest:
    if item is not None and item.state == "DISPATCH_INTENT":
        quota = _quota(config)  # type: ignore[arg-type]
        item.state = "UNKNOWN"
        item.save(update_fields=["state"])
        quota.blocked_reason = "USAGE_UNKNOWN"
        quota.save(update_fields=["blocked_reason"])
        _circuit_finish(config, quota, False)  # type: ignore[arg-type]
    credits.reconcile_system(request.operation_id)
    request.state = "RECONCILING"
    request.save(update_fields=["state"])
    _event(user, config, code, request, consent_version=request.consent_version)
    return request


@transaction.atomic
def _finish(
    owner_id: Any,
    request_id: Any,
    attempt_id: Any,
    token: str,
    response: Any = None,
    failure: AdapterFailure | None = None,
) -> tuple[GatewayRequest, bool]:
    user, op, request = _request_lock(owner_id, request_id, active=False)
    item = Attempt.objects.select_for_update().get(pk=attempt_id, request=request)
    config = ProviderConfig.objects.get(pk=item.config_id)
    quota = _quota(config)
    if item.state != "DISPATCH_INTENT" or request.state != "RUNNING":
        return request, False
    try:
        require_student(user)
        qualified = True
    except IdentityError:
        qualified = False
    if (
        not qualified
        or user.consent_version != request.consent_version
        or timezone.now() >= item.lease_until
        or timezone.now() >= op.reserve_until
        or not secrets.compare_digest(op.fence_digest, digest(token))
    ):
        return _unknown(user, request, item, config, "ACCEPTANCE_AUTHORITY_CHANGED"), False
    try:
        _check_route(
            user,
            config,
            request.classification,
            request.consent_version,
            ("SYNTHETIC_FIXTURE",),
            transport=False,
            admission=False,
        )
    except IdentityError:
        return _unknown(user, request, item, config, "ACCEPTANCE_POLICY_CHANGED"), False
    if failure is not None and failure.outcome_unknown:
        return _unknown(user, request, item, config, "PROVIDER_OUTCOME_UNKNOWN"), False
    if failure is not None:
        code = failure.code if failure.code in FAILURE_CODES else "PROVIDER_FAILURE"
        item.state, item.used = "NOT_EXECUTED", item.estimate
        quota.reserved -= item.estimate
        quota.consumed += item.used
        item.save(update_fields=["state", "used"])
        quota.save(update_fields=["reserved", "consumed"])
        _circuit_finish(config, quota, False)
        _event(user, config, code, request, consent_version=request.consent_version)
        return request, failure.safe_to_retry and code in {"PROVIDER_UNAVAILABLE", "RATE_LIMITED"}
    if (
        not isinstance(response, AdapterResponse)
        or type(response.usage_units) is not int
        or not 0 <= response.usage_units <= item.estimate
        or response.usage_unit != quota.unit
    ):
        return _unknown(user, request, item, config, "USAGE_UNTRUSTWORTHY"), False
    quota.reserved -= item.estimate
    quota.consumed += response.usage_units
    item.used = response.usage_units
    try:
        output = validate_output(response.output, _synthetic_request(request, config))
    except ValidationFailure:
        item.state = "REJECTED"
        item.save(update_fields=["state", "used"])
        quota.save(update_fields=["reserved", "consumed"])
        credits.fail(user.pk, op.pk, token)
        request.state = "RELEASED"
        request.save(update_fields=["state"])
        _circuit_finish(config, quota, True)
        _event(user, config, "UNSUPPORTED_OUTPUT", request, consent_version=request.consent_version)
        return request, False
    item.state = "SUCCEEDED"
    item.save(update_fields=["state", "used"])
    quota.save(update_fields=["reserved", "consumed"])
    GatewayResult.objects.create(request=request, owner=user, payload=output)
    credits.settle(
        user.pk, op.pk, token, {"fixture_id": str(op.fixture_id), "result": "SYNTHETIC_OK"}
    )
    request.state = "SETTLED"
    request.save(update_fields=["state"])
    _circuit_finish(config, quota, True)
    _event(user, config, "ACCEPTED", request, consent_version=request.consent_version)
    return request, False


@transaction.atomic
def _release(owner_id: Any, request_id: Any, token: str) -> GatewayRequest:
    user, op, request = _request_lock(owner_id, request_id, active=False)
    if request.state != "RUNNING":
        return request
    unresolved = Attempt.objects.filter(
        request=request, state__in=["DISPATCH_INTENT", "UNKNOWN", "SUCCEEDED"]
    ).first()
    if unresolved is not None:
        config = ProviderConfig.objects.get(pk=unresolved.config_id)
        return _unknown(user, request, unresolved, config, "PRIOR_OUTCOME_UNCERTAIN")
    if user.state != "ACTIVE" or timezone.now() >= op.reserve_until:
        return _unknown(user, request, None, None, "ADMISSION_AUTHORITY_CHANGED")
    credits.fail(user.pk, op.pk, token)
    request.state = "RELEASED"
    request.save(update_fields=["state"])
    _event(user, None, "NO_ELIGIBLE_ROUTE", request, consent_version=request.consent_version)
    return request


def run(
    owner_id: Any, request_id: Any, registry: dict[str, ProviderAdapter] | None = None
) -> GatewayRequest:
    if not settings.LOCAL:
        raise IdentityError("REAL_TRANSPORT_UNAVAILABLE", 503, "AI execution is unavailable")
    if transaction.get_connection().in_atomic_block:
        raise IdentityError(
            "GATEWAY_TRANSACTION_BOUNDARY", 409, "AI dispatch requires a committed boundary"
        )
    with transaction.atomic():
        user, op, request = _request_lock(owner_id, request_id)
        if request.state != "PENDING":
            return request  # Stable retry never starts another uncertain execution.
        if user.consent_version != request.consent_version:
            return _unknown(user, request, None, None, "CONSENT_CHANGED")
        token = credits.claim(user.pk, op.pk)
        request.state = "RUNNING"
        request.save(update_fields=["state"])
    # No provider invocation while a database transaction/row lock is held.
    registry = registry if registry is not None else {"MOCK": MockAdapter()}
    for config_id in request.route_ids:
        config = ProviderConfig.objects.get(pk=config_id)
        for _ in range(config.attempt_limit):
            with transaction.atomic():
                user, _, current = _request_lock(owner_id, request_id)
                if current.state != "RUNNING":
                    return current
                try:
                    _check_route(
                        user,
                        config,
                        current.classification,
                        current.consent_version,
                        ("SYNTHETIC_FIXTURE",),
                    )
                    number = Attempt.objects.filter(request=current).count() + 1
                    item = reserve_capacity(config.pk, current.pk, number, token)
                except IdentityError as error:
                    _event(
                        user, config, error.code, current, consent_version=current.consent_version
                    )
                    break
            adapter = registry.get(config.provider)
            if config.provider != "MOCK" or not isinstance(adapter, MockAdapter):
                # Registry injection cannot install a real transport or bypass the gate.
                failure = AdapterFailure("REAL_TRANSPORT_UNAVAILABLE")
                response = None
            else:
                started = time.monotonic()
                try:
                    response = adapter.execute(
                        _synthetic_request(request, config), config.timeout_seconds
                    )
                    failure = None
                    if time.monotonic() - started >= config.timeout_seconds:
                        response, failure = (
                            None,
                            AdapterFailure("PROVIDER_TIMEOUT", outcome_unknown=True),
                        )
                except AdapterFailure as error:
                    response, failure = None, error
                except Exception:
                    response, failure = (
                        None,
                        AdapterFailure("PROVIDER_FAILURE", outcome_unknown=True),
                    )
            current, retry = _finish(owner_id, request_id, item.pk, token, response, failure)
            if current.state != "RUNNING":
                return current
            if not retry:
                return _release(owner_id, request_id, token)
    return _release(owner_id, request_id, token)


def expire_attempts(now: datetime | None = None) -> int:
    now = now or timezone.now()
    ids = list(
        Attempt.objects.filter(state="DISPATCH_INTENT", lease_until__lte=now)
        .order_by("lease_until")
        .values_list("pk", flat=True)[:100]
    )
    count = 0
    for attempt_id in ids:
        with transaction.atomic():
            first = Attempt.objects.select_related("request").get(pk=attempt_id)
            user, _, request = _request_lock(first.request.owner_id, first.request_id, active=False)
            item = Attempt.objects.select_for_update().get(pk=attempt_id)
            if item.state == "DISPATCH_INTENT" and item.lease_until <= now:
                config = ProviderConfig.objects.get(pk=item.config_id)
                _unknown(user, request, item, config, "DISPATCH_LEASE_EXPIRED")
                count += 1
    return count
