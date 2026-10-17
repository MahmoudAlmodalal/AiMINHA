"""Owned manual history, closed private AI and exact immutable review evidence."""

import uuid
from datetime import date

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone
from documents import services
from documents.models import Document, DocumentApproval, DocumentVersion, SubmissionSnapshot
from identity.models import Account, CommandReceipt, IdentitySession
from identity.security import digest
from privacy.models import PrivacyAudit, PrivateAsset
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-document-passphrase-529!"  # noqa: S105 -- synthetic fixture.


@pytest.fixture(autouse=True)
def document_settings(settings):
    settings.LOCAL = True
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]


def csrf(client):
    return client.get("/api/v1/session/csrf").json()["csrf_token"]


def mutate(client, path, data, *, revision=None, key=None):
    headers = {"HTTP_X_CSRFTOKEN": csrf(client), "HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4())}
    if revision is not None:
        headers["HTTP_IF_MATCH"] = f'"{revision}"'
    return client.post("/api/v1/" + path, data, format="json", **headers)


def signed_client(role="STUDENT"):
    user = Account.objects.create_user(
        f"document-{uuid.uuid4()}@example.invalid",
        PASSWORD,
        birth_date=date(2000, 1, 1),
        locale="en",
        state="ACTIVE",
        email_verified_at=timezone.now(),
        role=role,
    )
    client = APIClient(enforce_csrf_checks=True)
    response = mutate(client, "session/login", {"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.content
    return client, user


def body(**changes):
    return {
        "kind": "CV",
        "title": "Synthetic CV",
        "language": "en",
        "content": "Synthetic student\nSelf-confirmed engineering interest.",
    } | changes


def create(client, **changes):
    response = mutate(client, "documents", body(**changes))
    assert response.status_code == 201, response.content
    return response.json()


@pytest.mark.parametrize("kind", ["CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"])
@pytest.mark.parametrize("language", ["ar", "en"])
def test_four_manual_document_types_and_independent_language_are_free(kind, language):
    from credits.models import Operation

    client, _ = signed_client()
    before = Operation.objects.count()
    value = create(
        client,
        kind=kind,
        language=language,
        content="محتوى اصطناعي" if language == "ar" else "Synthetic text",
    )
    assert value["kind"] == kind and value["current"]["language"] == language
    assert not value["current"]["approved"] and value["revision"] == 1
    assert value["current"]["provenance"] == "MANUAL"
    assert Operation.objects.count() == before
    assert client.get("/api/v1/documents").json()["items"] == [value]


def test_version_cas_compare_and_restore_preserve_exact_approved_history():
    client, user = signed_client()
    first = create(client)
    base = "documents/" + first["id"]
    source = first["current"]
    approved = mutate(
        client,
        base + "/approvals",
        {
            "version_id": source["id"],
            "content_hash": source["content_hash"],
            "confirm": True,
        },
    )
    assert approved.status_code == 200 and approved.json()["approved"]
    updated = mutate(
        client,
        base + "/versions",
        {
            "title": "Renamed variant",
            "language": "ar",
            "content": "تعديل يدوي اصطناعي",
        },
        revision=1,
    )
    assert updated.status_code == 200, updated.content
    assert updated.json()["revision"] == 2 and not updated.json()["current"]["approved"]
    stale = mutate(
        client,
        base + "/versions",
        {
            "title": "Stale",
            "language": "en",
            "content": "Must not overwrite",
        },
        revision=1,
    )
    assert stale.status_code == 412
    restored = mutate(client, base + "/restore", {"version_id": source["id"]}, revision=2)
    assert restored.status_code == 200, restored.content
    assert restored.json()["revision"] == 3
    assert restored.json()["current"]["restored_from_id"] == source["id"]
    assert restored.json()["current"]["content_hash"] == source["content_hash"]
    assert not restored.json()["current"]["approved"]
    history = client.get("/api/v1/" + base + "/versions").json()["items"]
    assert [row["number"] for row in history] == [1, 2, 3]
    assert history[0]["approved"]
    compare = client.get(
        "/api/v1/" + base + "/compare", {"left": source["id"], "right": history[1]["id"]}
    )
    assert compare.status_code == 200
    assert compare.json()["left"]["content"] == source["content"]
    assert DocumentVersion.objects.filter(owner=user).count() == 3


def test_script_and_markup_are_plain_text_in_sanitized_preview():
    client, _ = signed_client()
    value = create(
        client, title='<img src=x onerror="alert(1)">', content='<script>alert("private")</script>&'
    )
    preview = value["current"]["preview_html"]
    assert "<script>" not in preview and "<img " not in preview
    assert "&lt;script&gt;" in preview and "&quot;" in preview


@pytest.mark.parametrize(
    "invalid",
    [
        {"owner": str(uuid.uuid4())},
        {"kind": "TRANSCRIPT"},
        {"language": "fr"},
        {"content": "x" * 40001},
        {"content": "bad\u0001text"},
        {"title": ""},
    ],
)
def test_strict_content_types_limits_and_server_owner(invalid):
    client, _ = signed_client()
    response = mutate(client, "documents", body(**invalid))
    assert response.status_code == 400
    assert not Document.objects.exists()


def test_foreign_and_admin_library_content_history_mutation_denied_and_audited():
    owner, user = signed_client()
    first = create(owner)
    base = "documents/" + first["id"]
    for role in ("STUDENT", "ADMIN"):
        client, actor = signed_client(role)
        if role == "ADMIN":
            assert client.get("/api/v1/documents").status_code == 403
        else:
            assert client.get("/api/v1/documents").json()["items"] == []
        for suffix in ("", "/versions"):
            assert client.get("/api/v1/" + base + suffix).status_code == 403
        assert (
            mutate(
                client, base + "/restore", {"version_id": first["current"]["id"]}, revision=1
            ).status_code
            == 403
        )
        assert PrivacyAudit.objects.filter(actor_id=actor.pk, outcome="DENY").exists()
    assert Document.objects.get(owner=user).revision == 1


def test_exact_owner_hash_approval_cannot_be_forged():
    client, _ = signed_client()
    value = create(client)
    for changes in (
        {"confirm": False},
        {"content_hash": "a" * 64},
        {"version_id": str(uuid.uuid4())},
    ):
        data = {
            "version_id": value["current"]["id"],
            "content_hash": value["current"]["content_hash"],
            "confirm": True,
        } | changes
        assert mutate(client, f"documents/{value['id']}/approvals", data).status_code in (
            400,
            403,
            409,
        )
    assert not DocumentApproval.objects.exists()


def test_private_ai_consent_then_owned_source_then_unavailable_without_credit_or_provider():
    from credits.models import Operation

    client, user = signed_client()
    before = Operation.objects.count()
    for consent, expected in ((False, 403), (True, 503)):
        response = mutate(client, "documents/generate", body(consent=consent))
        assert response.status_code == expected
    asset = PrivateAsset.objects.create(owner=user, object_version="synthetic-unaccepted")
    assert (
        mutate(
            client, "documents/extract", {"asset_id": str(asset.pk), "consent": False}
        ).status_code
        == 403
    )
    assert (
        mutate(
            client, "documents/extract", {"asset_id": str(uuid.uuid4()), "consent": True}
        ).status_code
        == 403
    )
    # Current projection cannot authorize private AI even when metadata is owned.
    assert (
        mutate(
            client, "documents/extract", {"asset_id": str(asset.pk), "consent": True}
        ).status_code
        == 503
    )
    assert Operation.objects.count() == before and not Document.objects.exists()
    capabilities = client.get("/api/v1/documents/capabilities").json()
    assert capabilities["manual_editing"] and not capabilities["private_ai"]


def test_csrf_required_and_idempotency_keeps_only_opaque_identity():
    client, _ = signed_client()
    assert client.post("/api/v1/documents", body(), format="json").status_code == 403
    key = str(uuid.uuid4())
    first = mutate(client, "documents", body(), key=key)
    second = mutate(client, "documents", body(), key=key)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json() and Document.objects.count() == 1
    assert mutate(client, "documents", body(content="Changed"), key=key).status_code == 409
    receipt = CommandReceipt.objects.filter(response__document_id=first.json()["id"]).first()
    assert receipt.response == {"document_id": first.json()["id"]}


def test_immutable_sql_versions_owner_head_and_frozen_snapshot():
    client, user = signed_client()
    value = create(client)
    version = DocumentVersion.objects.get(pk=value["current"]["id"])
    proof = IdentitySession.objects.get(digest=digest(client.session.session_key))
    services.approve_version(
        user, proof, version.document_id, version.pk, version.content_hash, True
    )
    snapshot = services.freeze_approved_version(
        user, proof, version.document_id, version.pk, trusted_application_id=uuid.uuid4()
    )
    for model, pk, changed in (
        (DocumentVersion, version.pk, {"content": "Invented GPA 4.0"}),
        (Document, version.document_id, {"owner_id": uuid.uuid4()}),
        (SubmissionSnapshot, snapshot.pk, {"content_hash": "a" * 64}),
        (
            DocumentApproval,
            DocumentApproval.objects.get(version=version).pk,
            {"content_hash": "b" * 64},
        ),
    ):
        with pytest.raises(DatabaseError), transaction.atomic():
            model.objects.filter(pk=pk).update(**changed)
    with pytest.raises(DatabaseError), transaction.atomic():
        DocumentVersion.objects.create(
            document_id=version.document_id,
            owner=user,
            number=2,
            title=version.title,
            language=version.language,
            content="Fake",
            content_hash="a" * 64,
        )
    assert snapshot.content_hash == version.content_hash
    restored = services.restore_version(user, proof, version.document_id, version.pk, 1)
    snapshot.refresh_from_db()
    assert restored.current_id != version.pk and snapshot.version_id == version.pk
