"""Catalog acceptance tests using only authored, synthetic source data."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from catalog.models import (
    CatalogAudit,
    ModerationEvent,
    Scholarship,
    ScholarshipVersion,
    SourceRevision,
)
from catalog.serializers import SourceInputSerializer
from catalog.services import moderate as moderate_service
from catalog.services import write_source
from django.db import DatabaseError, connections, transaction
from django.db.models import F
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, digest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-catalog-passphrase-529!"  # noqa: S105 -- public synthetic fixture.


@pytest.fixture(autouse=True)
def catalog_settings(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]


def csrf(client):
    response = client.get("/api/v1/session/csrf")
    assert response.status_code == 200, response.content
    return response.json()["csrf_token"]


def post(client, path, payload, revision=None, key=None):
    headers = {
        "HTTP_X_CSRFTOKEN": csrf(client),
        "HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4()),
    }
    if revision is not None:
        headers["HTTP_IF_MATCH"] = f'"{revision}"'
    return client.post("/api/v1/" + path, payload, format="json", **headers)


def signed_client(role="ADMIN", scopes=None, mfa=True):
    user = Account.objects.create_user(
        f"catalog-{uuid.uuid4()}@example.invalid",
        PASSWORD,
        birth_date=date(2000, 1, 1),
        locale="en",
        state="ACTIVE",
        email_verified_at=timezone.now(),
        role=role,
        admin_scopes=scopes if scopes is not None else ["MODERATION", "SOURCE_APPROVAL"],
    )
    client = APIClient(enforce_csrf_checks=True)
    response = post(client, "session/login", {"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.content
    if mfa:
        # Synthetic server proof only: no endpoint accepts a client MFA claim.
        IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
            mfa_verified_at=timezone.now()
        )
    return client, user


@pytest.fixture
def moderator():
    return signed_client()[0]


def source_payload(**overrides):
    now = timezone.now()
    return {
        "name": "Authored synthetic scholarship source",
        "url": "https://fixtures.example.invalid/scholarships",
        "permission_status": "APPROVED",
        "license_basis": "Original synthetic fixture, authored for these tests.",
        "permission_evidence": "Synthetic fixture authorization; no external website accessed.",
        "date_checked": now.isoformat(),
        "valid_until": (now + timedelta(days=90)).isoformat(),
        "allow_manual": True,
        "allow_import": False,
        "freshness_days": 30,
        "reason": "Synthetic source registry acceptance fixture.",
        **overrides,
    }


def create_source(client, **overrides):
    response = post(client, "admin/sources", source_payload(**overrides))
    assert response.status_code == 201, response.content
    return response.json()


def candidate_payload(source, **overrides):
    return {
        "source_id": source["id"],
        "title": "Synthetic engineering scholarship",
        "provider": "Synthetic university",
        "summary": "Authored example for testing a public catalog, without real award claims.",
        "education_levels": ["MASTER"],
        "disciplines": ["engineering"],
        "countries": ["PS"],
        "languages": ["en"],
        "funding": "PARTIAL",
        "criteria": ["Synthetic eligibility criterion, not a real award."],
        "required_documents": ["Synthetic transcript requirement"],
        "submission_url": "https://fixtures.example.invalid/apply",
        "rounds": [{"kind": "UNKNOWN", "label": "Synthetic unknown round"}],
        "source_checked_at": timezone.now().isoformat(),
        "internal_notes": "INTERNAL-SYNTHETIC-NOTE-do-not-publish",
        "origin": "MANUAL",
        "reason": "Authored synthetic candidate.",
        **overrides,
    }


def create_candidate(client, source, **overrides):
    response = post(client, "admin/scholarships", candidate_payload(source, **overrides))
    assert response.status_code == 201, response.content
    return response.json()


def moderate(client, candidate, action="APPROVE", version_id=None):
    return post(
        client,
        f"admin/scholarships/{candidate['id']}/moderation",
        {
            "version_id": version_id or candidate["latest"]["id"],
            "action": action,
            "reason": f"Synthetic human decision: {action}.",
        },
        revision=candidate["revision"],
    )


def publish(client, source, **overrides):
    candidate = create_candidate(client, source, **overrides)
    response = moderate(client, candidate)
    assert response.status_code == 200, response.content
    return response.json()


def public_items(**params):
    response = APIClient().get("/api/v1/scholarships", params)
    assert response.status_code == 200, response.content
    return response.json()


def test_source_registry_defaults_unverified_and_never_enables_automation(moderator):
    payload = source_payload()
    payload.pop("permission_status")
    payload.pop("date_checked")
    payload.pop("valid_until")
    response = post(moderator, "admin/sources", payload)
    assert response.status_code == 201, response.content
    source = response.json()
    assert source["permission_status"] == "UNVERIFIED"
    assert source["automation_enabled"] is False
    assert source["editor_id"] and source["revision"] == 1
    assert public_items()["items"] == []


@pytest.mark.parametrize(
    "override",
    [
        {"license_basis": ""},
        {"permission_evidence": ""},
        {"date_checked": None},
        {"freshness_days": 0},
        {"freshness_days": 366},
        {"date_checked": "2099-01-01T00:00:00Z"},
    ],
)
def test_source_approval_requires_explicit_checked_legal_use_evidence(moderator, override):
    response = post(moderator, "admin/sources", source_payload(**override))
    assert response.status_code == 400, response.content
    assert moderator.get("/api/v1/admin/sources").json()["items"] == []


@pytest.mark.parametrize("status", ["UNVERIFIED", "BLOCKED", "REVOKED"])
def test_unapproved_sources_cannot_import_or_publish_and_make_no_network_call(moderator, status):
    source = create_source(moderator, permission_status=status, allow_import=True)
    with patch("socket.create_connection", side_effect=AssertionError("Network access forbidden")):
        response = post(
            moderator,
            "admin/scholarships",
            candidate_payload(source, origin="IMPORT"),
        )
        assert response.status_code in {403, 409}, response.content
        manual = post(moderator, "admin/scholarships", candidate_payload(source))
        assert manual.status_code in {201, 403, 409}, manual.content
        if manual.status_code == 201:
            assert moderate(moderator, manual.json()).status_code in {403, 409}
    assert public_items()["items"] == []


def test_individually_permitted_import_is_a_draft_and_never_fetches(moderator):
    source = create_source(moderator, allow_import=True)
    with patch("socket.create_connection", side_effect=AssertionError("Network access forbidden")):
        candidate = create_candidate(moderator, source, origin="IMPORT")
    assert candidate["published_version_id"] is None
    assert APIClient().get(f"/api/v1/scholarships/{candidate['id']}").status_code == 404
    assert public_items()["total"] == 0
    response = moderate(moderator, candidate)
    assert response.status_code == 200, response.content
    assert public_items()["total"] == 1


def test_source_manual_permission_does_not_imply_permission_to_import(moderator):
    source = create_source(moderator, allow_manual=True, allow_import=False)
    response = post(moderator, "admin/scholarships", candidate_payload(source, origin="IMPORT"))
    assert response.status_code == 403
    assert public_items()["total"] == 0


@pytest.mark.parametrize(
    ("role", "scopes", "mfa"),
    [
        ("STUDENT", [], False),
        ("ADMIN", [], True),
        ("ADMIN", ["MODERATION"], False),
        ("ADMIN", ["SOURCE_APPROVAL"], True),
    ],
)
def test_admin_catalog_denies_wrong_role_scope_or_absent_server_mfa(role, scopes, mfa):
    client, _ = signed_client(role, scopes, mfa)
    assert client.get("/api/v1/admin/sources").status_code == 403
    assert client.get("/api/v1/admin/scholarships").status_code == 403
    assert post(client, "admin/sources", source_payload()).status_code == 403


def test_anonymous_public_reads_are_open_but_admin_and_unsafe_calls_are_guarded(moderator):
    anonymous = APIClient(enforce_csrf_checks=True)
    assert anonymous.get("/api/v1/scholarships").status_code == 200
    assert anonymous.get("/api/v1/admin/scholarships").status_code in {401, 403}
    response = anonymous.post("/api/v1/admin/sources", source_payload(), format="json")
    assert response.status_code == 403
    response = moderator.post("/api/v1/admin/sources", source_payload(), format="json")
    assert response.status_code == 403 and response.json()["code"] == "CSRF_FAILED"


def test_moderation_scope_cannot_self_approve_source_permission():
    client, _ = signed_client(scopes=["MODERATION"])
    response = post(client, "admin/sources", source_payload())
    assert response.status_code == 403
    response = post(
        client,
        "admin/sources",
        source_payload(permission_status="UNVERIFIED", date_checked=None, valid_until=None),
    )
    assert response.status_code == 201, response.content


def test_server_mfa_expiry_boundary_denies_catalog_access(moderator):
    now = timezone.now()
    IdentitySession.objects.filter(digest=digest(moderator.session.session_key)).update(
        mfa_verified_at=now - timedelta(minutes=15)
    )
    with patch("django.utils.timezone.now", return_value=now):
        assert moderator.get("/api/v1/admin/sources").status_code == 403


def test_public_projection_traces_approved_version_and_omits_internal_fields(moderator):
    source = create_source(moderator)
    candidate = create_candidate(moderator, source)
    assert public_items()["items"] == []
    response = moderate(moderator, candidate)
    assert response.status_code == 200, response.content
    body = APIClient().get(f"/api/v1/scholarships/{candidate['id']}").json()
    assert set(body) == {
        "id",
        "version_id",
        "version",
        "title",
        "provider",
        "summary",
        "education_levels",
        "disciplines",
        "countries",
        "languages",
        "funding",
        "criteria",
        "required_documents",
        "submission_url",
        "source",
        "source_checked_at",
        "verified_at",
        "freshness",
        "rounds",
        "next_deadline",
        "reminder_eligible",
    }
    assert body["version_id"] == candidate["latest"]["id"]
    assert body["source"]["id"] == source["id"]
    assert body["source"]["version_id"] == candidate["latest"]["source_revision_id"]
    assert set(body["source"]) == {"id", "version_id", "name", "url"}
    assert "INTERNAL-SYNTHETIC-NOTE" not in str(body)
    assert "permission_evidence" not in str(body) and "actor_id" not in str(body)
    assert public_items()["items"][0] == body
    assert public_items(q="INTERNAL-SYNTHETIC-NOTE")["items"] == []


def test_rejected_candidate_stays_private_and_review_history_is_attributed(moderator):
    source = create_source(moderator)
    candidate = create_candidate(moderator, source)
    response = moderate(moderator, candidate, "REJECT")
    assert response.status_code == 200, response.content
    assert public_items()["total"] == 0
    body = response.json()
    assert body["history"][-1]["action"] == "REJECT"
    assert body["history"][-1]["actor_id"]
    assert body["history"][-1]["version_id"] == candidate["latest"]["id"]


def test_material_edit_creates_version_and_requires_a_new_human_decision(moderator):
    source = create_source(moderator)
    published = publish(moderator, source)
    original_version = published["published_version_id"]
    response = post(
        moderator,
        f"admin/scholarships/{published['id']}/versions",
        candidate_payload(source, title="Changed synthetic title", funding="FULL"),
        revision=published["revision"],
    )
    assert response.status_code == 200, response.content
    edited = response.json()
    assert edited["latest"]["id"] != original_version
    assert edited["latest"]["version"] == 2
    assert edited["published_version_id"] == original_version
    # A material update conservatively removes visibility while the new facts await review.
    assert APIClient().get(f"/api/v1/scholarships/{published['id']}").status_code == 404
    assert public_items()["total"] == 0
    response = moderate(moderator, edited)
    assert response.status_code == 200, response.content
    public = APIClient().get(f"/api/v1/scholarships/{published['id']}").json()
    assert public["version_id"] == edited["latest"]["id"] and public["funding"] == "FULL"


def test_stale_optimistic_revision_cannot_replace_newer_review(moderator):
    source = create_source(moderator)
    candidate = create_candidate(moderator, source)
    assert moderate(moderator, candidate).status_code == 200
    assert moderate(moderator, candidate, "REJECT").status_code == 412
    assert public_items()["items"][0]["version_id"] == candidate["latest"]["id"]


def test_source_permission_revocation_removes_public_access_without_rewriting_version(moderator):
    source = create_source(moderator)
    published = publish(moderator, source)
    response = post(
        moderator,
        f"admin/sources/{source['id']}/versions",
        source_payload(permission_status="REVOKED"),
        revision=source["revision"],
    )
    assert response.status_code == 200, response.content
    assert public_items()["total"] == 0
    assert APIClient().get(f"/api/v1/scholarships/{published['id']}").status_code == 404
    admin = moderator.get(f"/api/v1/admin/scholarships/{published['id']}").json()
    assert admin["published_version_id"] == published["published_version_id"]


def test_source_permission_expiry_hides_public_listing_at_the_exact_boundary(moderator):
    expires = timezone.now() + timedelta(days=1)
    source = create_source(moderator, valid_until=expires.isoformat())
    published = publish(moderator, source)
    with patch("django.utils.timezone.now", return_value=expires - timedelta(microseconds=1)):
        assert public_items()["total"] == 1
    with patch("django.utils.timezone.now", return_value=expires):
        assert public_items()["total"] == 0
        assert APIClient().get(f"/api/v1/scholarships/{published['id']}").status_code == 404


@pytest.mark.parametrize("freshness_days,age,expected", [(None, 0, "UNKNOWN"), (30, 31, "STALE")])
def test_unconfigured_or_stale_freshness_never_claims_current_or_eligible_reminder(
    moderator, freshness_days, age, expected
):
    source = create_source(moderator, freshness_days=freshness_days)
    candidate = publish(
        moderator,
        source,
        source_checked_at=(timezone.now() - timedelta(days=age)).isoformat(),
        rounds=[
            {
                "kind": "CONFIRMED",
                "source_text": "Synthetic source explicitly states this time and timezone.",
                "closes_at": "2029-01-15T16:00:00Z",
                "timezone": "UTC",
            }
        ],
    )
    body = APIClient().get(f"/api/v1/scholarships/{candidate['id']}").json()
    assert body["freshness"] == expected and body["reminder_eligible"] is False


def test_candidate_creation_is_idempotent_and_changed_retry_conflicts(moderator):
    source = create_source(moderator)
    payload = candidate_payload(source)
    key = str(uuid.uuid4())
    first = post(moderator, "admin/scholarships", payload, key=key)
    second = post(moderator, "admin/scholarships", payload, key=key)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    conflict = post(moderator, "admin/scholarships", {**payload, "title": "Changed retry"}, key=key)
    assert conflict.status_code == 409
    assert moderator.get("/api/v1/admin/scholarships").json()["total"] == 1


def test_reverify_and_suspend_remove_public_access_by_attributed_human_decision(moderator):
    source = create_source(moderator)
    published = publish(moderator, source)
    response = moderate(moderator, published, "REVERIFY")
    assert response.status_code == 200, response.content
    assert APIClient().get(f"/api/v1/scholarships/{published['id']}").status_code == 404
    response = moderate(moderator, response.json(), "SUSPEND")
    assert response.status_code == 200, response.content
    assert public_items()["total"] == 0


def test_arabic_and_english_full_text_filters_and_clear_empty_result(moderator):
    source = create_source(moderator)
    arabic = publish(
        moderator,
        source,
        title="منحة هندسة اصطناعية",
        summary="برنامج اصطناعي لدراسة الطاقة والهندسة",
        languages=["ar"],
        funding="FULL",
        countries=["PS"],
    )
    english = publish(
        moderator,
        source,
        title="Synthetic medical research fellowship",
        education_levels=["PHD"],
        disciplines=["medicine"],
        countries=["GB"],
    )
    result = public_items(q="هندسة", language="ar", funding="FULL", country="PS")
    assert [item["id"] for item in result["items"]] == [arabic["id"]]
    assert result["search_mode"] == "TEXT"
    result = public_items(q="medical", education_level="PHD", discipline="medicine")
    assert [item["id"] for item in result["items"]] == [english["id"]]
    assert public_items(q="nonexistentfixtureword")["items"] == []
    assert public_items(q="medical", funding="FULL")["total"] == 0


def test_public_pagination_is_bounded_and_deterministic(moderator):
    source = create_source(moderator)
    ids = {publish(moderator, source, title=f"Synthetic award {index}")["id"] for index in range(3)}
    first = public_items(page_size=2)
    second = public_items(page=2, page_size=2)
    assert first["total"] == second["total"] == 3
    assert first["page"] == 1 and second["page"] == 2
    first_ids = [item["id"] for item in first["items"]]
    second_ids = [item["id"] for item in second["items"]]
    assert len(first_ids) == 2 and len(second_ids) == 1
    assert set(first_ids).isdisjoint(second_ids) and set(first_ids + second_ids) == ids
    assert public_items(page_size=2)["items"] == first["items"]


@pytest.mark.parametrize(
    "query",
    [
        {"page": "0"},
        {"page": "bad"},
        {"page_size": "51"},
        {"page_size": "0"},
        {"q": "x" * 201},
        {"mode": "VECTOR"},
        {"funding": "guaranteed"},
        {"education_level": "DOCTORATE"},
        {"sort": "made-up"},
        {"deadline_before": "2029-02-30"},
        {"owner_id": str(uuid.uuid4())},
    ],
)
def test_public_search_rejects_invalid_or_unsupported_filters(query):
    response = APIClient().get("/api/v1/scholarships", query)
    assert response.status_code == 400, response.content


def test_semantic_search_is_explicitly_unavailable_and_does_not_contact_a_provider():
    with patch("socket.create_connection", side_effect=AssertionError("Network access forbidden")):
        response = APIClient().get("/api/v1/scholarships", {"q": "synthetic", "mode": "SEMANTIC"})
    assert response.status_code == 503
    assert response.json()["code"] == "SEARCH_MODE_UNAVAILABLE"


@pytest.mark.parametrize(
    "rounds",
    [
        [{"kind": "UNKNOWN", "label": "Unknown synthetic deadline"}],
        [{"kind": "ROLLING", "label": "Source explicitly says rolling"}],
        [{"kind": "DATE_ONLY", "deadline_date": "2029-06-30", "label": "Date only"}],
    ],
)
def test_unknown_rolling_and_date_only_deadlines_never_invent_instants_or_reminders(
    moderator, rounds
):
    source = create_source(moderator)
    candidate = publish(moderator, source, rounds=rounds)
    body = APIClient().get(f"/api/v1/scholarships/{candidate['id']}").json()
    assert body["next_deadline"] is None and body["reminder_eligible"] is False
    assert body["rounds"][0]["closes_at"] is None
    assert public_items(deadline_before="2030-01-01")["items"] == []


def test_confirmed_deadline_keeps_donor_zone_and_converts_only_verified_instant(moderator):
    source = create_source(moderator)
    candidate = publish(
        moderator,
        source,
        rounds=[
            {
                "kind": "CONFIRMED",
                "label": "Synthetic winter round",
                "source_text": "Synthetic source explicitly states 15 January at 17:00 Paris time.",
                "closes_at": "2029-01-15T17:00:00+01:00",
                "timezone": "Europe/Paris",
            }
        ],
    )
    body = APIClient().get(f"/api/v1/scholarships/{candidate['id']}").json()
    instant = datetime.fromisoformat(body["next_deadline"].replace("Z", "+00:00"))
    assert instant == datetime(2029, 1, 15, 16, tzinfo=UTC)
    assert body["rounds"][0]["timezone"] == "Europe/Paris"
    assert body["reminder_eligible"] is True
    assert public_items(deadline_before="2029-01-16")["total"] == 1
    assert public_items(deadline_before="2029-01-14")["total"] == 0


def test_reviewed_deadline_canonical_instant_round_trips_when_creating_a_new_version(moderator):
    source = create_source(moderator)
    published = publish(
        moderator,
        source,
        rounds=[
            {
                "kind": "CONFIRMED",
                "source_text": "Synthetic source states 15 January 2029 at 17:00 Paris time.",
                "closes_at": "2029-01-15T17:00:00+01:00",
                "timezone": "Europe/Paris",
            }
        ],
    )
    response = post(
        moderator,
        f"admin/scholarships/{published['id']}/versions",
        candidate_payload(
            source,
            summary="New synthetic summary; source deadline unchanged.",
            rounds=published["latest"]["rounds"],
        ),
        revision=published["revision"],
    )
    assert response.status_code == 200, response.content
    revised = response.json()
    assert revised["latest"]["rounds"] == published["latest"]["rounds"]
    assert revised["visibility"] == "REVERIFY"
    assert public_items()["total"] == 0


def test_multiple_rounds_choose_next_future_confirmed_deadline_and_ignore_past_rounds(moderator):
    source = create_source(moderator)
    published = publish(
        moderator,
        source,
        rounds=[
            {
                "kind": "CONFIRMED",
                "label": "Synthetic past round",
                "source_text": "Synthetic source states 1 January 2025 UTC.",
                "closes_at": "2025-01-01T12:00:00Z",
                "timezone": "UTC",
            },
            {"kind": "UNKNOWN", "label": "Unconfirmed future round"},
            {
                "kind": "CONFIRMED",
                "label": "Synthetic future round",
                "source_text": "Synthetic source states 1 January 2029 UTC.",
                "closes_at": "2029-01-01T12:00:00Z",
                "timezone": "UTC",
            },
        ],
    )
    body = APIClient().get(f"/api/v1/scholarships/{published['id']}").json()
    instant = datetime.fromisoformat(body["next_deadline"].replace("Z", "+00:00"))
    assert instant == datetime(2029, 1, 1, 12, tzinfo=UTC)
    assert len(body["rounds"]) == 3
    assert public_items(deadline_before="2027-01-01")["total"] == 0


@pytest.mark.parametrize(
    "round_data",
    [
        {"kind": "CONFIRMED", "closes_at": "2029-01-15T17:00:00"},
        {"kind": "CONFIRMED", "closes_at": "2029-01-15T17:00:00Z", "timezone": "Mars/Base"},
        {"kind": "CONFIRMED", "closes_at": "2029-01-15T17:00:00+03:00", "timezone": "Europe/Paris"},
        {"kind": "CONFIRMED", "closes_at": "2029-03-25T02:30:00", "timezone": "Europe/Paris"},
        {"kind": "CONFIRMED", "closes_at": "2029-10-28T02:30:00", "timezone": "Europe/Paris"},
        {"kind": "DATE_ONLY", "deadline_date": "2029-02-30"},
        {"kind": "UNKNOWN", "closes_at": "2029-01-15T17:00:00Z"},
    ],
)
def test_invalid_ambiguous_or_inconsistent_deadlines_are_rejected(moderator, round_data):
    source = create_source(moderator)
    response = post(
        moderator,
        "admin/scholarships",
        candidate_payload(
            source, rounds=[{"source_text": "Synthetic source evidence.", **round_data}]
        ),
    )
    assert response.status_code == 400, response.content
    assert public_items()["total"] == 0


def test_submission_url_and_read_only_field_injection_are_rejected(moderator):
    source = create_source(moderator)
    for override in [
        {"submission_url": "javascript:alert(1)"},
        {"submission_url": "https://fixtures.example.invalid:99999/apply"},
        {"published_version_id": str(uuid.uuid4())},
        {"visibility": "PUBLISHED"},
        {"approved": True},
        {"created_by": str(uuid.uuid4())},
    ]:
        response = post(moderator, "admin/scholarships", candidate_payload(source, **override))
        assert response.status_code == 400, response.content
    assert public_items()["total"] == 0


def test_duplicate_candidates_are_flagged_without_merging_or_publication(moderator):
    source = create_source(moderator)
    original = create_candidate(moderator, source)
    duplicate = create_candidate(moderator, source)
    assert original["id"] != duplicate["id"]
    assert original["id"] in duplicate["latest"]["duplicate_ids"]
    assert public_items()["total"] == 0


def test_versions_moderation_and_catalog_audit_are_immutable_at_database_boundary(moderator):
    source = create_source(moderator)
    published = publish(moderator, source)
    version = ScholarshipVersion.objects.get(pk=published["published_version_id"])
    approval = ModerationEvent.objects.get(version=version, action="APPROVE")
    assert approval.content_hash == version.content_hash
    changes = [
        lambda: ScholarshipVersion.objects.filter(pk=version.pk).update(
            title="Unreviewed overwrite"
        ),
        lambda: SourceRevision.objects.filter(pk=version.source_revision_id).update(
            license_basis="Overwritten permission basis"
        ),
        lambda: ModerationEvent.objects.filter(pk=approval.pk).delete(),
        lambda: CatalogAudit.objects.filter(resource_id=published["id"]).update(reason="overwrite"),
    ]
    for change in changes:
        with pytest.raises(DatabaseError), transaction.atomic():
            change()
    assert public_items()["items"][0]["title"] == "Synthetic engineering scholarship"


def test_direct_database_publication_cannot_bypass_human_approval(moderator):
    candidate = create_candidate(moderator, create_source(moderator))
    with pytest.raises(DatabaseError), transaction.atomic():
        Scholarship.objects.filter(pk=candidate["id"]).update(
            visibility="PUBLISHED",
            published_version_id=candidate["latest"]["id"],
            revision=F("revision") + 1,
        )
    assert public_items()["total"] == 0


@pytest.mark.django_db(transaction=True)
def test_publication_racing_permission_revocation_never_leaves_source_public():
    publisher, publishing_user = signed_client()
    revoker, revoking_user = signed_client()
    source = create_source(publisher)
    candidate = create_candidate(publisher, source)
    publishing_proof = IdentitySession.objects.get(digest=digest(publisher.session.session_key))
    revoking_proof = IdentitySession.objects.get(digest=digest(revoker.session.session_key))
    serializer = SourceInputSerializer(data=source_payload(permission_status="REVOKED"))
    serializer.is_valid(raise_exception=True)
    barrier = Barrier(2)

    def approve():
        moderate_service(
            publishing_user,
            publishing_proof,
            uuid.UUID(candidate["id"]),
            {
                "version_id": uuid.UUID(candidate["latest"]["id"]),
                "action": "APPROVE",
                "reason": "Synthetic concurrent publication review.",
            },
            candidate["revision"],
            None,
        )
        return "APPROVED"

    def revoke():
        write_source(
            revoking_user,
            revoking_proof,
            serializer.validated_data,
            None,
            uuid.UUID(source["id"]),
            source["revision"],
        )
        return "REVOKED"

    def run(action):
        try:
            barrier.wait(timeout=10)
            return action()
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, (approve, revoke)))
    assert outcomes[1] == "REVOKED"
    assert outcomes[0] in {"APPROVED", "SOURCE_NOT_PERMITTED"}
    assert public_items()["total"] == 0


def test_replacing_approved_source_permission_requires_new_candidate_review(moderator):
    source = create_source(moderator)
    published = publish(moderator, source)
    replacement = post(
        moderator,
        f"admin/sources/{source['id']}/versions",
        source_payload(license_basis="New synthetic license scope; needs a new fact review."),
        revision=source["revision"],
    )
    assert replacement.status_code == 200, replacement.content
    assert public_items()["total"] == 0
    assert APIClient().get(f"/api/v1/scholarships/{published['id']}").status_code == 404
    # An existing approval cannot be reused under the replacement permission snapshot.
    assert moderate(moderator, published, "REVERIFY").status_code == 200
    current = moderator.get(f"/api/v1/admin/scholarships/{published['id']}").json()
    assert moderate(moderator, current).status_code == 403
    revised = post(
        moderator,
        f"admin/scholarships/{published['id']}/versions",
        candidate_payload(replacement.json()),
        revision=current["revision"],
    )
    assert revised.status_code == 200, revised.content
    assert moderate(moderator, revised.json()).status_code == 200
    assert public_items()["total"] == 1


def test_restore_returns_to_review_without_automatic_republication(moderator):
    published = publish(moderator, create_source(moderator))
    suspended = moderate(moderator, published, "SUSPEND")
    assert suspended.status_code == 200
    restored = moderate(moderator, suspended.json(), "RESTORE")
    assert restored.status_code == 200, restored.content
    assert restored.json()["visibility"] == "REVERIFY"
    assert public_items()["total"] == 0
    assert moderate(moderator, restored.json()).status_code == 200
    assert public_items()["total"] == 1


def test_expired_permission_is_validation_error_and_never_partially_committed(moderator):
    now = timezone.now()
    response = post(
        moderator,
        "admin/sources",
        source_payload(
            date_checked=(now - timedelta(days=2)).isoformat(),
            valid_until=(now - timedelta(days=1)).isoformat(),
        ),
    )
    assert response.status_code == 400, response.content
    assert moderator.get("/api/v1/admin/sources").json()["items"] == []


def test_maximum_deadline_filter_has_no_date_overflow(moderator):
    publish(moderator, create_source(moderator))
    assert public_items(deadline_before="9999-12-31")["total"] == 0


def test_fact_label_filters_ignore_case_but_never_interpolate_query_text(moderator):
    publish(moderator, create_source(moderator), countries=["PS"], disciplines=["Engineering"])
    assert public_items(country="ps", discipline="engineering", language="EN")["total"] == 1
    assert public_items(country="PS') OR TRUE --")["total"] == 0


@pytest.mark.parametrize("field", ["date_checked", "valid_until"])
def test_source_check_and_expiry_need_explicit_utc_offset(moderator, field):
    response = post(moderator, "admin/sources", source_payload(**{field: "2025-01-01T10:00:00"}))
    assert response.status_code == 400


def test_audit_outage_rolls_back_approval_and_visibility(moderator):
    candidate = create_candidate(moderator, create_source(moderator))
    with patch("catalog.services.record", side_effect=RuntimeError("Synthetic audit outage")):
        response = moderate(moderator, candidate)
    assert response.status_code == 503, response.content
    assert response.json()["code"] == "AUDIT_UNAVAILABLE"
    assert public_items()["total"] == 0
    assert not ModerationEvent.objects.filter(version_id=candidate["latest"]["id"]).exists()
    assert Scholarship.objects.get(pk=candidate["id"]).visibility == "DRAFT"


def test_public_catalog_rate_limit_is_bounded_without_storing_query_text(settings):
    settings.CATALOG_PUBLIC_RATE_LIMIT = 1
    client = APIClient()
    assert client.get("/api/v1/scholarships", {"q": "synthetic-private-query"}).status_code == 200
    response = client.get("/api/v1/scholarships")
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"
    assert not CatalogAudit.objects.exists()
