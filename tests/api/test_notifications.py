"""Synthetic source evidence only; PostgreSQL ownership, scheduling and recovery."""

import uuid
from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from applications.models import Application, SavedScholarship
from applications.rounds import round_options
from catalog.models import ScholarshipVersion
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from identity.models import Account
from notifications import services
from notifications.models import (
    DeadlineEvent,
    DeadlineReminder,
    DeadlineVersion,
    Notification,
    NotificationAudit,
    WorkerCursor,
)
from rest_framework.test import APIClient
from test_catalog import (
    candidate_payload,
    create_source,
    csrf,
    moderate,
    post,
    publish,
    signed_client,
    source_payload,
)
from test_catalog import catalog_settings as catalog_settings

pytestmark = pytest.mark.django_db


def confirmed(instant=None, zone="UTC", label="Reviewed synthetic 2026 round"):
    instant = instant or timezone.now() + timedelta(days=1, minutes=5)
    return {
        "kind": "CONFIRMED",
        "label": label,
        # Z declares an absolute instant; the sponsor zone supplies its source display.
        # An offset such as +00:00 would instead assert a UTC donor-local wall clock.
        "closes_at": instant.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "timezone": zone,
        "source_text": "Authored exact synthetic closing instant; not a real scholarship.",
    }


def setup(rounds=None, required_documents=None):
    moderator, _ = signed_client()
    source = create_source(moderator)
    value = publish(
        moderator,
        source,
        rounds=rounds if rounds is not None else [confirmed()],
        required_documents=required_documents if required_documents is not None else [],
    )
    client, owner = signed_client(role="STUDENT", scopes=[])
    response = post(client, "saved-scholarships", {"scholarship_id": value["id"]})
    assert response.status_code == 200, response.content
    services.sync_scholarship(value["id"])
    return moderator, source, value, client, owner


@pytest.fixture
def deadline_setup():
    result = setup()
    assert services.schedule_owner(result[-1].pk) == 1
    return result


def due_moment(owner):
    return DeadlineReminder.objects.get(owner=owner).due_at + timedelta(seconds=1)


def deliver_due(owner):
    value = DeadlineReminder.objects.get(owner=owner)
    with patch(
        "notifications.services.timezone.now", return_value=value.due_at + timedelta(seconds=1)
    ):
        assert services.deliver(value.pk)
    return Notification.objects.get(owner=owner)


def revise(moderator, source, value, rounds, **overrides):
    response = post(
        moderator,
        f"admin/scholarships/{value['id']}/versions",
        candidate_payload(source, rounds=rounds, **{"required_documents": [], **overrides}),
        revision=value["revision"],
    )
    assert response.status_code == 200, response.content
    result = moderate(moderator, response.json())
    assert result.status_code == 200, result.content
    return result.json()


def create_application(client, value):
    version = ScholarshipVersion.objects.get(pk=value["published_version_id"])
    options = round_options(version.rounds)
    response = post(
        client,
        "applications",
        {"scholarship_id": value["id"], "round_key": options[0]["round_key"]},
    )
    assert response.status_code == 201, response.content
    return Application.objects.get(pk=response.json()["id"])


def test_schedule_offsets_are_absolute_elapsed_minutes_and_idempotent():
    closes = timezone.now() + timedelta(days=20)
    _, _, _, _, owner = setup([confirmed(closes, "Asia/Hebron")])
    assert services.schedule_owner(owner.pk) == 4
    assert services.schedule_owner(owner.pk) == 0
    assert set(DeadlineReminder.objects.values_list("offset_minutes", flat=True)) == set(
        services.OFFSETS
    )
    for item in DeadlineReminder.objects.select_related("event_version"):
        assert item.due_at == closes - timedelta(minutes=item.offset_minutes)
        assert item.event_version.closes_at == closes


@pytest.mark.parametrize(
    "round",
    [
        {"kind": "UNKNOWN"},
        {"kind": "ROLLING", "timezone": "Asia/Hebron"},
        {"kind": "DATE_ONLY", "deadline_date": "2027-01-01", "timezone": "Asia/Hebron"},
    ],
)
def test_unknown_rolling_date_only_never_schedule_or_return_countdown(round):
    _, _, value, client, owner = setup([round])
    assert services.schedule_owner(owner.pk) == 0
    app = create_application(client, value)
    data = services.deadline_for_application(app)
    assert data["eligible"] is False
    assert data["closes_at"] is None and data["display_at"] is None
    assert not DeadlineReminder.objects.exists()


