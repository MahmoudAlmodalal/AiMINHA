"""Phase13 owned tickets, measured first-response SLA, AI triage and assigned access."""

import io
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from credits.models import GlobalAiDay, GlobalDay, LedgerEntry
from credits.services import (
    business_day,
    create_synthetic_input,
    grant_signup,
    initialize_policy,
    read_wallet,
    reserve,
)
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import digest
from PIL import Image
from privacy.models import PrivacyAudit
from private_files import scanner
from private_files import services as file_services
from private_files.models import StorageLock
from rest_framework.test import APIClient
from support import services
from support.models import SupportCalendar, SupportCalendarHead, Ticket, TicketEvent

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-support-passphrase-529!"  # noqa: S105 -- public synthetic fixture.

AGENT_SCOPES = ["SUPPORT", "SUPPORT_QUEUE", "SUPPORT_ASSIGNMENT", "SUPPORT_POLICY"]
DEFAULT_TARGETS = {"CRITICAL": 240, "HIGH": 480, "NORMAL": 1440, "LOW": 2880}


def csrf(client):
    response = client.get("/api/v1/session/csrf")
    assert response.status_code == 200, response.content
    return response.json()["csrf_token"]


def request(client, method, path, data=None, *, revision=None, key=None):
    headers = {
        "HTTP_X_CSRFTOKEN": csrf(client),
        "HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4()),
    }
    if revision is not None:
        headers["HTTP_IF_MATCH"] = f'"{revision}"'
    return getattr(client, method)("/api/v1/" + path, data=data, format="json", **headers)


def sign_in(role="STUDENT", scopes=None, locale="en"):
    user = Account.objects.create_user(
        f"support-{uuid.uuid4()}@example.invalid",
        PASSWORD,
        birth_date=date(2000, 1, 1),
        locale=locale,
        state="ACTIVE",
        role=role,
        email_verified_at=timezone.now(),
        admin_scopes=scopes or [],
    )
    client = APIClient(enforce_csrf_checks=True)
    response = request(client, "post", "session/login", {"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.content
    if role == "ADMIN":
        # Synthetic server proof only: no endpoint accepts a client MFA claim.
        IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
            mfa_verified_at=timezone.now()
        )
    return client, user


def student(locale="en"):
    return sign_in("STUDENT", locale=locale)


def agent(scopes=None):
    return sign_in("ADMIN", scopes=scopes if scopes is not None else AGENT_SCOPES)


def create_ticket(client, *, request_human=False, message=None, subject=None, category="TECHNICAL"):
    response = request(
        client,
        "post",
        "tickets",
        {
            "category": category,
            "subject": subject or "Upload problem on the application portal",
            "message": message
            or "The upload failed again and the portal is not working for me right now.",
            "request_human": request_human,
        },
    )
    assert response.status_code == 201, response.content
    return response.json()


def refresh(client, ticket):
    response = client.get(f"/api/v1/tickets/{ticket['id']}")
    assert response.status_code == 200, response.content
    return response.json()


def assign(agent_client, agent_user, ticket, *, reason="Workload balance", revision=None):
    response = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/assignments",
        {"agent_id": str(agent_user.pk), "reason_code": reason},
        revision=ticket["row_version"] if revision is None else revision,
    )
    assert response.status_code == 200, response.content
    return response.json()


def agent_reply(
    agent_client,
    ticket,
    body="We checked the portal and the transcript upload needs a smaller file.",
):
    response = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/messages",
        {"body": body, "request_human": False},
    )
    assert response.status_code == 200, response.content
    return response.json()


def ai_reply(client, ticket):
    response = request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    assert response.status_code == 200, response.content
    return response.json()


def sla(client, ticket):
    response = client.get(f"/api/v1/tickets/{ticket['id']}/sla")
    assert response.status_code == 200, response.content
    return response.json()


@pytest.fixture(autouse=True)
def support_settings(settings):
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver"]
    initialize_policy()
    head = SupportCalendarHead.objects.select_related("policy").filter(pk=1).first()
    if head is None:
        policy = SupportCalendar.objects.create(
            version=1,
            timezone="Asia/Hebron",
            working_weekdays=[6, 0, 1, 2, 3],
            opens_local="09:00",
            closes_local="17:00",
            holidays=[],
            targets=DEFAULT_TARGETS,
            reason="Sourced default working calendar.",
        )
        SupportCalendarHead.objects.create(id=1, policy=policy)
    yield


