import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PrivacyAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(null=True)
    resource_id = models.UUIDField(null=True)
    action = models.CharField(max_length=64)
    outcome = models.CharField(max_length=12)
    reason = models.CharField(max_length=64, blank=True)
    correlation_id = models.UUIDField(null=True)
    recorded_at = models.DateTimeField(default=timezone.now)


class Disclosure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(
        max_length=24,
        choices=[("TERMS", "Terms"), ("PRIVACY", "Privacy"), ("PERSONAL_AI", "Personal AI")],
    )
    version = models.PositiveIntegerField()
    disclosure = models.TextField()
    available = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purpose", "version"], name="privacy_disclosure_version_unique"
            )
        ]


class ConsentRecord(models.Model):
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    disclosure = models.ForeignKey(Disclosure, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    state = models.CharField(max_length=8, choices=[("GRANTED", "Granted"), ("REVOKED", "Revoked")])
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "version"], name="privacy_consent_version_unique"
            )
        ]


class LegalEnvelope(models.Model):
    """Independent approval evidence; never created or approved by an ordinary Admin API."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    approved = models.BooleanField(default=False)
    min_days = models.PositiveIntegerField()
    max_days = models.PositiveIntegerField()
    evidence_ref = models.UUIDField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_days__gte=1, max_days__gte=models.F("min_days")),
                name="privacy_valid_legal_bounds",
            )
        ]


class RetentionPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(unique=True)
    recovery_days = models.PositiveIntegerField(default=30)
    recovery_timezone = models.CharField(max_length=20, default="UTC")
    cutoff_algorithm = models.CharField(max_length=24, default="UTC_ELAPSED_DAYS")
    legal_envelope = models.ForeignKey(LegalEnvelope, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(recovery_days__gte=1), name="privacy_positive_recovery_days"
            )
        ]


class RetentionHead(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    policy = models.ForeignKey(RetentionPolicy, on_delete=models.PROTECT)


class DeletionRequest(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING"
        RESTORED = "RESTORED"
        PURGING = "PURGING"
        PURGED = "PURGED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    policy = models.ForeignKey(RetentionPolicy, on_delete=models.PROTECT)
    state = models.CharField(max_length=12, choices=State, default=State.PENDING)
    recovery_days = models.PositiveIntegerField()
    recovery_timezone = models.CharField(max_length=20, default="UTC")
    cutoff_algorithm = models.CharField(max_length=24, default="UTC_ELAPSED_DAYS")
    confirmed_at = models.DateTimeField()
    restore_until = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(state__in=["PENDING", "PURGING"]),
                name="privacy_one_pending_deletion",
            ),
            models.CheckConstraint(
                condition=models.Q(restore_until__gt=models.F("confirmed_at")),
                name="privacy_valid_deletion_cutoff",
            ),
        ]


class PrivateAsset(models.Model):
    """Authorization/object-version projection, not an upload or storage implementation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    object_key = models.UUIDField(default=uuid.uuid4)
    object_version = models.CharField(max_length=128)
    state = models.CharField(max_length=16, default="QUARANTINED")
    declared_size = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["id", "owner"], name="privacy_asset_owner_key")
        ]


class TicketAccess(models.Model):
    """Minimal support authorization projection; ticket workflows belong to Phase13."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ticket_access"
    )
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="support_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["id", "owner"], name="privacy_ticket_owner_key")
        ]


class TicketShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ticket = models.ForeignKey(TicketAccess, on_delete=models.PROTECT)
    asset = models.ForeignKey(PrivateAsset, on_delete=models.PROTECT)
    revoked_at = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ticket", "asset"], name="privacy_exact_ticket_share")
        ]


class FilePurgeTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deletion = models.ForeignKey(DeletionRequest, on_delete=models.PROTECT)
    asset = models.ForeignKey(PrivateAsset, on_delete=models.PROTECT)
    object_key = models.UUIDField()
    object_version = models.CharField(max_length=128)
    state = models.CharField(max_length=24, default="BLOCKED_STORAGE")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["deletion", "asset"], name="privacy_purge_once")
        ]