def test_past_deadline_and_ambiguous_round_identity_never_count_down_or_schedule():
    _, _, value, client, owner = setup([confirmed(timezone.now() - timedelta(minutes=1))])
    app = create_application(client, value)
    assert services.deadline_for_application(app)["reason"] == "DEADLINE_PASSED"
    assert services.schedule_owner(owner.pk) == 0
    ambiguous = setup([confirmed(label="Same label"), {"kind": "UNKNOWN", "label": "same label"}])
    assert services.schedule_owner(ambiguous[-1].pk) == 0
    assert not DeadlineEvent.objects.filter(scholarship_id=ambiguous[2]["id"]).exists()


@pytest.mark.parametrize(
    "raw,zone",
    [
        ("2027-11-07T01:30:00", "America/New_York"),  # ambiguous fall-back wall clock
        ("2027-03-14T02:30:00", "America/New_York"),  # nonexistent spring-forward time
        ("2027-11-07T01:30:00+02:00", "America/New_York"),  # forged source offset
    ],
)
def test_catalog_rejects_ambiguous_gap_and_spoofed_zone_deadlines(raw, zone):
    moderator, _ = signed_client()
    source = create_source(moderator)
    response = post(
        moderator,
        "admin/scholarships",
        candidate_payload(source, rounds=[{**confirmed(zone=zone), "closes_at": raw}]),
    )
    assert response.status_code == 400
    assert not DeadlineEvent.objects.exists()


@pytest.mark.parametrize("offset", ["-04:00", "-05:00"])
def test_explicit_dst_fold_offset_keeps_exact_distinct_source_instant(offset):
    instant = datetime.fromisoformat(f"2027-11-07T01:30:00{offset}")
    row = {**confirmed(instant, "America/New_York"), "closes_at": instant.isoformat()}
    _, _, _, _, owner = setup([row])
    services.schedule_owner(owner.pk)
    evidence = DeadlineVersion.objects.get(state="CONFIRMED")
    assert evidence.closes_at == instant.astimezone(UTC)
    reminder = DeadlineReminder.objects.get(owner=owner, offset_minutes=1440)
    assert evidence.closes_at - reminder.due_at == timedelta(hours=24)


def test_new_confirmed_version_cancels_pending_old_but_preserves_delivered_and_read(deadline_setup):
    moderator, source, value, client, owner = deadline_setup
    notification = deliver_due(owner)
    response = post(client, f"notifications/{notification.pk}/read", {})
    assert response.status_code == 200, response.content
    saved_read = response.json()["read_at"]
    old_version = DeadlineVersion.objects.get()
    new = revise(moderator, source, value, [confirmed(timezone.now() + timedelta(days=22))])
    services.sync_scholarship(new["id"])
    assert DeadlineEvent.objects.get().current_id != old_version.pk
    assert DeadlineVersion.objects.get(pk=old_version.pk).state == "CONFIRMED"
    assert services.schedule_owner(owner.pk) == 4
    payload = client.get("/api/v1/notifications").json()["items"][0]
    assert payload["read_at"] == saved_read
    assert payload["deadline"]["current"] is False
    assert Notification.objects.count() == 1


def test_confirmed_to_unknown_cancels_pending_without_guessing_new_deadline(deadline_setup):
    moderator, source, value, _, owner = deadline_setup
    old = DeadlineVersion.objects.get()
    new = revise(moderator, source, value, [{"kind": "UNKNOWN", "label": confirmed()["label"]}])
    services.sync_scholarship(new["id"])
    assert DeadlineReminder.objects.get().status == "CANCELLED"
    assert DeadlineVersion.objects.get(pk=old.pk).closes_at == old.closes_at
    assert DeadlineEvent.objects.get().current.state == "UNKNOWN"
    assert services.schedule_owner(owner.pk) == 0


def test_delivery_rechecks_source_revocation_even_before_scheduler_sync(deadline_setup):
    moderator, source, _, _, owner = deadline_setup
    response = post(
        moderator,
        f"admin/sources/{source['id']}/versions",
        source_payload(permission_status="REVOKED"),
        revision=source["revision"],
    )
    assert response.status_code == 200, response.content
    with patch("notifications.services.timezone.now", return_value=due_moment(owner)):
        assert not services.deliver(DeadlineReminder.objects.get().pk)
    assert DeadlineReminder.objects.get().status == "CANCELLED"
    assert not Notification.objects.exists()


