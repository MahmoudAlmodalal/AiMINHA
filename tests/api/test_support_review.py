"""Phase13 regression cases for the reviewed support, SLA and AI-triage defects."""

import io
import uuid
from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from credits.models import GlobalAiDay, GlobalDay, LedgerEntry
from credits.services import business_day, grant_signup, initialize_policy, reserve
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import digest
from PIL import Image
from privacy.models import PrivacyAudit
from private_files import scanner
from private_files import services as file_services
from private_files.models import StorageLock
from rest_framework.test import APIClient
from support import calendar as workcal
from support import services
from support.models import SupportCalendar, SupportCalendarHead, Ticket

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-support-review-passphrase-529!"  # noqa: S105 -- public synthetic fixture.
AGENT_SCOPES = ["SUPPORT", "SUPPORT_QUEUE", "SUPPORT_ASSIGNMENT", "SUPPORT_POLICY"]
DEFAULT_TARGETS = {"CRITICAL": 240, "HIGH": 480, "NORMAL": 1440, "LOW": 2880}
HEBRON = ZoneInfo("Asia/Hebron")


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


def sign_in(role="STUDENT", scopes=None, locale="en", mfa=True):
    user = Account.objects.create_user(
        f"review-{uuid.uuid4()}@example.invalid",
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
    if role == "ADMIN" and mfa:
        IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
            mfa_verified_at=timezone.now()
        )
    return client, user


def student():
    return sign_in("STUDENT")


def agent(scopes=None, mfa=True):
    return sign_in("ADMIN", scopes if scopes is not None else AGENT_SCOPES, mfa=mfa)


def create_ticket(
    client, *, request_human=False, message=None, subject=None, urgency=None, category="TECHNICAL"
):
    payload = {
        "category": category,
        "subject": subject or "Upload problem on the application portal",
        "message": message or "The upload failed again and the portal is not working for me.",
        "request_human": request_human,
    }
    if urgency is not None:
        payload["urgency"] = urgency
    response = request(client, "post", "tickets", payload)
    assert response.status_code == 201, response.content
    return response.json()


def assign(agent_client, agent_user, ticket, *, revision=None, agent_id=None):
    response = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/assignments",
        {"agent_id": str(agent_id or agent_user.pk), "reason_code": "Review workload"},
        revision=ticket["row_version"] if revision is None else revision,
    )
    assert response.status_code == 200, response.content
    return response.json()


def agent_reply(agent_client, ticket, body="Please upload a PNG copy of the transcript."):
    response = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/messages",
        {"body": body, "request_human": False},
    )
    assert response.status_code == 200, response.content
    return response.json()


def sla(client, ticket):
    response = client.get(f"/api/v1/tickets/{ticket['id']}/sla")
    assert response.status_code == 200, response.content
    return response.json()