@pytest.fixture
def private_settings(settings, tmp_path):
    StorageLock.objects.get_or_create(pk=1)
    settings.PRIVATE_FILES_ROOT = str(tmp_path / "private")
    settings.PRIVATE_FILES_STORAGE_APPROVED = True
    clean = scanner.CleanScan("ClamAV synthetic-test", "12345", timezone.now())
    with (
        patch("private_files.scanner.health", return_value=clean),
        patch("private_files.scanner.scan", return_value=clean),
    ):
        yield


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (3, 3), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


# --- ownership and lifecycle ------------------------------------------------


def test_a_ticket_starts_new_and_is_owner_scoped():
    client, user = student()
    ticket = create_ticket(client)
    assert ticket["state"] == "NEW"
    assert ticket["priority"] == "NORMAL"
    assert ticket["row_version"] >= 1
    other, _ = student()
    assert client.get(f"/api/v1/tickets/{ticket['id']}").status_code == 200
    assert other.get(f"/api/v1/tickets/{ticket['id']}").status_code == 404


def test_the_default_calendar_matches_the_sourced_working_week():
    policy = SupportCalendarHead.objects.select_related("policy").get(pk=1).policy
    assert policy.timezone == "Asia/Hebron"
    assert set(policy.working_weekdays) == {0, 1, 2, 3, 6}
    assert policy.opens_local == "09:00"
    assert policy.closes_local == "17:00"
    assert policy.targets == DEFAULT_TARGETS
    assert policy.ai_daily_messages == 5
    assert policy.closure_days == 7
    assert policy.reopen_days == 14
    assert policy.rating_edit_days == 7


def test_the_transition_log_is_append_only_and_records_the_actor():
    client, user = student()
    ticket = create_ticket(client, request_human=True)
    history = client.get(f"/api/v1/tickets/{ticket['id']}/history").json()["items"]
    kinds = [row["kind"] for row in history]
    assert "CREATED" in kinds
    assert "HUMAN_REQUESTED" in kinds
    sequences = [row["sequence"] for row in history]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)


def test_an_unknown_ticket_is_indistinguishable_from_a_missing_one():
    client, _ = student()
    other, _ = student()
    ticket = create_ticket(client)
    missing = other.get(f"/api/v1/tickets/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert other.get(f"/api/v1/tickets/{ticket['id']}").status_code == 404


# --- first-response SLA -----------------------------------------------------


def test_requesting_a_human_starts_the_measured_clock():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    assert ticket["state"] == "AWAITING_ADMIN"
    value = sla(client, ticket)
    assert value["human_requested_at"] is not None
    assert value["computed_due_at"] is not None
    assert value["target_business_minutes"] == 1440
    assert value["met"] is False


def test_an_ai_reply_never_satisfies_the_first_response_obligation():
    client, _ = student()
    ticket = create_ticket(client)
    result = ai_reply(client, ticket)
    assert result["ai"]["available"] is True
    assert result["ticket"]["state"] == "AI_HANDLING"
    value = sla(client, ticket)
    assert value["first_human_response_at"] is None
    assert value["met"] is False


def test_only_a_substantive_human_reply_satisfies_the_obligation():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    agent_reply(
        agent_client, ticket, "Thank you for contacting support, we will look into your issue"
    )
    value = sla(client, ticket)
    assert value["first_human_response_at"] is None
    assert value["met"] is False
    agent_reply(agent_client, ticket, "Please upload a PNG")
    value = sla(client, ticket)
    assert value["first_human_response_at"] is not None
    assert value["met"] is True


def test_waiting_for_the_student_afterwards_does_not_change_the_metric():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    agent_reply(agent_client, ticket)
    first = sla(client, ticket)["first_human_response_at"]
    assert (
        request(
            client,
            "post",
            f"tickets/{ticket['id']}/messages",
            {"body": "Thank you, I added the missing page.", "request_human": False},
        ).status_code
        == 200
    )
    assert sla(client, ticket)["first_human_response_at"] == first


def test_a_student_resolution_waits_for_the_quiet_period_before_closing():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    resolved = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    ).json()
    assert resolved["state"] == "RESOLVED"
    assert services.sweep()["closed"] == 0
    Ticket.objects.filter(pk=ticket["id"]).update(resolved_at=timezone.now() - timedelta(days=8))
    assert services.sweep()["closed"] == 1
    assert Ticket.objects.get(pk=ticket["id"]).state == "CLOSED"
    assert services.sweep()["closed"] == 0