def test_delivery_rechecks_stale_source_and_unpublished_version(deadline_setup):
    moderator, _, value, _, owner = deadline_setup
    result = moderate(moderator, value, action="SUSPEND")
    assert result.status_code == 200, result.content
    with patch("notifications.services.timezone.now", return_value=due_moment(owner)):
        assert not services.deliver(DeadlineReminder.objects.get().pk)
    assert not Notification.objects.exists()


def test_freshness_expiry_removes_live_countdown_and_cancels(deadline_setup):
    _, _, value, client, owner = deadline_setup
    app = create_application(client, value)
    with patch(
        "notifications.services.timezone.now", return_value=timezone.now() + timedelta(days=31)
    ):
        assert services.deadline_for_application(app)["eligible"] is False
        services.sync_scholarship(value["id"])
    assert DeadlineEvent.objects.get().current.state == "CANCELLED"
    assert DeadlineReminder.objects.get().status == "CANCELLED"


@pytest.mark.parametrize("state", ["SUSPENDED", "DELETION_PENDING", "DELETED", "PENDING"])
def test_lifecycle_denial_cancels_delivery(deadline_setup, state):
    _, _, _, _, owner = deadline_setup
    Account.objects.filter(pk=owner.pk).update(state=state)
    with patch("notifications.services.timezone.now", return_value=due_moment(owner)):
        assert not services.deliver(DeadlineReminder.objects.get().pk)
    assert not Notification.objects.exists()
    assert DeadlineReminder.objects.get().status == "CANCELLED"


def test_lost_relationship_cancels_pending_and_new_owner_cannot_reuse(deadline_setup):
    _, _, _, _, owner = deadline_setup
    SavedScholarship.objects.filter(owner=owner).update(active=False, revision=2)
    with patch("notifications.services.timezone.now", return_value=due_moment(owner)):
        assert not services.deliver(DeadlineReminder.objects.get().pk)
    assert DeadlineReminder.objects.get().status == "CANCELLED"
    assert not Notification.objects.exists()


def test_delivery_is_atomic_recovers_failed_inbox_and_does_not_repeat(deadline_setup):
    _, _, _, _, owner = deadline_setup
    reminder = DeadlineReminder.objects.get()
    with patch("notifications.services.timezone.now", return_value=due_moment(owner)):
        with patch(
            "notifications.services.record", side_effect=RuntimeError("synthetic audit outage")
        ):
            with pytest.raises(RuntimeError):
                services.deliver(reminder.pk)
        assert not Notification.objects.exists()
        assert DeadlineReminder.objects.get().status == "SCHEDULED"
        assert services.deliver(reminder.pk)
        assert not services.deliver(reminder.pk)
    assert Notification.objects.count() == 1
    assert DeadlineReminder.objects.get().status == "DELIVERED"


def test_inbox_and_once_read_are_owned_csrf_protected_private_and_audited(deadline_setup):
    _, _, _, client, owner = deadline_setup
    item = deliver_due(owner)
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["unread_count"] == 1
    assert response.json()["items"][0]["target"]["kind"] == "SCHOLARSHIP"
    other, _ = signed_client(role="STUDENT", scopes=[])
    assert other.get("/api/v1/notifications").json()["items"] == []
    assert post(other, f"notifications/{item.pk}/read", {}).status_code == 404
    assert (
        client.post(f"/api/v1/notifications/{item.pk}/read", {}, format="json").status_code == 403
    )
    key = str(uuid.uuid4())
    first = post(client, f"notifications/{item.pk}/read", {}, key=key)
    second = post(client, f"notifications/{item.pk}/read", {}, key=key)
    third = post(client, f"notifications/{item.pk}/read", {})
    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json()["read_at"] == second.json()["read_at"] == third.json()["read_at"]
    assert client.get("/api/v1/notifications", {"unread_only": "true"}).json()["items"] == []
    assert NotificationAudit.objects.filter(
        actor_id=owner.pk, action="notification_inbox_read"
    ).exists()
    assert NotificationAudit.objects.filter(outcome="DENY").exists()


def test_admin_anonymous_and_unverified_cannot_read_private_inbox(deadline_setup):
    moderator, _, _, client, owner = deadline_setup
    assert APIClient().get("/api/v1/notifications").status_code == 401
    assert moderator.get("/api/v1/notifications").status_code == 403
    Account.objects.filter(pk=owner.pk).update(email_verified_at=None)
    assert client.get("/api/v1/notifications").status_code == 403