@pytest.fixture(autouse=True)
def review_settings(settings):
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver"]
    initialize_policy()
    head = SupportCalendarHead.objects.select_related("policy").filter(pk=1).first()
    if head is None:
        policy = SupportCalendar.objects.create(
            version=1,
            timezone="Asia/Hebron",
            working_weekdays=[0, 1, 2, 3, 6],
            opens_local="09:00",
            closes_local="17:00",
            holidays=[],
            targets=DEFAULT_TARGETS,
            reason="Sourced default support calendar.",
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


# --- 01: assigned-ticket actions need the scope and a live MFA proof ---------


def assigned_ticket_actions(client, ticket):
    """Every administrator-facing action on an assigned ticket."""
    return [
        ("thread", client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages")),
        (
            "reply",
            request(
                client,
                "post",
                f"admin/tickets/{ticket['id']}/messages",
                {"body": "Please upload a PNG copy.", "request_human": False},
            ),
        ),
        (
            "transition",
            request(
                client,
                "post",
                f"admin/tickets/{ticket['id']}/transitions",
                {"to_state": "AWAITING_STUDENT", "reason_code": "Waiting on student"},
                revision=ticket["row_version"],
            ),
        ),
        (
            "classification",
            request(
                client,
                "put",
                f"admin/tickets/{ticket['id']}/classification",
                {"category": "TECHNICAL", "priority": "HIGH", "reason_code": "Classified"},
                revision=ticket["row_version"],
            ),
        ),
        ("sla", client.get(f"/api/v1/admin/tickets/{ticket['id']}/sla")),
    ]


def test_an_assigned_agent_without_the_support_scope_is_refused():
    client, _ = student()
    assigner_client, assigner = agent()
    target_client, target = agent()
    ticket = create_ticket(client, request_human=True)
    assign(assigner_client, assigner, ticket, agent_id=target.pk)
    Account.objects.filter(pk=target.pk).update(admin_scopes=["SUPPORT_QUEUE"])

    # Missing SUPPORT scope refuses every assigned action with ADMIN_MFA_REQUIRED
    for action_name, response in assigned_ticket_actions(target_client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )

    # An agent who never held the support scope at all is also refused
    never_client, never_agent = agent(scopes=["SUPPORT_QUEUE"])
    Ticket.objects.filter(pk=ticket["id"]).update(assigned_admin=never_agent)
    for action_name, response in assigned_ticket_actions(never_client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )

    # Missing SUPPORT_QUEUE scope refuses queue access with ADMIN_MFA_REQUIRED
    no_queue_client, _ = agent(scopes=["SUPPORT"])
    queue_resp = no_queue_client.get("/api/v1/admin/tickets")
    assert queue_resp.status_code == 403
    assert queue_resp.json()["code"] == "ADMIN_MFA_REQUIRED"


def test_an_assigned_agent_without_a_live_mfa_proof_is_refused():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    IdentitySession.objects.filter(account=agent_user).update(mfa_verified_at=None)

    # Queue access without live MFA
    queue_resp = agent_client.get("/api/v1/admin/tickets")
    assert queue_resp.status_code == 403
    assert queue_resp.json()["code"] == "ADMIN_MFA_REQUIRED"

    # Every assigned-ticket action without live MFA
    for action_name, response in assigned_ticket_actions(agent_client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )


def test_an_assigned_agent_with_an_expired_mfa_proof_is_refused():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    IdentitySession.objects.filter(account=agent_user).update(
        mfa_verified_at=timezone.now() - timedelta(minutes=16)
    )

    # Queue access with expired MFA proof
    queue_resp = agent_client.get("/api/v1/admin/tickets")
    assert queue_resp.status_code == 403
    assert queue_resp.json()["code"] == "ADMIN_MFA_REQUIRED"

    # Every assigned-ticket action with expired MFA proof
    for action_name, response in assigned_ticket_actions(agent_client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )


def test_removing_the_support_scope_revokes_the_assigned_access():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)

    # Active assigned agent with scope and live MFA has access
    assert agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/messages").status_code == 200
    assert agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/sla").status_code == 200
    assert agent_client.get("/api/v1/admin/tickets").status_code == 200

    # Removing the SUPPORT scope immediately revokes all assigned actions without reassignment
    Account.objects.filter(pk=agent_user.pk).update(admin_scopes=["SUPPORT_QUEUE"])
    for action_name, response in assigned_ticket_actions(agent_client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )

    # Removing SUPPORT_QUEUE immediately revokes queue access
    Account.objects.filter(pk=agent_user.pk).update(admin_scopes=[])
    queue_resp = agent_client.get("/api/v1/admin/tickets")
    assert queue_resp.status_code == 403
    assert queue_resp.json()["code"] == "ADMIN_MFA_REQUIRED"


def test_a_student_role_is_refused_for_every_admin_action():
    client, _ = student()
    assigner_client, assigner = agent()
    ticket = create_ticket(client, request_human=True)
    assign(assigner_client, assigner, ticket)

    # A student session attempting queue access
    queue_resp = client.get("/api/v1/admin/tickets")
    assert queue_resp.status_code == 403
    assert queue_resp.json()["code"] == "ADMIN_MFA_REQUIRED"

    # A student session attempting assigned-ticket admin actions
    for action_name, response in assigned_ticket_actions(client, ticket):
        assert response.status_code == 403, f"{action_name} returned {response.status_code}"
        assert response.json()["code"] == "ADMIN_MFA_REQUIRED", (
            f"{action_name} returned {response.json()}"
        )


# --- 02: a replay re-checks authorization -----------------------------------


def queue_row(agent_client, ticket_id):
    queue = agent_client.get("/api/v1/admin/tickets").json()
    return next(item for item in queue["items"] if item["id"] == ticket_id)


def test_a_replay_after_reassignment_is_refused_without_disclosing_the_ticket():
    client, _ = student()
    agent_client, agent_user = agent()
    other_agent_client, other_agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200, first.content
    assign(
        agent_client,
        other_agent_user,
        ticket,
        revision=queue_row(agent_client, ticket["id"])["row_version"],
    )
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert replay.status_code == 403
    assert "Upload problem" not in replay.content.decode()
    assert PrivacyAudit.objects.filter(
        actor_id=agent_user.pk,
        action="support_ticket_access",
        outcome="DENY",
        resource_id=ticket["id"],
    ).exists()


def test_a_replay_after_scope_removal_is_refused_and_audited():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200, first.content
    Account.objects.filter(pk=agent_user.pk).update(admin_scopes=["SUPPORT_QUEUE"])
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert replay.status_code == 403
    assert replay.json()["code"] == "ADMIN_MFA_REQUIRED"
    assert "Upload problem" not in replay.content.decode()
    assert PrivacyAudit.objects.filter(
        actor_id=agent_user.pk,
        action="support_ticket_access",
        outcome="DENY",
        resource_id=ticket["id"],
    ).exists()


def test_a_replay_after_mfa_expiry_is_refused_and_audited():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200, first.content
    IdentitySession.objects.filter(account=agent_user).update(
        mfa_verified_at=timezone.now() - timedelta(minutes=20)
    )
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert replay.status_code == 403
    assert replay.json()["code"] == "ADMIN_MFA_REQUIRED"
    assert "Upload problem" not in replay.content.decode()
    assert PrivacyAudit.objects.filter(
        actor_id=agent_user.pk,
        action="support_ticket_access",
        outcome="DENY",
        resource_id=ticket["id"],
    ).exists()


def test_a_replay_after_support_scope_revocation_is_refused():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200, first.content

    # Revoking the support scope must block the replay
    Account.objects.filter(pk=agent_user.pk).update(admin_scopes=["SUPPORT_QUEUE"])
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert replay.status_code == 403
    assert replay.json()["code"] == "ADMIN_MFA_REQUIRED"


def test_a_replay_after_mfa_proof_expiration_is_refused():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200, first.content

    # Expiring the MFA proof must block the replay
    IdentitySession.objects.filter(account=agent_user).update(
        mfa_verified_at=timezone.now() - timedelta(minutes=16)
    )
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert replay.status_code == 403
    assert replay.json()["code"] == "ADMIN_MFA_REQUIRED"


def test_a_transition_and_classification_replay_after_scope_revocation_is_refused():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)

    trans_key = str(uuid.uuid4())
    trans_payload = {"to_state": "AWAITING_STUDENT", "reason_code": "Waiting on student"}
    current_rev = queue_row(agent_client, ticket["id"])["row_version"]
    trans_first = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        trans_payload,
        revision=current_rev,
        key=trans_key,
    )
    assert trans_first.status_code == 200, trans_first.content

    class_key = str(uuid.uuid4())
    class_payload = {"category": "TECHNICAL", "priority": "HIGH", "reason_code": "Classified"}
    current_rev = queue_row(agent_client, ticket["id"])["row_version"]
    class_first = request(
        agent_client,
        "put",
        f"admin/tickets/{ticket['id']}/classification",
        class_payload,
        revision=current_rev,
        key=class_key,
    )
    assert class_first.status_code == 200, class_first.content

    # Revoking support scope blocks both replays
    Account.objects.filter(pk=agent_user.pk).update(admin_scopes=["SUPPORT_QUEUE"])
    trans_replay = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        trans_payload,
        revision=current_rev,
        key=trans_key,
    )
    assert trans_replay.status_code == 403
    assert trans_replay.json()["code"] == "ADMIN_MFA_REQUIRED"

    class_replay = request(
        agent_client,
        "put",
        f"admin/tickets/{ticket['id']}/classification",
        class_payload,
        revision=current_rev,
        key=class_key,
    )
    assert class_replay.status_code == 403
    assert class_replay.json()["code"] == "ADMIN_MFA_REQUIRED"


