"""Fail-closed AI routing metadata and capacity reservations; never raw prompts."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

PROVIDERS = ["MOCK", "CLOUDFLARE", "GROQ", "GEMINI_FREE", "OPENROUTER_FREE"]
CLASSIFICATIONS = ["PUBLIC/SYNTHETIC", "STUDENT_PRIVATE", "PROHIBITED"]
REQUEST_STATES = ["PENDING", "RUNNING", "RECONCILING", "SETTLED", "RELEASED"]
ATTEMPT_STATES = ["DISPATCH_INTENT", "SUCCEEDED", "NOT_EXECUTED", "REJECTED", "UNKNOWN"]


class ProviderApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=[(x, x) for x in PROVIDERS])
    model = models.CharField(max_length=128)
    classification = models.CharField(max_length=24, choices=[(x, x) for x in CLASSIFICATIONS])
    data_type = models.CharField(max_length=64)
    purpose = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    evidence_ref = models.UUIDField()
    terms_ref = models.UUIDField()
    private_controls_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(provider__in=PROVIDERS, classification__in=CLASSIFICATIONS)
                & Q(expires_at__gt=F("approved_at")),
                name="gateway_approval_values",
            ),
            models.CheckConstraint(
                condition=~Q(classification="STUDENT_PRIVATE")
                | Q(provider__in=["CLOUDFLARE", "GROQ"], private_controls_approved=True),
                name="gateway_private_approval",
            ),
        ]


class QuotaWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=[(x, x) for x in PROVIDERS])
    account_ref = models.UUIDField()
    unit = models.CharField(
        max_length=10, choices=[("REQUESTS", "REQUESTS"), ("NEURONS", "NEURONS")]
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    hard_limit = models.PositiveBigIntegerField()
    observed_used = models.PositiveBigIntegerField(default=0)
    observed_at = models.DateTimeField()
    valid_until = models.DateTimeField()
    measurement_ref = models.UUIDField(null=True)
    free_only_confirmed = models.BooleanField(default=False)
    reserved = models.PositiveBigIntegerField(default=0)
    consumed = models.PositiveBigIntegerField(default=0)
    blocked_reason = models.CharField(max_length=64, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    provider__in=PROVIDERS, unit__in=["REQUESTS", "NEURONS"], hard_limit__gte=1
                )
                & Q(ends_at__gt=F("starts_at"))
                & Q(valid_until__gte=F("observed_at")),
                name="gateway_quota_values",
            ),
            models.CheckConstraint(
                condition=~Q(provider="CLOUDFLARE") | Q(unit="NEURONS", hard_limit__lte=8000),
                name="gateway_cf_ceiling",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "account_ref", "unit"], name="gateway_quota_scope")
        ]


class ProviderConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=20, choices=[(x, x) for x in PROVIDERS])
    model = models.CharField(max_length=128)
    classification = models.CharField(max_length=24, choices=[(x, x) for x in CLASSIFICATIONS])
    data_type = models.CharField(max_length=64)
    purpose = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    approval = models.ForeignKey(ProviderApproval, null=True, on_delete=models.PROTECT)
    quota = models.ForeignKey(QuotaWindow, on_delete=models.PROTECT)
    enabled = models.BooleanField(default=False)
    timeout_seconds = models.PositiveSmallIntegerField(default=10)
    attempt_limit = models.PositiveSmallIntegerField(default=2)
    max_units_per_attempt = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    provider__in=PROVIDERS,
                    classification__in=CLASSIFICATIONS,
                    timeout_seconds__gte=1,
                    timeout_seconds__lte=30,
                    attempt_limit__gte=1,
                    attempt_limit__lte=3,
                    max_units_per_attempt__gte=1,
                ),
                name="gateway_config_values",
            ),
            models.CheckConstraint(
                condition=~Q(classification="STUDENT_PRIVATE")
                | Q(provider__in=["CLOUDFLARE", "GROQ"]),
                name="gateway_private_route",
            ),
        ]


class ProviderCircuit(models.Model):
    scope = models.CharField(max_length=200, primary_key=True)
    failures = models.PositiveIntegerField(default=0)
    open_until = models.DateTimeField(null=True)
    probe_until = models.DateTimeField(null=True)


class GatewayRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    operation = models.OneToOneField("credits.Operation", on_delete=models.PROTECT)
    route_ids = models.JSONField(default=list)
    consent_version = models.PositiveIntegerField()
    classification = models.CharField(
        max_length=24, choices=[(x, x) for x in CLASSIFICATIONS], default="PUBLIC/SYNTHETIC"
    )
    language = models.CharField(max_length=2, choices=[("ar", "ar"), ("en", "en")])
    state = models.CharField(
        max_length=12, choices=[(x, x) for x in REQUEST_STATES], default="PENDING"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    classification__in=CLASSIFICATIONS,
                    language__in=["ar", "en"],
                    state__in=REQUEST_STATES,
                    consent_version__gte=0,
                ),
                name="gateway_request_values",
            )
        ]


class Attempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(GatewayRequest, on_delete=models.PROTECT)
    config = models.ForeignKey(ProviderConfig, on_delete=models.PROTECT)
    quota = models.ForeignKey(QuotaWindow, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    state = models.CharField(
        max_length=16, choices=[(x, x) for x in ATTEMPT_STATES], default="DISPATCH_INTENT"
    )
    estimate = models.PositiveBigIntegerField()
    used = models.PositiveBigIntegerField(null=True)
    fence_digest = models.CharField(max_length=64)
    lease_until = models.DateTimeField()
    approval = models.ForeignKey(ProviderApproval, null=True, on_delete=models.PROTECT)
    consent_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["request", "number"], name="gateway_attempt_number"),
            models.UniqueConstraint(
                fields=["request"],
                condition=Q(state__in=["DISPATCH_INTENT", "UNKNOWN"]),
                name="gateway_one_unresolved",
            ),
            models.CheckConstraint(
                condition=Q(
                    state__in=ATTEMPT_STATES, number__gte=1, estimate__gte=1, consent_version__gte=0
                ),
                name="gateway_attempt_values",
            ),
        ]


class GatewayResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(GatewayRequest, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    payload = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)


class RoutingEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(GatewayRequest, null=True, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    provider = models.CharField(max_length=20, blank=True)
    model = models.CharField(max_length=128, blank=True)
    classification = models.CharField(max_length=24)
    approval = models.ForeignKey(ProviderApproval, null=True, on_delete=models.PROTECT)
    consent_version = models.PositiveIntegerField(null=True)
    code = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