def put_preferences(client, body, revision=0, key=None):
    return client.put(
        "/api/v1/notification-preferences",
        body,
        format="json",
        HTTP_X_CSRFTOKEN=csrf(client),
        HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
        HTTP_IF_MATCH=f'"{revision}"',
    )


def test_timezone_preferences_compare_and_swap_idempotency_and_optional_only(deadline_setup):
    _, _, _, client, owner = deadline_setup
    first = client.get("/api/v1/notification-preferences")
    assert first.json()["timezone"] == "Asia/Hebron" and first.headers["ETag"] == '"0"'
    body = {
        "timezone": "Asia/Kathmandu",
        "deadline_enabled": False,
        "source_enabled": False,
        "document_enabled": False,
    }
    key = str(uuid.uuid4())
    result = put_preferences(client, body, key=key)
    assert result.status_code == 200, result.content
    assert result.headers["ETag"] == '"1"'
    assert put_preferences(client, body, key=key).json() == result.json()
    assert put_preferences(client, body).status_code == 412
    assert put_preferences(client, {**body, "timezone": "Invented/Zone"}, 1).status_code == 400
    assert DeadlineReminder.objects.get(owner=owner).status == "CANCELLED"
    assert services.category_enabled(result.json(), "ACCOUNT")
    assert services.category_enabled(result.json(), "SECURITY")
    assert not services.category_enabled(result.json(), "DEADLINE")


@pytest.mark.parametrize("switch", ["PREFERENCE", "SAVE"])
def test_opt_in_again_creates_new_attempt_preserves_cancel_and_delivers_only_once(
    deadline_setup, switch
):
    _, _, _, client, owner = deadline_setup
    initial = DeadlineReminder.objects.get()
    if switch == "PREFERENCE":
        body = {
            "timezone": "UTC",
            "deadline_enabled": False,
            "source_enabled": True,
            "document_enabled": True,
        }
        assert put_preferences(client, body).status_code == 200
        assert put_preferences(client, {**body, "deadline_enabled": True}, 1).status_code == 200
    else:
        saved = SavedScholarship.objects.get(owner=owner)
        saved.active, saved.revision = False, 2
        saved.save(update_fields=["active", "revision"])
        services.schedule_owner(owner.pk)
        saved.active, saved.revision = True, 3
        saved.save(update_fields=["active", "revision"])
    assert services.schedule_owner(owner.pk) == 1
    initial.refresh_from_db()
    assert initial.status == "CANCELLED"
    replacement = DeadlineReminder.objects.get(status="SCHEDULED")
    assert replacement.pk != initial.pk
    with patch(
        "notifications.services.timezone.now",
        return_value=replacement.due_at + timedelta(seconds=1),
    ):
        assert services.deliver(replacement.pk)
        assert not services.deliver(initial.pk)
        assert not services.deliver(replacement.pk)
    assert services.schedule_owner(owner.pk) == 0
    assert Notification.objects.filter(owner=owner).count() == 1
    assert DeadlineReminder.objects.filter(status="CANCELLED").count() == 1


def test_user_display_keeps_non_hour_zone_offset_and_24h_absolute(deadline_setup):
    _, _, value, client, owner = deadline_setup
    notification = deliver_due(owner)
    prefs = {
        "timezone": "Asia/Kathmandu",
        "deadline_enabled": True,
        "source_enabled": True,
        "document_enabled": True,
    }
    assert put_preferences(client, prefs).status_code == 200
    result = client.get("/api/v1/notifications").json()["items"][0]
    assert result["deadline"]["display_at"].endswith("+05:45")
    assert result["offset_minutes"] == 1440
    app = create_application(client, value)
    deadline = services.deadline_for_application(app)
    assert deadline["eligible"] and deadline["display_at"].endswith("+05:45")
    assert (
        datetime.fromisoformat(deadline["closes_at"])
        == notification.reminder.event_version.closes_at
    )


