"""R18/OQ-017: UTC evidence, recoverable scheduling and one private inbox effect."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from applications.models import Application, ApplicationRequirement, SavedScholarship
from applications.rounds import round_options
from catalog import services as catalog
from catalog.deadlines import parse_round
from catalog.models import Scholarship, ScholarshipVersion, Source
from django.db import transaction
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, require_student
from rest_framework.exceptions import ValidationError

from notifications.models import (
    DeadlineEvent,
    DeadlineReminder,
    DeadlineVersion,
    Notification,
    NotificationAudit,
    NotificationPreference,
    WorkerCursor,
)

OFFSETS = (20160, 10080, 4320, 1440)
TERMINAL = ("ACCEPTED", "REJECTED", "WITHDRAWN")
DEFAULT_ZONE = "Asia/Hebron"  # Display default only; never supplies a sponsor source zone.


def record(
    actor: Any,
    action: str,
    resource: Any = None,
    *,
    outcome: str = "ALLOW",
    reason: str = "",
    correlation: Any = None,
) -> None:
    NotificationAudit.objects.create(
        actor_id=getattr(actor, "pk", None),
        resource_id=resource,
        action=action,
        outcome=outcome,
        reason=reason,
        correlation_id=correlation,
    )


def student(user: Account, proof: IdentitySession) -> Account:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_student(user)
    proof.refresh_from_db()
    now = timezone.now()
    if (
        proof.account_id != user.pk
        or proof.epoch != user.session_epoch
        or proof.revoked_at is not None
        or now >= proof.expires_at
        or now >= proof.last_seen_at + timedelta(hours=24)
    ):
        raise IdentityError("SESSION_EXPIRED", 401, "Sign in again")
    return user


def preferences(owner_id: Any) -> dict[str, Any]:
    value = NotificationPreference.objects.filter(owner_id=owner_id).first()
    return {
        "revision": value.revision if value else 0,
        "timezone": value.timezone if value else DEFAULT_ZONE,
        "deadline_enabled": value.deadline_enabled if value else True,
        "source_enabled": value.source_enabled if value else True,
        "document_enabled": value.document_enabled if value else True,
    }


def category_enabled(prefs: dict[str, Any], category: str) -> bool:
    # Account/security producers are outside Phase12. Optional switches cannot deny them.
    field = {
        "DEADLINE": "deadline_enabled",
        "SOURCE_CHANGE": "source_enabled",
        "DOCUMENT_MISSING": "document_enabled",
    }.get(category)
    return bool(prefs[field]) if field else True


@transaction.atomic
def read_preferences(user: Account, proof: IdentitySession, correlation: Any) -> dict[str, Any]:
    user = student(user, proof)
    value = preferences(user.pk)
    record(user, "notification_preferences_read", correlation=correlation)
    return value


@transaction.atomic
def write_preferences(
    user: Account, proof: IdentitySession, data: dict[str, Any], expected: int, correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    value, _ = NotificationPreference.objects.get_or_create(owner=user)
    if value.revision != expected:
        raise IdentityError("STALE_REVISION", 412, "Preferences changed; reload before editing")
    for key, item in data.items():
        setattr(value, key, item)
    value.revision += 1
    value.save()
    if not value.deadline_enabled:
        for reminder in DeadlineReminder.objects.select_for_update().filter(
            owner=user, status="SCHEDULED"
        ):
            cancel(reminder, "PREFERENCE_DISABLED")
    record(user, "notification_preferences_updated", correlation=correlation)
    return preferences(user.pk)


def current_published(scholarship_id: Any) -> ScholarshipVersion | None:
    version = catalog.published_query().filter(scholarship_id=scholarship_id).first()
    if version is None or catalog.public_data(version)["freshness"] != "CURRENT":
        return None
    return version


def deadline_for_application(
    application: Application, display_timezone: str | None = None
) -> dict[str, Any]:
    zone = display_timezone or preferences(application.owner_id)["timezone"]
    result: dict[str, Any] = {
        "kind": "UNKNOWN",
        "closes_at": None,
        "source_timezone": None,
        "display_at": None,
        "display_timezone": zone,
        "eligible": False,
        "reason": "SOURCE_UNAVAILABLE_OR_STALE",
        "source_version_id": None,
    }
    version = current_published(application.scholarship_id)
    if version is None:
        return result
    result["source_version_id"] = str(version.pk)
    try:
        rows = round_options(version.rounds)
        row = next((value for value in rows if value["round_key"] == application.round_key), None)
        if row is None:
            result["reason"] = "ROUND_UNAVAILABLE"
            return result
        row = parse_round(row)
    except (IdentityError, ValidationError, ValueError, KeyError):
        result["reason"] = "ROUND_IDENTITY_OR_DATE_UNAVAILABLE"
        return result
    result.update(kind=row["kind"], source_timezone=row.get("timezone"))
    if row["kind"] != "CONFIRMED":
        result["reason"] = "DEADLINE_NOT_CONFIRMED"
        return result
    instant = datetime.fromisoformat(row["closes_at"])
    if instant <= timezone.now():
        result["reason"] = "DEADLINE_PASSED"
        return result
    result.update(
        eligible=True,
        reason="CONFIRMED_CURRENT_SOURCE",
        closes_at=instant.isoformat().replace("+00:00", "Z"),
        display_at=instant.astimezone(ZoneInfo(zone)).isoformat(),
    )
    return result


def locked_catalog(scholarship_id: Any) -> Scholarship:
    """Caller locks owner first if needed; catalog order is source, scholarship, event."""
    snapshot = Scholarship.objects.select_related("latest__source_revision").get(pk=scholarship_id)
    if snapshot.latest_id:
        Source.objects.select_for_update().get(pk=snapshot.latest.source_revision.source_id)
    scholarship = Scholarship.objects.select_for_update().get(pk=scholarship_id)
    if scholarship.latest_id != snapshot.latest_id:
        raise IdentityError("CATALOG_CHANGED", 409, "Retry against the current catalog")
    return scholarship


def cancel(reminder: DeadlineReminder, reason: str) -> None:
    if reminder.status != "SCHEDULED":
        return
    reminder.status = "CANCELLED"
    reminder.cancelled_at = timezone.now()
    reminder.cancel_reason = reason
    reminder.save(update_fields=["status", "cancelled_at", "cancel_reason"])


def append_deadline(
    event: DeadlineEvent,
    version: ScholarshipVersion,
    state: str,
    row: dict[str, Any],
    reason: str,
) -> None:
    instant = datetime.fromisoformat(row["closes_at"]) if state == "CONFIRMED" else None
    payload = {
        "scholarship_version_id": str(version.pk),
        "state": state,
        "source_round": row,
        "reason": reason,
    }
    content_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if event.current_id and event.current.content_hash == content_hash:
        return
    revision = DeadlineVersion.objects.create(
        event=event,
        version=event.revision + 1,
        scholarship_version=version,
        state=state,
        closes_at=instant,
        source_timezone=row.get("timezone") or "",
        source_round=row,
        reason=reason,
        content_hash=content_hash,
    )
    event.current, event.revision = revision, revision.version
    event.save(update_fields=["current", "revision"])
    for reminder in (
        DeadlineReminder.objects.select_for_update()
        .filter(event=event, status="SCHEDULED")
        .exclude(event_version=revision)
    ):
        cancel(reminder, "SUPERSEDED_EVENT")


@transaction.atomic
def sync_scholarship(scholarship_id: Any) -> None:
    scholarship = locked_catalog(scholarship_id)
    version = current_published(scholarship_id)
    rows: list[dict[str, Any]] = []
    reason = "SOURCE_UNAVAILABLE_OR_STALE"
    if version:
        try:
            rows = [parse_round(row) for row in round_options(version.rounds)]
        except (IdentityError, ValidationError, ValueError, KeyError):
            reason = "ROUND_IDENTITY_OR_DATE_UNAVAILABLE"
        else:
            reason = "ROUND_REMOVED"
    keys = set()
    for value in rows:
        assert version is not None
        row = dict(value)
        key = row.pop("round_key")
        keys.add(key)
        event, _ = DeadlineEvent.objects.get_or_create(scholarship=scholarship, round_key=key)
        event = (
            DeadlineEvent.objects.select_for_update(of=("self",))
            .select_related("current")
            .get(pk=event.pk)
        )
        append_deadline(
            event,
            version,
            "CONFIRMED" if row["kind"] == "CONFIRMED" else "UNKNOWN",
            row,
            "CONFIRMED_CURRENT_SOURCE" if row["kind"] == "CONFIRMED" else "DEADLINE_NOT_CONFIRMED",
        )
    for event in (
        DeadlineEvent.objects.select_for_update(of=("self",))
        .select_related("current__scholarship_version")
        .filter(scholarship=scholarship)
        .exclude(round_key__in=keys)
    ):
        if event.current:
            append_deadline(
                event, version or event.current.scholarship_version, "CANCELLED", {}, reason
            )


def relationship(owner_id: Any, event: DeadlineEvent) -> tuple[str, Any] | None:
    application = (
        Application.objects.filter(
            owner_id=owner_id, scholarship_id=event.scholarship_id, round_key=event.round_key
        )
        .exclude(state__in=TERMINAL)
        .first()
    )
    if application:
        return "APPLICATION", application.pk
    if SavedScholarship.objects.filter(
        owner_id=owner_id, scholarship_id=event.scholarship_id, active=True
    ).exists():
        return "SCHOLARSHIP", event.scholarship_id
    return None


def current_event(event: DeadlineEvent) -> bool:
    value = event.current
    if value is None or value.state != "CONFIRMED":
        return False
    version = current_published(event.scholarship_id)
    if version is None or version.pk != value.scholarship_version_id:
        return False
    try:
        rows = round_options(version.rounds)
    except IdentityError:
        return False
    return any(
        row["round_key"] == event.round_key
        and {key: item for key, item in row.items() if key != "round_key"} == value.source_round
        for row in rows
    )


def application_notices(user: Account, version: ScholarshipVersion) -> None:
    from applications.services import artifact_is_available

    prefs = preferences(user.pk)
    for application in Application.objects.filter(
        owner=user, scholarship_id=version.scholarship_id
    ).exclude(state__in=TERMINAL):
        if application.scholarship_version_id != version.pk and category_enabled(
            prefs, "SOURCE_CHANGE"
        ):
            Notification.objects.get_or_create(
                owner=user,
                event_id=application.pk,
                event_version=version.version,
                category="SOURCE_CHANGE",
                defaults={"application": application},
            )
        if (
            application.scholarship_version_id == version.pk
            and application.requirements_known
            and application.state in {"PREPARING", "READY"}
            and category_enabled(prefs, "DOCUMENT_MISSING")
        ):
            # Only explicit, exact-version known requirements can assert a missing file.
            for requirement in ApplicationRequirement.objects.filter(
                application=application,
                scholarship_version_id=application.scholarship_version_id,
            ).select_related("selectedartifact"):
                selected = getattr(requirement, "selectedartifact", None)
                if selected and artifact_is_available(
                    user.pk, selected.version_id, selected.asset_id, selected.content_hash
                ):
                    continue
                Notification.objects.get_or_create(
                    owner=user,
                    event_id=requirement.pk,
                    event_version=1,
                    category="DOCUMENT_MISSING",
                    defaults={"application": application},
                )


@transaction.atomic
def schedule_owner(owner_id: Any) -> int:
    user = Account.objects.select_for_update().get(pk=owner_id)
    try:
        require_student(user)
        eligible = True
        allowed = category_enabled(preferences(owner_id), "DEADLINE")
    except IdentityError:
        eligible, allowed = False, False
    count = 0
    # Current saved scholarships cover all reviewed rounds; applications select one round.
    ids = set(
        SavedScholarship.objects.filter(owner=user, active=True).values_list(
            "scholarship_id", flat=True
        )
    ) | set(
        Application.objects.filter(owner=user)
        .exclude(state__in=TERMINAL)
        .values_list("scholarship_id", flat=True)
    )
    for scholarship_id in sorted(ids):
        locked_catalog(scholarship_id)
        version = current_published(scholarship_id)
        if eligible and version:
            application_notices(user, version)
        for event in (
            DeadlineEvent.objects.select_for_update(of=("self",))
            .select_related("current")
            .filter(scholarship_id=scholarship_id)
            .order_by("id")
        ):
            if not allowed or not relationship(user.pk, event) or not current_event(event):
                continue
            for offset in OFFSETS:
                due = event.current.closes_at - timedelta(minutes=offset)
                # R18 proposed policy: no missed reminders backfilled on first relationship.
                if due <= timezone.now():
                    continue
                _, created = DeadlineReminder.objects.exclude(status="CANCELLED").get_or_create(
                    owner=user,
                    event=event,
                    event_version=event.current,
                    offset_minutes=offset,
                    defaults={"due_at": due},
                )
                count += int(created)
    # A removed relationship, lifecycle change or preference does not erase read history.
    for reminder in (
        DeadlineReminder.objects.select_for_update(of=("self",))
        .select_related("event__current")
        .filter(owner=user, status="SCHEDULED")
    ):
        if (
            not allowed
            or reminder.event.current_id != reminder.event_version_id
            or not relationship(user.pk, reminder.event)
            or not current_event(reminder.event)
        ):
            cancel(reminder, "RECIPIENT_OR_EVENT_UNAVAILABLE")
    return count


@transaction.atomic
def deliver(reminder_id: Any) -> bool:
    snapshot = DeadlineReminder.objects.select_related("event").get(pk=reminder_id)
    user = Account.objects.select_for_update().get(pk=snapshot.owner_id)
    locked_catalog(snapshot.event.scholarship_id)
    event = (
        DeadlineEvent.objects.select_for_update(of=("self",))
        .select_related("current")
        .get(pk=snapshot.event_id)
    )
    reminder = DeadlineReminder.objects.select_for_update().get(pk=reminder_id)
    if reminder.status != "SCHEDULED" or reminder.due_at > timezone.now():
        return False
    try:
        require_student(user)
        allowed = category_enabled(preferences(user.pk), "DEADLINE")
    except IdentityError:
        allowed = False
    target = relationship(user.pk, event)
    if (
        not allowed
        or not target
        or event.current_id != reminder.event_version_id
        or not current_event(event)
        or event.current.closes_at <= timezone.now()
    ):
        cancel(reminder, "DELIVERY_GUARD_FAILED")
        return False
    target_field = "application_id" if target[0] == "APPLICATION" else "scholarship_id"
    now = timezone.now()
    Notification.objects.create(
        owner=user,
        # Each threshold is its own durable event; retry reuses this exact scheduler id.
        event_id=reminder.pk,
        event_version=event.current.version,
        category="DEADLINE",
        reminder=reminder,
        created_at=now,
        **{target_field: target[1]},
    )
    reminder.status, reminder.delivered_at = "DELIVERED", now
    reminder.save(update_fields=["status", "delivered_at"])
    record(user, "deadline_delivered", reminder.pk)
    return True


def notification_data(value: Notification, zone: str) -> dict[str, Any]:
    application = value.application_id is not None
    available = (
        Application.objects.filter(pk=value.application_id, owner_id=value.owner_id).exists()
        if application
        else catalog.published_query().filter(scholarship_id=value.scholarship_id).exists()
    )
    deadline = None
    if value.reminder_id:
        evidence = value.reminder.event_version
        deadline = {
            "closes_at": evidence.closes_at,
            "source_timezone": evidence.source_timezone,
            "display_at": evidence.closes_at.astimezone(ZoneInfo(zone)).isoformat(),
            "display_timezone": zone,
            "current": value.reminder.event.current_id == evidence.pk
            and current_event(value.reminder.event),
        }
    return {
        "id": str(value.pk),
        "category": value.category,
        "event_id": str(value.event_id),
        "event_version": value.event_version,
        "offset_minutes": value.reminder.offset_minutes if value.reminder_id else None,
        "created_at": value.created_at,
        "read_at": value.read_at,
        "target": {
            "kind": "APPLICATION" if application else "SCHOLARSHIP",
            "id": str(value.application_id if application else value.scholarship_id),
            "available": available,
        },
        "deadline": deadline,
    }


def inbox_query(owner_id: Any) -> Any:
    return Notification.objects.filter(owner_id=owner_id).select_related(
        "reminder__event__current", "reminder__event_version"
    )


@transaction.atomic
def inbox(
    user: Account, proof: IdentitySession, data: dict[str, Any], correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    query = inbox_query(user.pk)
    unread = query.filter(read_at__isnull=True).count()
    if data["unread_only"]:
        query = query.filter(read_at__isnull=True)
    start = (data["page"] - 1) * data["page_size"]
    zone = preferences(user.pk)["timezone"]
    result = {
        "items": [
            notification_data(value, zone)
            for value in query.order_by("-created_at", "id")[start : start + data["page_size"]]
        ],
        "total": query.count(),
        "unread_count": unread,
        "page": data["page"],
        "page_size": data["page_size"],
    }
    record(user, "notification_inbox_read", correlation=correlation)
    return result


@transaction.atomic
def mark_read(
    user: Account, proof: IdentitySession, notification_id: UUID, correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    value = inbox_query(user.pk).select_for_update(of=("self",)).filter(pk=notification_id).first()
    if value is None:
        raise IdentityError("NOT_FOUND", 404, "Notification not found")
    if value.read_at is None:
        value.read_at = timezone.now()
        value.save(update_fields=["read_at"])
    record(user, "notification_marked_read", value.pk, correlation=correlation)
    return notification_data(value, preferences(user.pk)["timezone"])


def sweep(name: str, model: Any, size: int, handler: Any) -> int:
    cursor, _ = WorkerCursor.objects.get_or_create(name=name)
    query = model.objects.order_by("id")
    if cursor.last_id:
        query = query.filter(id__gt=cursor.last_id)
    ids = list(query.values_list("id", flat=True)[:size])
    for value in ids:
        handler(value)
    # Per-row handlers commit independently, so never retain source/owner locks across
    # rows. Concurrent sweeps may repeat work safely; only the unchanged cursor moves.
    WorkerCursor.objects.filter(name=name, last_id=cursor.last_id).update(
        last_id=ids[-1] if len(ids) == size else None
    )
    return len(ids)


def process(batch_size: int = 100, max_batches: int = 10) -> dict[str, int]:
    if not 1 <= batch_size <= 500 or not 1 <= max_batches <= 20:
        raise ValueError("Batch size must be 1..500 and max batches 1..20")
    counts = {"scholarships": 0, "owners": 0, "delivered": 0}
    for name, model, handler, key in (
        ("scholarships", Scholarship, sync_scholarship, "scholarships"),
        ("owners", Account, schedule_owner, "owners"),
    ):
        for _ in range(max_batches):
            count = sweep(name, model, batch_size, handler)
            counts[key] += count
            if count < batch_size:
                break
    # A failed delivery rolls back both effects. Retry preserves the same reminder identity.
    due = list(
        DeadlineReminder.objects.filter(status="SCHEDULED", due_at__lte=timezone.now())
        .order_by("due_at", "id")
        .values_list("id", flat=True)[: batch_size * max_batches]
    )
    for reminder_id in due:
        counts["delivered"] += int(deliver(reminder_id))
    return counts