def test_reopening_starts_a_new_measured_cycle():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    assert ticket["sla"]["cycle_no"] == 1
    response = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    )
    assert response.status_code == 200, response.content
    closed = response.json()
    # A resolution stays RESOLVED until the configured quiet period expires.
    assert closed["state"] == "RESOLVED"
    assert closed["sla"]["cycle_no"] == 1
    response = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=closed["row_version"],
    )
    assert response.status_code == 200, response.content
    reopened = response.json()
    assert reopened["state"] == "AWAITING_ADMIN"
    assert reopened["sla"]["cycle_no"] == 2
    assert reopened["sla"]["human_requested_at"] is not None


def test_reopening_outside_the_window_is_refused():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    closed = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    ).json()
    Ticket.objects.filter(pk=closed["id"]).update(
        resolved_at=timezone.now() - timedelta(days=30),
        closed_at=timezone.now() - timedelta(days=30),
        reopen_until=timezone.now() - timedelta(days=16),
    )
    response = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=closed["row_version"],
    )
    assert response.status_code == 409
    assert response.json()["code"] == "REOPEN_WINDOW_CLOSED"


def test_a_stale_revision_is_refused():
    client, _ = student()
    ticket = create_ticket(client)
    response = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "HUMAN_REQUESTED"},
        revision=ticket["row_version"] + 5,
    )
    assert response.status_code == 412


# --- administrator access ---------------------------------------------------


def test_an_unassigned_agent_cannot_read_the_thread():
    client, _ = student()
    agent_client, _ = agent()
    ticket = create_ticket(client)
    response = agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages")
    assert response.status_code == 403
    assert PrivacyAudit.objects.filter(
        action="support_ticket_read", outcome="DENY", reason="NOT_ASSIGNED"
    ).exists()


def test_the_queue_exposes_metadata_but_no_student_identity_or_subject():
    client, _ = student()
    agent_client, _ = agent()
    ticket = create_ticket(client, subject="My private transcript issue")
    queue = agent_client.get("/api/v1/admin/tickets").json()
    row = next(item for item in queue["items"] if item["id"] == ticket["id"])
    assert row["state"] == "NEW"
    assert "subject" not in row
    assert "student" not in row
    assert "owner" not in row


def test_an_assigned_agent_reads_the_thread_and_reassignment_revokes_it():
    client, _ = student()
    agent_client, agent_user = agent()
    other_agent_client, other_agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    row = assign(agent_client, agent_user, ticket)
    assert agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages").status_code == 200
    assert (
        other_agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages").status_code == 403
    )
    assert row["assigned_to_me"] is True
    assign(agent_client, other_agent_user, ticket, revision=row["row_version"])
    assert agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages").status_code == 403


def test_an_administrator_cannot_browse_the_private_file_library():
    client, _ = student()
    agent_client, _ = agent()
    response = agent_client.get("/api/v1/files")
    assert response.status_code == 403
    assert PrivacyAudit.objects.filter(action="identity_privacy_request", outcome="DENY").exists()


def test_the_administrator_sets_the_effective_priority_and_the_suggestion_is_kept():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client)
    result = ai_reply(client, ticket)
    suggested = result["ai"]["priority"]
    ticket = refresh(client, ticket)
    row = assign(agent_client, agent_user, ticket)
    response = request(
        agent_client,
        "put",
        f"admin/tickets/{ticket['id']}/classification",
        {"category": "DOCUMENTS", "priority": "HIGH", "reason_code": "MANUAL_REVIEW"},
        revision=row["row_version"],
    )
    assert response.status_code == 200, response.content
    updated = response.json()
    assert updated["priority"] == "HIGH"
    assert updated["category"] == "DOCUMENTS"
    assert updated["suggested_priority"] == suggested