def test_source_change_and_known_missing_notices_dedupe_unknown_does_not_alert():
    moderator, source, value, client, owner = setup(required_documents=["Authored synthetic CV"])
    app = create_application(client, value)
    services.schedule_owner(owner.pk)
    services.schedule_owner(owner.pk)
    assert Notification.objects.filter(category="DOCUMENT_MISSING", application=app).count() == 1
    new = revise(moderator, source, value, [confirmed(timezone.now() + timedelta(days=3))])
    services.sync_scholarship(new["id"])
    services.schedule_owner(owner.pk)
    services.schedule_owner(owner.pk)
    assert Notification.objects.filter(category="SOURCE_CHANGE", application=app).count() == 1
    assert Notification.objects.filter(category="DOCUMENT_MISSING").count() == 1
    unknown = setup(required_documents=[])
    other_app = create_application(unknown[3], unknown[2])
    services.schedule_owner(unknown[-1].pk)
    assert not Notification.objects.filter(
        category="DOCUMENT_MISSING", application=other_app
    ).exists()


def test_rebase_does_not_emit_new_missing_alerts_for_historical_requirements():
    moderator, source, value, client, owner = setup(required_documents=["Historical synthetic CV"])
    app = create_application(client, value)
    # Rebase before running notifications: historical missing requirement is never current.
    new = revise(
        moderator,
        source,
        value,
        [confirmed(timezone.now() + timedelta(days=3))],
        required_documents=["Current synthetic transcript"],
    )
    response = post(
        client, f"applications/{app.pk}/rebase", {"confirm": True}, revision=app.revision
    )
    assert response.status_code == 200, response.content
    app.refresh_from_db()
    services.sync_scholarship(new["id"])
    services.schedule_owner(owner.pk)
    assert app.requirements.count() == 2
    notice = Notification.objects.get(category="DOCUMENT_MISSING", application=app)
    assert str(notice.event_id) == str(
        app.requirements.get(scholarship_version_id=app.scholarship_version_id).pk
    )


def test_deadline_evidence_and_read_history_cannot_be_mutated_in_database(deadline_setup):
    _, _, _, client, owner = deadline_setup
    notification = deliver_due(owner)
    assert post(client, f"notifications/{notification.pk}/read", {}).status_code == 200
    for mutation in (
        lambda: DeadlineVersion.objects.update(state="UNKNOWN", closes_at=None),
        lambda: Notification.objects.filter(pk=notification.pk).update(read_at=None),
        lambda: Notification.objects.filter(pk=notification.pk).update(event_version=999),
        lambda: NotificationAudit.objects.update(action="forged"),
    ):
        with pytest.raises(DatabaseError), transaction.atomic():
            mutation()


def test_database_rejects_reminder_wrong_due_and_cross_owner_inbox(deadline_setup):
    _, _, _, _, owner = deadline_setup
    reminder = DeadlineReminder.objects.get(owner=owner)
    with pytest.raises(DatabaseError), transaction.atomic():
        DeadlineReminder.objects.create(
            owner=owner,
            event=reminder.event,
            event_version=reminder.event_version,
            offset_minutes=4320,
            due_at=reminder.due_at,
        )
    _, other = signed_client(role="STUDENT", scopes=[])
    with pytest.raises(DatabaseError), transaction.atomic():
        Notification.objects.create(
            owner=other,
            event_id=reminder.pk,
            event_version=reminder.event_version.version,
            category="DEADLINE",
            reminder=reminder,
            scholarship_id=reminder.event.scholarship_id,
        )


def test_partial_delivery_fails_deferred_database_atomicity_guard(deadline_setup):
    reminder = DeadlineReminder.objects.get()
    with pytest.raises(DatabaseError), transaction.atomic():
        reminder.status = "DELIVERED"
        reminder.delivered_at = timezone.now()
        reminder.save(update_fields=["status", "delivered_at"])
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_worker_is_bounded_cursor_recovers_and_never_accepts_student_clock(deadline_setup):
    _, _, _, client, _ = deadline_setup
    stream = StringIO()
    call_command("process_deadline_reminders", batch_size=1, max_batches=1, stdout=stream)
    assert '"scholarships": 1' in stream.getvalue()
    assert WorkerCursor.objects.count() == 2
    with pytest.raises(ValueError):
        services.process(501, 1)
    assert client.post("/api/v1/notifications/process", {"now": "2099-01-01"}).status_code == 404
    cursor = WorkerCursor.objects.get(name="scholarships")
    old = cursor.last_id
    with patch(
        "notifications.services.sync_scholarship", side_effect=RuntimeError("synthetic crash")
    ):
        # Reset to prove a failed unit leaves cursor at its prior stable position.
        WorkerCursor.objects.filter(pk=cursor.pk).update(last_id=None)
        with pytest.raises(RuntimeError):
            services.process(1, 1)
    assert WorkerCursor.objects.get(pk=cursor.pk).last_id is None
    assert old is not None