def test_an_authorized_replay_returns_the_same_result_and_is_audited():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    key = str(uuid.uuid4())
    payload = {"body": "Please upload a PNG copy.", "request_human": False}
    first = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    replay = request(
        agent_client, "post", f"admin/tickets/{ticket['id']}/messages", payload, key=key
    )
    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert (
        PrivacyAudit.objects.filter(
            actor_id=agent_user.pk,
            action="support_ticket_access",
            outcome="ALLOW",
            resource_id=ticket["id"],
        ).count()
        >= 2
    )


# --- 03: the assigned agent can list the explicit attachments --------------


def test_the_assigned_agent_lists_the_explicit_attachments(private_settings):
    client, user = student()
    agent_client, agent_user = agent()
    other_agent_client, _ = agent()
    ticket = create_ticket(client, request_human=True)
    asset = file_services.store_bytes(user.pk, "cv.png", "image/png", png(), str(uuid.uuid4()))
    share = request(
        client, "post", f"tickets/{ticket['id']}/attachments", {"asset_id": str(asset.pk)}
    )
    assert share.status_code == 201, share.content
    assign(agent_client, agent_user, ticket)
    listing = agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    assert listing.status_code == 200, listing.content
    items = listing.json()["items"]
    assert items[0]["id"] == share.json()["id"]
    assert items[0]["state"] == "SHARED"
    refused = other_agent_client.get(f"/api/v1/admin/tickets/{ticket['id']}/attachments")
    assert refused.status_code == 403
    assert PrivacyAudit.objects.filter(action="support_attachments_read").exists()