# --- explicit ticket attachments --------------------------------------------


def test_an_explicitly_shared_attachment_is_readable_only_by_the_assigned_agent(private_settings):
    client, user = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    asset = file_services.store_bytes(user.pk, "cv.png", "image/png", png(), str(uuid.uuid4()))
    share = request(
        client,
        "post",
        f"tickets/{ticket['id']}/attachments",
        {"asset_id": str(asset.pk)},
    )
    assert share.status_code == 201, share.content
    assign(agent_client, agent_user, ticket)
    listing = agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    assert listing.status_code == 200, listing.content
    attachment = listing.json()["items"][0]
    assert attachment["display_name"] == "cv.png"
    assert attachment["state"] == "SHARED"
    metadata = agent_client.get(f"/api/v1/tickets/{ticket['id']}/attachments/{attachment['id']}")
    assert metadata.status_code == 200, metadata.content
    grant = request(
        agent_client,
        "post",
        f"tickets/{ticket['id']}/attachments/{attachment['id']}/access-grants",
        {},
    )
    assert grant.status_code == 201, grant.content
    content = agent_client.get(
        f"/api/v1/tickets/{ticket['id']}/attachments/{attachment['id']}/content",
        HTTP_X_FILE_ACCESS_GRANT=grant.json()["token"],
    )
    assert content.status_code == 200
    assert content.content == png()
    assert PrivacyAudit.objects.filter(action="ticket_file_bytes_read").exists()


def test_a_revoked_attachment_is_denied_to_the_assigned_agent(private_settings):
    client, user = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    asset = file_services.store_bytes(user.pk, "cv.png", "image/png", png(), str(uuid.uuid4()))
    share = request(
        client,
        "post",
        f"tickets/{ticket['id']}/attachments",
        {"asset_id": str(asset.pk)},
    )
    assert share.status_code == 201, share.content
    assign(agent_client, agent_user, ticket)
    listing = agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    attachment = listing.json()["items"][0]
    listed = client.get(f"/api/v1/tickets/{ticket['id']}/attachments").json()["items"]
    assert listed[0]["id"] == attachment["id"]
    assert listed[0]["display_name"] == "cv.png"
    assert listed[0]["state"] == "SHARED"
    assert listed[0]["version"] == attachment["version"]
    revoke = request(
        client,
        "delete",
        f"tickets/{ticket['id']}/attachments/{attachment['id']}",
        revision=f"share-{attachment['id']}-{attachment['version']}",
    )
    assert revoke.status_code == 202, revoke.content
    response = agent_client.get(f"/api/v1/tickets/{ticket['id']}/attachments/{attachment['id']}")
    assert response.status_code == 403
    after = client.get(f"/api/v1/tickets/{ticket['id']}/attachments").json()["items"]
    assert after[0]["state"] == "REVOKED"


def test_an_unassigned_agent_cannot_read_a_shared_attachment(private_settings):
    client, user = student()
    agent_client, agent_user = agent()
    other_agent_client, _ = agent()
    ticket = create_ticket(client, request_human=True)
    asset = file_services.store_bytes(user.pk, "cv.png", "image/png", png(), str(uuid.uuid4()))
    share = request(
        client,
        "post",
        f"tickets/{ticket['id']}/attachments",
        {"asset_id": str(asset.pk)},
    )
    assert share.status_code == 201, share.content
    assign(agent_client, agent_user, ticket)
    listing = agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    assert listing.status_code == 200
    attachment_id = listing.json()["items"][0]["id"]
    response = other_agent_client.get(f"/api/v1/tickets/{ticket['id']}/attachments/{attachment_id}")
    assert response.status_code == 403
    other_listing = other_agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    assert other_listing.status_code == 403


# --- AI triage ---------------------------------------------------------------


def test_a_financial_question_hands_off_to_a_human():
    client, _ = student()
    ticket = create_ticket(
        client,
        message="I lost my credits and my transfer receipt was never shown to me.",
        subject="My credit balance is wrong",
        category="PAYMENTS",
    )
    result = ai_reply(client, ticket)
    assert result["ai"]["available"] is True
    assert "FINANCIAL_TOPIC" in result["ai"]["reason"]
    assert result["ticket"]["state"] == "AWAITING_ADMIN"
    assert result["ticket"]["sla"]["human_requested_at"] is not None


