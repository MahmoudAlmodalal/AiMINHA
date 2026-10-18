"""Private durable inbox and immutable, source-bound deadline revisions (R18)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationPreference(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=0)
    timezone = models.CharField(max_length=100, default="Asia/Hebron")
    deadline_enabled = models.BooleanField(default=True)
    source_enabled = models.BooleanField(default=True)
    document_enabled = models.BooleanField(default=True)


class DeadlineEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scholarship = models.ForeignKey("catalog.Scholarship", on_delete=models.PROTECT)
    round_key = models.CharField(max_length=64)
    revision = models.PositiveIntegerField(default=0)
    current = models.ForeignKey(
        "DeadlineVersion", null=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scholarship", "round_key"], name="notifications_round_event"
            )
        ]


class DeadlineVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(DeadlineEvent, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    state = models.CharField(
        max_length=12, choices=[(value, value) for value in ("CONFIRMED", "UNKNOWN", "CANCELLED")]
    )
    closes_at = models.DateTimeField(null=True)
    source_timezone = models.CharField(max_length=100, blank=True)
    source_round = models.JSONField(default=dict)
    reason = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "version"], name="notifications_event_version"
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=["CONFIRMED", "UNKNOWN", "CANCELLED"]),
                name="notifications_deadline_state",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(state="CONFIRMED", closes_at__isnull=False)
                    & ~models.Q(source_timezone="")
                )
                | (~models.Q(state="CONFIRMED") & models.Q(closes_at__isnull=True)),
                name="notifications_confirmed_instant",
            ),
        ]


class DeadlineReminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.ForeignKey(DeadlineEvent, on_delete=models.PROTECT)
    event_version = models.ForeignKey(DeadlineVersion, on_delete=models.PROTECT)
    offset_minutes = models.PositiveIntegerField()
    due_at = models.DateTimeField()
    status = models.CharField(
        max_length=12,
        default="SCHEDULED",
        choices=[(value, value) for value in ("SCHEDULED", "DELIVERED", "CANCELLED")],
    )
    delivered_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)
    cancel_reason = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "event", "event_version", "offset_minutes"],
                condition=models.Q(status__in=["SCHEDULED", "DELIVERED"]),
                name="notifications_once_per_offset",
            ),
            models.CheckConstraint(
                condition=models.Q(offset_minutes__in=[20160, 10080, 4320, 1440]),
                name="notifications_offset_known",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status="SCHEDULED", delivered_at__isnull=True, cancelled_at__isnull=True
                )
                | models.Q(
                    status="DELIVERED", delivered_at__isnull=False, cancelled_at__isnull=True
                )
                | (
                    models.Q(
                        status="CANCELLED", delivered_at__isnull=True, cancelled_at__isnull=False
                    )
                    & ~models.Q(cancel_reason="")
                ),
                name="notifications_reminder_terminal",
            ),
        ]
        indexes = [models.Index(fields=["status", "due_at"], name="notifications_due")]


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event_id = models.UUIDField()
    event_version = models.PositiveIntegerField()
    category = models.CharField(
        max_length=24,
        choices=[(value, value) for value in ("DEADLINE", "SOURCE_CHANGE", "DOCUMENT_MISSING")],
    )
    reminder = models.OneToOneField(
        DeadlineReminder, null=True, on_delete=models.PROTECT, related_name="notification"
    )
    application = models.ForeignKey("applications.Application", null=True, on_delete=models.PROTECT)
    scholarship = models.ForeignKey("catalog.Scholarship", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "event_id", "event_version", "category"],
                name="notifications_inbox_once",
            ),
            models.CheckConstraint(
                condition=models.Q(application__isnull=False, scholarship__isnull=True)
                | models.Q(application__isnull=True, scholarship__isnull=False),
                name="notifications_one_destination",
            ),
            models.CheckConstraint(
                condition=models.Q(category="DEADLINE", reminder__isnull=False)
                | models.Q(
                    category__in=["SOURCE_CHANGE", "DOCUMENT_MISSING"], reminder__isnull=True
                ),
                name="notifications_typed_category",
            ),
        ]
        indexes = [models.Index(fields=["owner", "-created_at"], name="notifications_owner_inbox")]


class WorkerCursor(models.Model):
    """Recoverable bounded sweeps; a crash never advances an unfinished batch."""

    name = models.CharField(primary_key=True, max_length=32)
    last_id = models.UUIDField(null=True)


class NotificationAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(null=True)
    resource_id = models.UUIDField(null=True)
    action = models.CharField(max_length=64)
    outcome = models.CharField(max_length=8, default="ALLOW")
    reason = models.CharField(max_length=64, blank=True)
    correlation_id = models.UUIDField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