# --- 04: one shared global allowance ----------------------------------------


def test_a_published_allowance_above_five_is_refused():
    agent_client, _ = agent()
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    response = request(
        agent_client,
        "post",
        "admin/policies/sla",
        {
            "timezone": "Asia/Hebron",
            "working_weekdays": [0, 1, 2, 3, 6],
            "opens_local": "09:00",
            "closes_local": "17:00",
            "holidays": [],
            "targets": DEFAULT_TARGETS,
            "ai_daily_messages": 9,
            "closure_days": 7,
            "reopen_days": 14,
            "rating_edit_days": 7,
            "warning_percent": 80,
            "effective_at": timezone.now().isoformat(),
            "reason_code": "Attempt to raise the experiment allowance.",
        },
        revision=current["version"],
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_POLICY"


def test_a_reduced_allowance_is_accepted():
    agent_client, _ = agent()
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    response = request(
        agent_client,
        "post",
        "admin/policies/sla",
        {
            "timezone": "Asia/Hebron",
            "working_weekdays": [0, 1, 2, 3, 6],
            "opens_local": "09:00",
            "closes_local": "17:00",
            "holidays": [],
            "targets": DEFAULT_TARGETS,
            "ai_daily_messages": 3,
            "closure_days": 7,
            "reopen_days": 14,
            "rating_edit_days": 7,
            "warning_percent": 80,
            "effective_at": timezone.now().isoformat(),
            "reason_code": "Reduced allowance for the resource pilot.",
        },
        revision=current["version"],
    )
    assert response.status_code == 201, response.content
    assert response.json()["ai_daily_messages"] == 3


def test_a_support_reply_and_a_credit_admission_share_one_allowance():
    client, user = student()
    day = business_day(timezone.now())
    GlobalDay.objects.get_or_create(day=day)
    GlobalAiDay.objects.get_or_create(day=day)
    global_ai = GlobalAiDay.objects.get(day=day)
    global_ai.operations = 99
    global_ai.save(update_fields=["operations"])
    ticket = create_ticket(client)
    result = request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    assert result.status_code == 200, result.content
    assert result.json()["ai"]["available"] is True
    grant_signup(user.pk)
    from credits.services import create_synthetic_input

    fixture = create_synthetic_input(user.pk)
    refused = None
    try:
        reserve(user.pk, "MATCHING_AI", str(uuid.uuid4()), fixture)
    except Exception as error:  # noqa: BLE001 -- the refusal code is asserted below.
        refused = error
    assert refused is not None
    assert getattr(refused, "code", "") == "GLOBAL_AI_CAP"


# --- 05: sensitive topics always hand off -----------------------------------


def test_a_mixed_financial_topic_hands_off_even_with_document_terms():
    client, _ = student()
    ticket = create_ticket(
        client,
        message="My payment receipt document upload failed and the file will not open.",
        subject="Payment receipt document problem",
        category="DOCUMENTS",
    )
    result = request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    assert result.status_code == 200, result.content
    assert "FINANCIAL_TOPIC" in result.json()["ai"]["reason"]
    assert result.json()["ticket"]["state"] == "AWAITING_ADMIN"
    assert result.json()["ticket"]["suggested_category"] != ""


def test_a_mixed_security_topic_hands_off_even_with_document_terms():
    client, _ = student()
    ticket = create_ticket(
        client,
        message="The document upload failed and someone changed my password without permission.",
        subject="Upload and password problem",
        category="DOCUMENTS",
    )
    result = request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    assert "SECURITY_TOPIC" in result.json()["ai"]["reason"]
    assert result.json()["ticket"]["state"] == "AWAITING_ADMIN"


def test_a_clean_documents_question_is_still_answered_by_the_ai():
    client, _ = student()
    ticket = create_ticket(
        client,
        message="The upload failed again and the portal is not working for me.",
        subject="Upload problem on the application portal",
        category="TECHNICAL",
    )
    result = request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    assert result.json()["ai"]["available"] is True
    assert result.json()["ticket"]["state"] == "AI_HANDLING"


# --- 06: two failed answers hand off ----------------------------------------


def test_two_student_reports_that_the_advice_did_not_help_hand_off():
    client, _ = student()
    ticket = create_ticket(client)
    request(client, "post", f"tickets/{ticket['id']}/ai-replies", {})
    first = request(
        client,
        "post",
        f"tickets/{ticket['id']}/messages",
        {"body": "That did not help, the upload still fails.", "request_human": False},
    )
    assert first.status_code == 200, first.content
    assert first.json()["state"] != "AWAITING_ADMIN"
    second = request(
        client,
        "post",
        f"tickets/{ticket['id']}/messages",
        {"body": "It still did not work for me at all.", "request_human": False},
    )
    assert second.status_code == 200, second.content
    assert second.json()["state"] == "AWAITING_ADMIN"


def test_a_failure_on_one_ticket_does_not_hand_off_another():
    client, _ = student()
    first = create_ticket(client)
    second = create_ticket(client)
    for _ in range(2):
        request(
            client,
            "post",
            f"tickets/{first['id']}/messages",
            {"body": "That did not help at all.", "request_human": False},
        )
    other = request(
        client,
        "post",
        f"tickets/{second['id']}/messages",
        {"body": "That did not help at all.", "request_human": False},
    )
    assert other.json()["state"] != "AWAITING_ADMIN"


# --- 08, 09, 10, 11: rating and lifecycle -----------------------------------


def test_a_first_rating_can_be_given_inside_the_window():
    client, _ = student()
    ticket = create_ticket(client, request_human=True)
    closed = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=ticket["row_version"],
    ).json()
    assert closed["rating_available"] is True
    assert closed["rating_editable"] is False
    rated = request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 4},
        revision=closed["row_version"],
    )
    assert rated.status_code == 200, rated.content
    assert rated.json()["value"] == 4