def test_a_security_question_hands_off_to_a_human():
    client, _ = student()
    ticket = create_ticket(
        client,
        message="Someone signed in to my account without permission and my password changed.",
        subject="Someone else changed my password",
        category="ACCOUNT",
    )
    result = ai_reply(client, ticket)
    assert "SECURITY_TOPIC" in result["ai"]["reason"]
    assert result["ticket"]["state"] == "AWAITING_ADMIN"


def test_an_unclassifiable_question_hands_off_with_low_confidence():
    client, _ = student()
    ticket = create_ticket(client, message="???", subject="?", category="OTHER")
    result = ai_reply(client, ticket)
    assert "LOW_CONFIDENCE" in result["ai"]["reason"]
    assert result["ticket"]["state"] == "AWAITING_ADMIN"


def test_two_uncertain_answers_hand_off_as_repeated_failures():
    client, _ = student()
    first = ai_reply(client, create_ticket(client, message="???", subject="?", category="OTHER"))
    assert "LOW_CONFIDENCE" in first["ai"]["reason"]
    assert "REPEATED_FAILURE" not in first["ai"]["reason"]
    second = ai_reply(client, create_ticket(client, message="???", subject="?", category="OTHER"))
    assert "REPEATED_FAILURE" in second["ai"]["reason"]


def test_the_ai_never_changes_the_effective_priority():
    client, _ = student()
    ticket = create_ticket(client)
    result = ai_reply(client, ticket)
    assert result["ticket"]["priority"] == "NORMAL"
    assert result["ticket"]["suggested_priority"] != ""


def test_the_ai_never_moves_a_credit_balance():
    client, user = student()
    grant_signup(user.pk)
    proof = IdentitySession.objects.filter(account=user).first()
    before = read_wallet(user, proof)
    ticket = create_ticket(client)
    ai_reply(client, ticket)
    after = read_wallet(user, proof)
    assert after["posted_balance"] == before["posted_balance"]
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").count() == 0


def test_the_daily_allowance_falls_back_to_a_human_ticket():
    client, _ = student()
    last = None
    for index in range(6):
        ticket = create_ticket(
            client,
            message=f"The upload failed again and the portal is not working, case {index}.",
        )
        last = ai_reply(client, ticket)
    assert last["ai"]["available"] is False
    assert last["ai"]["reason"] == "DAILY_ALLOWANCE_EXHAUSTED"
    assert last["ticket"]["state"] == "AWAITING_ADMIN"


def consume_global_budget(total=100):
    """Fill the shared global AI budget with real reserved credit operations."""
    remaining = total
    while remaining > 0:
        user = Account.objects.create_user(
            f"budget-{uuid.uuid4()}@example.invalid",
            PASSWORD,
            birth_date=date(2000, 1, 1),
            locale="en",
            state="ACTIVE",
            email_verified_at=timezone.now(),
        )
        grant_signup(user.pk)
        fixture = create_synthetic_input(user.pk)
        for _ in range(min(6, remaining)):
            reserve(user.pk, "MATCHING_AI", str(uuid.uuid4()), fixture)
            remaining -= 1


def test_the_global_ai_budget_falls_back_to_a_human_ticket():
    client, _ = student()
    consume_global_budget()
    ticket = create_ticket(client)
    result = ai_reply(client, ticket)
    assert result["ai"]["available"] is False
    assert result["ai"]["reason"] == "GLOBAL_BUDGET_EXHAUSTED"


def test_the_ai_reply_consumes_the_shared_global_budget():
    client, _ = student()
    ticket = create_ticket(client)
    day = business_day(timezone.now())
    GlobalAiDay.objects.get_or_create(day=day)
    before = GlobalAiDay.objects.get(day=day).operations
    ai_reply(client, ticket)
    assert GlobalAiDay.objects.get(day=day).operations == before + 1
    # The financial ledger counter is never touched by support AI usage.
    assert GlobalDay.objects.filter(day=day).exists()


# --- resolution, rating and the worker sweep --------------------------------


