"""Credit journals and captured entitlements. No provider execution lives here."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

SERVICES = ["MATCHING_AI", "CV_EXTRACTION", "DOCUMENT_NEW"]
STATES = ["RESERVED", "RUNNING", "RECONCILING", "SETTLED", "RELEASED"]


class CreditPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(unique=True)
    signup_grant = models.PositiveIntegerField(default=30)
    daily_spend_cap = models.PositiveIntegerField(default=6)
    global_ai_cap = models.PositiveIntegerField(default=100)
    matching_price = models.PositiveIntegerField(default=1)
    cv_price = models.PositiveIntegerField(default=4)
    document_price = models.PositiveIntegerField(default=6)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    session_proof = models.ForeignKey(
        "identity.IdentitySession", null=True, on_delete=models.PROTECT
    )
    reason = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(matching_price__gte=1, cv_price__gte=1, document_price__gte=1),
                name="credits_positive_prices",
            ),
        ]


class PolicyHead(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    policy = models.ForeignKey(CreditPolicy, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(id=1), name="credits_single_head")]


class Wallet(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT
    )
    posted_balance = models.BigIntegerField(default=0)
    reserved_balance = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(posted_balance__gte=0, reserved_balance__gte=0)
                    & Q(posted_balance__gte=models.F("reserved_balance"))
                ),
                name="credits_wallet_nonnegative",
            )
        ]


class StudentDay(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    day = models.DateField()
    spent = models.PositiveBigIntegerField(default=0)
    reserved = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "day"], name="credits_student_day")]


class GlobalDay(models.Model):
    day = models.DateField(primary_key=True)
    admitted_operations = models.PositiveBigIntegerField(default=0)


class SyntheticInput(models.Model):
    """Local test port: an opaque fixture, never a student document/profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class Operation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    service = models.CharField(max_length=20, choices=[(x, x) for x in SERVICES])
    state = models.CharField(max_length=12, choices=[(x, x) for x in STATES], default="RESERVED")
    price = models.PositiveIntegerField()
    policy = models.ForeignKey(CreditPolicy, on_delete=models.PROTECT)
    captured_day = models.DateField()
    key_digest = models.CharField(max_length=64)
    request_digest = models.CharField(max_length=64)
    fixture = models.ForeignKey(SyntheticInput, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    reserve_until = models.DateTimeField()
    reconciliation_started_at = models.DateTimeField(null=True)
    resolution_due_at = models.DateTimeField(null=True)
    attempt = models.PositiveIntegerField(default=0)
    fence_digest = models.CharField(max_length=64, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "key_digest"], name="credits_owner_idempotency"
            ),
            models.CheckConstraint(
                condition=Q(service__in=SERVICES, state__in=STATES, price__gte=1),
                name="credits_operation_values",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "created_at"], name="credits_owner_operations"),
            models.Index(fields=["state", "reserve_until"], name="credits_expired_operations"),
        ]


class Hold(models.Model):
    operation = models.OneToOneField(Operation, primary_key=True, on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()
    state = models.CharField(
        max_length=8, default="ACTIVE", choices=[(x, x) for x in ["ACTIVE", "SETTLED", "RELEASED"]]
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=1, state__in=["ACTIVE", "SETTLED", "RELEASED"]),
                name="credits_hold_values",
            )
        ]


class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(
        max_length=12, choices=[("SIGNUP_GRANT", "SIGNUP_GRANT"), ("DEBIT", "DEBIT")]
    )
    amount = models.BigIntegerField()
    operation = models.OneToOneField(Operation, null=True, on_delete=models.PROTECT)
    policy = models.ForeignKey(CreditPolicy, on_delete=models.PROTECT)
    reason_code = models.CharField(max_length=40)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner"], condition=Q(kind="SIGNUP_GRANT"), name="credits_once_signup_grant"
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="SIGNUP_GRANT", amount__gte=0, operation__isnull=True)
                    | Q(kind="DEBIT", amount__lt=0, operation__isnull=False)
                ),
                name="credits_entry_sign",
            ),
        ]


class SavedOutput(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation = models.OneToOneField(Operation, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    payload = models.JSONField()
    content_hash = models.CharField(max_length=64)
    validator_version = models.CharField(max_length=40, default="synthetic-v1")
    created_at = models.DateTimeField(default=timezone.now)


class Finalization(models.Model):
    operation = models.OneToOneField(Operation, primary_key=True, on_delete=models.PROTECT)
    outcome = models.CharField(
        max_length=8, choices=[("SETTLED", "SETTLED"), ("RELEASED", "RELEASED")]
    )
    output = models.OneToOneField(SavedOutput, null=True, on_delete=models.PROTECT)
    entry = models.OneToOneField(LedgerEntry, null=True, on_delete=models.PROTECT)
    reason_code = models.CharField(max_length=40)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(outcome="SETTLED", output__isnull=False, entry__isnull=False)
                    | Q(outcome="RELEASED", output__isnull=True, entry__isnull=True)
                ),
                name="credits_finalization_proof",
            )
        ]