def test_an_expired_rating_stays_locked_after_a_re_resolution():
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
    ).json()
    request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 4},
        revision=resolved["row_version"],
    ).json()
    # The rating's own deadline passes, then the ticket is reopened and resolved again.
    from support.models import TicketRating

    assert TicketRating.objects.filter(ticket_id=ticket["id"]).count() == 1
    TicketRating.objects.filter(ticket_id=ticket["id"]).update(
        editable_until=timezone.now() - timedelta(days=1)
    )
    reopened = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=client.get(f"/api/v1/tickets/{ticket['id']}").json()["row_version"],
    ).json()
    again = request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "ANSWERED"},
        revision=reopened["row_version"],
    ).json()
    assert again["rating_editable"] is False
    refused = request(
        client,
        "put",
        f"tickets/{ticket['id']}/rating",
        {"rating": 2},
        revision=again["row_version"],
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "RATING_WINDOW_CLOSED"


def test_a_student_can_object_to_an_administrator_resolution():
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
    ).json()
    objected = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=resolved["row_version"],
    )
    assert objected.status_code == 200, objected.content
    assert objected.json()["state"] == "AWAITING_ADMIN"


def test_an_objection_after_the_quiet_period_is_refused():
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
    ).json()
    Ticket.objects.filter(pk=ticket["id"]).update(resolved_at=timezone.now() - timedelta(days=9))
    refused = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=resolved["row_version"],
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "REOPEN_WINDOW_CLOSED"


