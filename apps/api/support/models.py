"""Ticket aggregate, append-only thread/history and the versioned working calendar."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone as django_timezone

STATES = ["NEW", "AI_HANDLING", "AWAITING_ADMIN", "AWAITING_STUDENT", "RESOLVED", "CLOSED"]
PRIORITIES = ["CRITICAL", "HIGH", "NORMAL", "LOW"]
AUTHOR_KINDS = ["STUDENT", "ADMIN", "AI"]
EVENT_KINDS = [
    "CREATED",
    "STATE_CHANGED",
    "HUMAN_REQUESTED",
    "HUMAN_ASSIGNED",
    "FIRST_HUMAN_RESPONSE",
    "AI_REPLIED",
    "AI_HANDOFF",
    "AI_LIMIT_REACHED",
    "CLASSIFIED",
    "RATED",
    "REOPENED",
    "SLA_WARNING",
    "SLA_BREACH",
    "AUTO_CLOSED",
    "MESSAGE_ADDED",
]


class SupportCalendar(models.Model):
    """Immutable, versioned working calendar and support lifecycle policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(unique=True)
    timezone = models.CharField(max_length=100, default="Asia/Hebron")
    # Python weekday numbering: Monday=0 .. Sunday=6.
    working_weekdays = models.JSONField(default=list)
    opens_local = models.CharField(max_length=5, default="09:00")
    closes_local = models.CharField(max_length=5, default="17:00")
    holidays = models.JSONField(default=list)
    # Business minutes per priority, exactly as configured by an administrator.
    targets = models.JSONField(default=dict)
    ai_daily_messages = models.PositiveSmallIntegerField(default=5)
    closure_days = models.PositiveSmallIntegerField(default=7)
    reopen_days = models.PositiveSmallIntegerField(default=14)
    rating_edit_days = models.PositiveSmallIntegerField(default=7)
    warning_percent = models.PositiveSmallIntegerField(default=80)
    effective_at = models.DateTimeField(default=django_timezone.now)
    reason = models.CharField(max_length=512)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    session_proof = models.ForeignKey(
        "identity.IdentitySession", null=True, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    ai_daily_messages__gte=1,
                    closure_days__gte=1,
                    reopen_days__gte=1,
                    rating_edit_days__gte=1,
                    warning_percent__gte=1,
                    warning_percent__lte=100,
                ),
                name="support_calendar_positive_windows",
            )
        ]


class SupportCalendarHead(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    policy = models.ForeignKey(SupportCalendar, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="support_single_head")]


class Ticket(models.Model):
    """One student case; the identifier is the shared authorization projection id."""

    access = models.OneToOneField(
        "privacy.TicketAccess", primary_key=True, on_delete=models.PROTECT, related_name="ticket"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_tickets"
    )
    category = models.CharField(max_length=128)
    subject = models.CharField(max_length=256)
    state = models.CharField(max_length=16, default="NEW", choices=[(s, s) for s in STATES])
    priority = models.CharField(
        max_length=8, default="NORMAL", choices=[(p, p) for p in PRIORITIES]
    )
    suggested_category = models.CharField(max_length=128, blank=True)
    suggested_priority = models.CharField(max_length=8, blank=True)
    triage_confidence = models.PositiveSmallIntegerField(null=True)
    triage_reason = models.CharField(max_length=512, blank=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="assigned_support_tickets",
    )
    row_version = models.PositiveIntegerField(default=1)
    head_sequence = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)
    human_requested_at = models.DateTimeField(null=True)
    first_human_response_at = models.DateTimeField(null=True)
    sla_policy = models.ForeignKey(SupportCalendar, null=True, on_delete=models.PROTECT)
    sla_target_minutes = models.PositiveIntegerField(null=True)
    sla_due_at = models.DateTimeField(null=True)
    sla_cycle_no = models.PositiveIntegerField(default=0)
    sla_warning_at = models.DateTimeField(null=True)
    sla_breached_at = models.DateTimeField(null=True)
    ai_failure_streak = models.PositiveSmallIntegerField(default=0)
    ai_message_count = models.PositiveIntegerField(default=0)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    reopen_until = models.DateTimeField(null=True)
    rating_window_until = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(state__in=STATES, priority__in=PRIORITIES),
                name="support_ticket_known_state",
            ),
            models.CheckConstraint(
                condition=models.Q(row_version__gte=1), name="support_ticket_version"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(suggested_priority="", triage_confidence__isnull=True)
                    | models.Q(suggested_priority__in=PRIORITIES, triage_confidence__isnull=False)
                ),
                name="support_ticket_suggestion_consistent",
            ),
            models.CheckConstraint(
                condition=models.Q(sla_cycle_no__gte=0, ai_failure_streak__gte=0),
                name="support_ticket_counters",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="support_owner_tickets"),
            models.Index(fields=["state", "-created_at"], name="support_state_tickets"),
        ]


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="messages")
    sequence = models.PositiveIntegerField()
    author_kind = models.CharField(max_length=8, choices=[(a, a) for a in AUTHOR_KINDS])
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="support_messages",
    )
    body = models.TextField()
    substantive = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ticket", "sequence"], name="support_message_sequence"),
            models.CheckConstraint(
                condition=models.Q(author_kind__in=AUTHOR_KINDS), name="support_message_author_kind"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(author_kind="AI", author__isnull=True)
                    | models.Q(author_kind__in=["STUDENT", "ADMIN"], author__isnull=False)
                ),
                name="support_message_author_present",
            ),
        ]


class TicketEvent(models.Model):
    """Append-only transition and evidence log; no row is ever rewritten or deleted."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="events")
    sequence = models.PositiveIntegerField()
    from_state = models.CharField(max_length=16, blank=True)
    to_state = models.CharField(max_length=16)
    kind = models.CharField(max_length=24, choices=[(k, k) for k in EVENT_KINDS])
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="support_events"
    )
    reason = models.CharField(max_length=512, blank=True)
    observed_at = models.DateTimeField(default=django_timezone.now)
    recorded_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ticket", "sequence"], name="support_event_sequence"),
            models.CheckConstraint(
                condition=models.Q(kind__in=EVENT_KINDS), name="support_event_known_kind"
            ),
        ]


class SlaCycle(models.Model):
    """One measured first-human-response cycle. A finished cycle stays readable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name="sla_cycles")
    cycle_no = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True)
    target_minutes = models.PositiveIntegerField()
    due_at = models.DateTimeField()
    warning_at = models.DateTimeField(null=True)
    breached_at = models.DateTimeField(null=True)
    state = models.CharField(
        max_length=12, default="OPEN", choices=[("OPEN", "Open"), ("COMPLETED", "Completed")]
    )
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ticket", "cycle_no"], name="support_sla_cycle_once")
        ]


class TicketRating(models.Model):
    """Exactly one support-quality rating per ticket, editable inside its window."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(Ticket, on_delete=models.PROTECT, related_name="rating")
    value = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(default=django_timezone.now)
    editable_until = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gte=1, value__lte=5), name="support_rating_range"
            )
        ]


class SupportAiDay(models.Model):
    """Per-student daily AI support allowance counter (Asia/Hebron business day)."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    day = models.DateField()
    messages = models.PositiveIntegerField(default=0)
    uncertain_streak = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "day"], name="support_ai_day_once")]