def test_a_rating_is_recorded_once_and_stays_editable_inside_the_window():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    closed = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    ).json()
    response = request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 4},
        revision=closed["row_version"],
    )
    assert response.status_code == 200, response.content
    assert response.json()["value"] == 4
    updated = client.get(f"/api/v1/tickets/{ticket['id']}").json()
    response = request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 5},
        revision=updated["row_version"],
    )
    assert response.status_code == 200, response.content
    assert response.json()["value"] == 5


def test_a_rating_outside_the_window_is_refused():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    closed = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    ).json()
    Ticket.objects.filter(pk=closed["id"]).update(
        rating_window_until=timezone.now() - timedelta(days=1)
    )
    response = request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 3},
        revision=closed["row_version"],
    )
    assert response.status_code == 409
    assert response.json()["code"] == "RATING_WINDOW_CLOSED"


def test_the_worker_closes_a_resolved_ticket_after_the_quiet_period():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    row = assign(agent_client, agent_user, ticket)
    resolved = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "ANSWERED"},
        revision=row["row_version"],
    )
    assert resolved.status_code == 200, resolved.content
    Ticket.objects.filter(pk=ticket["id"]).update(resolved_at=timezone.now() - timedelta(days=8))
    result = services.sweep()
    assert result["closed"] == 1
    assert Ticket.objects.get(pk=ticket["id"]).state == "CLOSED"
    assert services.sweep()["closed"] == 0


def test_the_worker_records_an_sla_breach():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    Ticket.objects.filter(pk=ticket["id"]).update(
        human_requested_at=timezone.now() - timedelta(days=10),
        sla_due_at=timezone.now() - timedelta(days=1),
    )
    result = services.sweep()
    assert result["breaches"] == 1
    row = Ticket.objects.get(pk=ticket["id"])
    assert row.sla_breached_at is not None
    kinds = [event.kind for event in TicketEvent.objects.filter(ticket=row)]
    assert "SLA_BREACH" in kinds
    assert services.sweep()["breaches"] == 0


def test_aggregate_metrics_report_the_support_measurements():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    agent_reply(agent_client, ticket)
    metrics = agent_client.get("/api/v1/admin/support/metrics").json()["tickets"]
    assert metrics["total"] == 1
    assert metrics["first_human_responses"] == 1
    assert metrics["sla_breaches"] == 0


def test_the_support_policy_is_versioned_and_published_by_an_administrator():
    agent_client, _ = agent()
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    payload = {
        "timezone": "Asia/Hebron",
        "working_weekdays": [6, 0, 1, 2, 3],
        "opens_local": "08:00",
        "closes_local": "16:00",
        "holidays": ["2026-12-25"],
        "targets": DEFAULT_TARGETS,
        "ai_daily_messages": 3,
        "closure_days": 7,
        "reopen_days": 14,
        "rating_edit_days": 7,
        "warning_percent": 80,
        "effective_at": timezone.now().isoformat(),
        "reason_code": "Winter working hours.",
    }
    response = request(
        agent_client,
        "post",
        "admin/policies/sla",
        payload,
        revision=current["version"],
    )
    assert response.status_code == 201, response.content
    published = response.json()
    assert published["version"] == current["version"] + 1
    assert published["opens_local"] == "08:00"
    assert published["ai_daily_messages"] == 3


def test_a_policy_change_does_not_rewrite_an_in_flight_commitment():
    client, _ = student()
    agent_client, _ = agent()
    ticket = create_ticket(client, request_human=True)
    before = sla(client, ticket)
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    request(
        agent_client,
        "post",
        "admin/policies/sla",
        {
            "timezone": "Asia/Hebron",
            "working_weekdays": [6, 0, 1, 2, 3],
            "opens_local": "08:00",
            "closes_local": "16:00",
            "holidays": [],
            "targets": {**DEFAULT_TARGETS, "NORMAL": 60},
            "ai_daily_messages": 5,
            "closure_days": 7,
            "reopen_days": 14,
            "rating_edit_days": 7,
            "warning_percent": 80,
            "effective_at": timezone.now().isoformat(),
            "reason_code": "Shortened target for the experiment.",
        },
        revision=current["version"],
    )
    after = sla(client, ticket)
    assert after["computed_due_at"] == before["computed_due_at"]
    assert after["target_business_minutes"] == before["target_business_minutes"]