def test_a_reopened_ticket_can_be_closed_again():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    row = assign(agent_client, agent_user, ticket)
    request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "ANSWERED"},
        revision=row["row_version"],
    ).json()
    reopened = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=client.get(f"/api/v1/tickets/{ticket['id']}").json()["row_version"],
    ).json()
    assert reopened["closed_at"] is None
    assert reopened["resolved_at"] is None
    request(
        agent_client,
        "post",
        f"admin/tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "ANSWERED"},
        revision=reopened["row_version"],
    ).json()
    Ticket.objects.filter(pk=ticket["id"]).update(resolved_at=timezone.now() - timedelta(days=8))
    assert services.sweep()["closed"] == 1
    assert Ticket.objects.get(pk=ticket["id"]).state == "CLOSED"


# --- 12: the first human response clock -------------------------------------


def test_an_acknowledgement_does_not_satisfy_the_clock_but_a_short_answer_does():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    agent_reply(agent_client, ticket, "We will look into your issue and reply shortly.")
    assert sla(client, ticket)["met"] is False
    agent_reply(agent_client, ticket, "Please upload a PNG")
    assert sla(client, ticket)["met"] is True


def test_a_late_first_reply_records_the_breach_immediately():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    Ticket.objects.filter(pk=ticket["id"]).update(sla_due_at=timezone.now() - timedelta(minutes=5))
    agent_reply(agent_client, ticket, "Please upload a PNG")
    value = sla(client, ticket)
    assert value["met"] is True
    assert value["breached"] is True
    metrics = agent_client.get("/api/v1/admin/support/metrics").json()["tickets"]
    assert metrics["sla_breaches"] >= 1


# --- 13: exact business-hour arithmetic -------------------------------------


def test_one_business_minute_added_at_a_second_boundary_keeps_the_seconds():
    calendar = workcal.WorkingCalendar(
        timezone="Asia/Hebron",
        working_weekdays=(6, 0, 1, 2, 3),
        opens_local=time(9, 0),
        closes_local=time(17, 0),
        holidays=frozenset(),
    )
    start = datetime(2026, 10, 19, 16, 59, 30, tzinfo=HEBRON)
    due = workcal.add_business_seconds(calendar, start, 60)
    assert due == datetime(2026, 10, 20, 9, 0, 30, tzinfo=HEBRON)
    assert workcal.business_seconds(calendar, start, due) == 60


def test_a_transition_window_keeps_the_elapsed_duration_exact():
    calendar = workcal.WorkingCalendar(
        timezone="Asia/Hebron",
        working_weekdays=(0, 1, 2, 3, 4, 5, 6),
        opens_local=time(0, 0),
        closes_local=time(23, 59),
        holidays=frozenset(),
    )
    start = datetime(2026, 3, 28, 0, 0, tzinfo=HEBRON)
    end = datetime(2026, 3, 30, 0, 0, tzinfo=HEBRON)
    elapsed = workcal.business_seconds(calendar, start, end)
    # Two working days, each open until 23:59, across the spring-forward night.
    assert elapsed == 172800 - 120


# --- 14: a policy applies from its effective date ---------------------------


def test_a_future_policy_does_not_change_todays_tickets():
    client, _ = student()
    agent_client, _ = agent()
    ticket = create_ticket(client, request_human=True)
    before = sla(client, ticket)
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    response = request(
        agent_client,
        "post",
        "admin/policies/sla",
        {
            "timezone": "Asia/Hebron",
            "working_weekdays": [0, 1, 2, 3, 6],
            "opens_local": "08:00",
            "closes_local": "16:00",
            "holidays": [],
            "targets": {**DEFAULT_TARGETS, "NORMAL": 60},
            "ai_daily_messages": 5,
            "closure_days": 7,
            "reopen_days": 14,
            "rating_edit_days": 7,
            "warning_percent": 80,
            "effective_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "reason_code": "Next season working hours.",
        },
        revision=current["version"],
    )
    assert response.status_code == 201, response.content
    after = sla(client, ticket)
    assert after["computed_due_at"] == before["computed_due_at"]
    fresh = create_ticket(client, request_human=True)
    assert sla(client, fresh)["target_business_minutes"] == 1440


# --- 15: the closure sweep closes every due ticket --------------------------


def test_the_sweep_closes_every_due_ticket_whatever_its_closure_policy():
    client, _ = student()
    agent_client, agent_user = agent()
    long_policy = create_ticket(client, request_human=True)
    short_policy = create_ticket(client, request_human=True)
    for ticket in (long_policy, short_policy):
        row = assign(agent_client, agent_user, ticket)
        resolved = request(
            agent_client,
            "post",
            f"admin/tickets/{ticket['id']}/transitions",
            {"to_state": "RESOLVED", "reason_code": "ANSWERED"},
            revision=row["row_version"],
        )
        assert resolved.status_code == 200, resolved.content
    # The long-policy ticket captured a 30 day quiet period; the other keeps 7.
    long_calendar = SupportCalendar.objects.create(
        version=900,
        timezone="Asia/Hebron",
        working_weekdays=[0, 1, 2, 3, 6],
        opens_local="09:00",
        closes_local="17:00",
        holidays=[],
        targets=DEFAULT_TARGETS,
        ai_daily_messages=5,
        closure_days=30,
        reopen_days=14,
        rating_edit_days=7,
        warning_percent=80,
        reason="Long quiet period fixture.",
    )
    Ticket.objects.filter(pk=long_policy["id"]).update(
        resolved_at=timezone.now() - timedelta(days=8), sla_policy=long_calendar
    )
    Ticket.objects.filter(pk=short_policy["id"]).update(
        resolved_at=timezone.now() - timedelta(days=8)
    )
    result = services.sweep()
    assert result["closed"] == 1
    assert Ticket.objects.get(pk=short_policy["id"]).state == "CLOSED"
    assert Ticket.objects.get(pk=long_policy["id"]).state == "RESOLVED"
    assert services.sweep()["closed"] == 0


# --- 16: the initial priority binds the target ------------------------------


def test_the_declared_urgency_binds_the_first_response_target():
    client, _ = student()
    ticket = create_ticket(client, request_human=True, urgency="CRITICAL")
    value = sla(client, ticket)
    assert value["target_business_minutes"] == 240


def test_a_later_reclassification_does_not_rewrite_a_measured_cycle():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True, urgency="HIGH")
    row = assign(agent_client, agent_user, ticket)
    before = sla(client, ticket)
    classified = request(
        agent_client,
        "put",
        f"admin/tickets/{ticket['id']}/classification",
        {"category": "TECHNICAL", "priority": "LOW", "reason_code": "LATER_REVIEW"},
        revision=row["row_version"],
    )
    assert classified.status_code == 200, classified.content
    after = sla(client, ticket)
    assert after["target_business_minutes"] == before["target_business_minutes"]
    assert after["computed_due_at"] == before["computed_due_at"]


# --- 17: a completed cycle stays measurable ---------------------------------


def test_a_completed_cycle_stays_readable_after_a_reopen():
    client, _ = student()
    agent_client, agent_user = agent()
    ticket = create_ticket(client, request_human=True)
    assign(agent_client, agent_user, ticket)
    agent_reply(agent_client, ticket, "Please upload a PNG")
    first = sla(client, ticket)
    assert first["cycles"] and first["cycles"][0]["state"] == "COMPLETED"
    closed = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
        revision=client.get(f"/api/v1/tickets/{ticket['id']}").json()["row_version"],
    ).json()
    reopened = request(
        client,
        "post",
        f"tickets/{ticket['id']}/transitions",
        {"to_state": "AWAITING_ADMIN", "reason_code": "STUDENT_REOPENED"},
        revision=closed["row_version"],
    ).json()
    after = sla(client, ticket)
    assert len(after["cycles"]) == 2
    assert after["cycles"][0]["responded_at"] is not None
    assert after["cycles"][0]["cycle_no"] == 1
    assert reopened["sla"]["cycle_no"] == 2
    metrics = agent_client.get("/api/v1/admin/support/metrics").json()["tickets"]
    assert metrics["measured_cycles"] >= 2
    assert metrics["first_human_responses"] >= 1


# --- 18: impossible calendar values are refused ------------------------------


def test_an_invalid_calendar_value_is_a_client_error():
    agent_client, _ = agent()
    current = agent_client.get("/api/v1/admin/policies/sla/current").json()
    base = {
        "timezone": "Asia/Hebron",
        "working_weekdays": [0, 1, 2, 3, 6],
        "opens_local": "09:00",
        "closes_local": "17:00",
        "holidays": [],
        "targets": DEFAULT_TARGETS,
        "ai_daily_messages": 5,
        "closure_days": 7,
        "reopen_days": 14,
        "rating_edit_days": 7,
        "warning_percent": 80,
        "effective_at": timezone.now().isoformat(),
        "reason_code": "Invalid clock value probe.",
    }
    for field, value in (
        ("opens_local", "not-a-time"),
        ("closes_local", "25:00"),
        ("holidays", ["2026-02-31"]),
        ("working_weekdays", []),
    ):
        payload = {**base, field: value}
        response = request(
            agent_client, "post", "admin/policies/sla", payload, revision=current["version"]
        )
        assert response.status_code == 400, (field, response.content)
        assert response.json()["code"] in {"INVALID_POLICY", "INVALID_REQUEST"}


# --- 19: the student attach journey and the ledger stay untouched -----------


def test_the_student_attach_journey_and_the_unchanged_ledger(private_settings):
    client, user = student()
    ticket = create_ticket(client, request_human=True)
    grant_signup(user.pk)
    asset = file_services.store_bytes(user.pk, "cv.png", "image/png", png(), str(uuid.uuid4()))
    share = request(
        client, "post", f"tickets/{ticket['id']}/attachments", {"asset_id": str(asset.pk)}
    )
    assert share.status_code == 201, share.content
    listed = client.get(f"/api/v1/tickets/{ticket['id']}/attachments").json()["items"]
    assert listed[0]["id"] == share.json()["id"]
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").count() == 0


def test_a_student_cannot_share_another_students_file(private_settings):
    client, _ = student()
    other, other_user = student()
    ticket = create_ticket(client, request_human=True)
    asset = file_services.store_bytes(
        other_user.pk, "cv.png", "image/png", png(), str(uuid.uuid4())
    )
    refused = request(
        client, "post", f"tickets/{ticket['id']}/attachments", {"asset_id": str(asset.pk)}
    )
    assert refused.status_code in (403, 404)
