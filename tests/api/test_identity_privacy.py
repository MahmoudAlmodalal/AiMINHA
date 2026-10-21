import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from identity import google
from identity.models import Account, AuthIdentity, Challenge, IdentitySession
from identity.security import IdentityError, PublicCatalogRead, adult, digest, require_admin
from identity.services import issue
from privacy.models import (
    ConsentRecord,
    DeletionRequest,
    Disclosure,
    FilePurgeTask,
    LegalEnvelope,
    PrivacyAudit,
    PrivateAsset,
    RetentionHead,
    RetentionPolicy,
    TicketAccess,
    TicketShare,
)
from privacy.services import has_consent, publish_retention, queue_expired_deletion, restore_account
from rest_framework.test import APIClient
from support.models import Ticket

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-only-passphrase-529!"  # noqa: S105 -- public synthetic test fixture.


@pytest.fixture(autouse=True)
def identity_settings(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]


@pytest.fixture
def client():
    return APIClient(enforce_csrf_checks=True)


def csrf(client):
    response = client.get("/api/v1/session/csrf")
    assert response.status_code == 200, response.content
    return response.json()["csrf_token"]


def post(client, path, data=None, key=None, **headers):
    token = csrf(client)
    return client.post(
        "/api/v1/" + path,
        data or {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
        **headers,
    )


def account(email="student@example.invalid", role="STUDENT", **values):
    return Account.objects.create_user(
        email,
        PASSWORD,
        birth_date=date(2000, 1, 1),
        locale="ar",
        state="ACTIVE",
        email_verified_at=timezone.now(),
        role=role,
        **values,
    )


def login(client, user):
    response = post(client, "session/login", {"email": user.email, "password": PASSWORD})
    assert response.status_code == 200, response.content
    return response


def proof(client):
    return IdentitySession.objects.get(digest=digest(client.session.session_key))


def email_token():
    return re.search(r"Verification code: (\S+)", mail.outbox[-1].body).group(1)


@pytest.fixture
def policy():
    envelope = LegalEnvelope.objects.create(
        approved=True, min_days=1, max_days=60, evidence_ref=uuid.uuid4()
    )
    policy = RetentionPolicy.objects.create(version=2, recovery_days=30, legal_envelope=envelope)
    RetentionHead.objects.update_or_create(pk=1, defaults={"policy": policy})
    return policy


def request_deletion(client):
    assert client.get("/api/v1/account/deletions/impact").status_code == 200
    reauth = post(client, "session/reauthentications", {"password": PASSWORD})
    assert reauth.status_code == 200
    return post(
        client,
        "account/deletions",
        {"confirm_impact": True, "reauthentication_token": reauth.json()["reauthentication_token"]},
    )


@pytest.mark.parametrize(
    ("dob", "today", "expected"),
    [
        (date(2008, 10, 16), date(2026, 10, 15), False),
        (date(2008, 10, 16), date(2026, 10, 16), True),
        (date(2008, 2, 29), date(2026, 2, 28), False),
        (date(2008, 2, 29), date(2026, 3, 1), True),
        (date(2004, 2, 29), date(2024, 2, 29), True),
        (date(2030, 1, 1), date(2026, 10, 16), False),
        (date(9999, 12, 31), date(2026, 10, 16), False),
    ],
)
def test_server_adult_boundary_and_conservative_leap_anniversary(dob, today, expected):
    assert adult(dob, today) is expected


def test_signup_verify_login_server_proof_no_response_secrets(client):
    body = {
        "email": "New@Example.invalid",
        "password": PASSWORD,
        "birth_date": "2000-02-29",
        "locale": "en",
    }
    response = post(client, "auth/registrations", body)
    assert response.status_code == 202
    assert set(response.json()) == {"accepted", "correlation_id"}
    user = Account.objects.get(email="new@example.invalid")
    assert user.state == "PENDING" and not user.email_verified_at
    assert PASSWORD not in user.password
    assert (
        post(client, "session/login", {"email": user.email, "password": PASSWORD}).status_code
        == 401
    )
    token = email_token()
    assert not Challenge.objects.filter(digest=token).exists()
    assert token not in response.content.decode()
    response = post(client, "auth/email-verifications", {"challenge_token": token})
    assert response.status_code == 200
    assert post(client, "auth/email-verifications", {"challenge_token": token}).status_code == 400
    response = login(client, user)
    assert set(response.json()) == {
        "actor_id",
        "verified_email",
        "adult_eligible",
        "roles",
        "expires_at",
    }
    assert response.json()["roles"] == ["STUDENT"]
    assert all(
        value not in response.content.decode()
        for value in [PASSWORD, token, user.password, user.email]
    )
    assert client.get("/api/v1/session").status_code == 200
    assert post(client, "session/logout").status_code == 204
    assert client.get("/api/v1/session").status_code == 401


def test_registration_duplicate_and_idempotency_do_not_create_identity_twice(client):
    body = {
        "email": "duplicate@example.invalid",
        "password": PASSWORD,
        "birth_date": "2000-01-01",
        "locale": "ar",
    }
    key = str(uuid.uuid4())
    assert post(client, "auth/registrations", body, key).status_code == 202
    assert post(client, "auth/registrations", body, key).status_code == 202
    assert len(mail.outbox) == 1
    assert (
        post(client, "auth/registrations", {**body, "email": body["email"].upper()}).status_code
        == 202
    )
    assert Account.objects.filter(email__iexact=body["email"]).count() == 1
    assert post(client, "auth/registrations", {**body, "locale": "en"}, key).status_code == 409


@pytest.mark.parametrize(
    "patch_data",
    [
        {"role": "ADMIN"},
        {"owner_id": str(uuid.uuid4())},
        {"email_verified": True},
        {"birth_date": "2010-01-01"},
        {"birth_date": "2000-02-30"},
    ],
)
def test_signup_rejects_privilege_injection_minors_and_invalid_dates(client, patch_data):
    body = {
        "email": "blocked@example.invalid",
        "password": PASSWORD,
        "birth_date": "2000-01-01",
        "locale": "ar",
    }
    assert post(client, "auth/registrations", {**body, **patch_data}).status_code == 400
    assert not Account.objects.exists()


def test_all_anonymous_unsafe_auth_calls_retain_csrf(client):
    for path in [
        "auth/registrations",
        "session/login",
        "auth/email-verifications",
        "account/restorations",
    ]:
        response = client.post("/api/v1/" + path, {}, format="json")
        assert response.status_code == 403 and response.json()["code"] == "CSRF_FAILED"


def test_expired_or_wrong_purpose_challenge_is_rejected(client):
    user = account()
    token = issue(user, "RESET_PASSWORD", lifetime=timedelta(seconds=-1))
    assert (
        post(
            client, "auth/password-resets", {"challenge_token": token, "password": PASSWORD}
        ).status_code
        == 400
    )
    token = issue(user, "RESTORE")
    assert post(client, "auth/email-verifications", {"challenge_token": token}).status_code == 400


def test_login_throttling_ignores_client_forwarded_ip(client, settings):
    settings.IDENTITY_RATE_LIMIT = 2
    for index in range(3):
        result = post(
            client,
            "session/login",
            {"email": "unknown@example.invalid", "password": PASSWORD},
            HTTP_X_FORWARDED_FOR=f"192.0.2.{index}",
        )
    assert result.status_code == 429


def test_session_rotation_expiry_revocation_and_reset(client):
    user = account()
    old_session = client.session.session_key
    login(client, user)
    assert client.session.session_key != old_session
    row = proof(client)
    IdentitySession.objects.filter(pk=row.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client.get("/api/v1/session").status_code == 401
    login(client, user)
    assert post(client, "auth/password-reset-requests", {"email": user.email}).status_code == 202
    response = post(
        client,
        "auth/password-resets",
        {"challenge_token": email_token(), "password": PASSWORD + "new"},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/session").status_code == 401
    assert (
        post(client, "session/login", {"email": user.email, "password": PASSWORD}).status_code
        == 401
    )


def test_public_catalog_read_permission_is_safe_method_only():
    permission = PublicCatalogRead()
    assert permission.has_permission(SimpleNamespace(method="GET"), None)
    assert not permission.has_permission(SimpleNamespace(method="POST"), None)


def test_ownership_and_admin_file_denials_are_persistently_audited(client):
    owner, stranger = account(), account("other@example.invalid")
    asset = PrivateAsset.objects.create(
        owner=owner, object_version="synthetic-v1", state="ACCEPTED"
    )
    login(client, stranger)
    assert client.get(f"/api/v1/files/{asset.pk}").status_code == 403
    assert client.get("/api/v1/files").json()["items"] == []
    assert PrivacyAudit.objects.filter(actor_id=stranger.pk, outcome="DENY").exists()
    admin = account("admin@example.invalid", role="ADMIN")
    login(client, admin)
    assert client.get("/api/v1/files").status_code == 403
    assert client.get(f"/api/v1/files/{asset.pk}").status_code == 403
    assert PrivacyAudit.objects.filter(actor_id=admin.pk, outcome="DENY").count() == 2
    login(client, owner)
    response = client.get(f"/api/v1/files/{asset.pk}")
    assert response.status_code == 200
    assert set(response.json()) == {"id", "state", "declared_size", "created_at"}


def test_support_requires_current_assignment_explicit_exact_share_and_mfa(client):
    owner = account()
    admin = account("support@example.invalid", role="ADMIN", admin_scopes=["SUPPORT"])
    asset = PrivateAsset.objects.create(
        owner=owner, object_version="synthetic-v1", state="ACCEPTED"
    )
    sibling = PrivateAsset.objects.create(
        owner=owner, object_version="synthetic-v2", state="ACCEPTED"
    )
    access = TicketAccess.objects.create(owner=owner, assigned_admin=admin)
    ticket = Ticket.objects.create(
        access=access,
        owner=owner,
        category="GENERAL",
        subject="Synthetic support ticket",
        assigned_admin=admin,
    )
    login(client, owner)
    response = post(client, f"tickets/{ticket.pk}/attachments", {"asset_id": str(asset.pk)})
    assert response.status_code == 201
    reader = APIClient(enforce_csrf_checks=True)
    login(reader, admin)
    list_path = f"/api/v1/admin/tickets/{ticket.pk}/attachments"
    assert reader.get(list_path).status_code == 403
    # Synthetic server MFA proof only; no API accepts a client-supplied MFA flag.
    IdentitySession.objects.filter(pk=proof(reader).pk).update(mfa_verified_at=timezone.now())
    listing = reader.get(list_path)
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    share_id = items[0]["id"]
    assert items[0]["display_name"] == "synthetic-v1"
    assert items[0]["state"] == "SHARED"
    path = f"/api/v1/tickets/{ticket.pk}/attachments/{share_id}"
    assert reader.get(path).status_code == 200
    assert reader.get(f"/api/v1/files/{sibling.pk}").status_code == 403
    Ticket.objects.filter(pk=ticket.pk).update(assigned_admin=None)
    TicketAccess.objects.filter(pk=ticket.pk).update(assigned_admin=None)
    assert reader.get(list_path).status_code == 403
    assert reader.get(path).status_code == 403
    Ticket.objects.filter(pk=ticket.pk).update(assigned_admin=admin)
    TicketAccess.objects.filter(pk=ticket.pk).update(assigned_admin=admin)
    response = client.delete(
        path, HTTP_X_CSRFTOKEN=csrf(client), HTTP_IF_MATCH=f'"share-{share_id}-1"'
    )
    assert response.status_code == 202
    after_listing = reader.get(list_path).json()["items"]
    assert after_listing[0]["state"] == "REVOKED"
    assert reader.get(path).status_code == 403


def test_share_cross_owner_reference_is_rejected_by_database():
    owner, other = account(), account("other@example.invalid")
    asset = PrivateAsset.objects.create(owner=other, object_version="v1")
    ticket = TicketAccess.objects.create(owner=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        TicketShare.objects.create(owner=owner, ticket=ticket, asset=asset)


def test_consent_is_separate_explicit_versioned_and_revocable(client):
    user = account()
    privacy = Disclosure.objects.create(
        purpose="PRIVACY", version=1, disclosure="Synthetic notice", available=True
    )
    ai = Disclosure.objects.create(
        purpose="PERSONAL_AI", version=1, disclosure="Synthetic AI notice", available=True
    )
    login(client, user)
    assert not has_consent(user, "PERSONAL_AI")
    etag = client.get("/api/v1/consents")["ETag"]
    assert (
        post(
            client,
            "consents",
            {"disclosure_id": str(privacy.pk), "decision": "GRANT"},
            HTTP_IF_MATCH=etag,
        ).status_code
        == 201
    )
    assert not has_consent(user, "PERSONAL_AI")
    assert (
        post(
            client,
            "consents",
            {"disclosure_id": str(ai.pk), "decision": "GRANT"},
            HTTP_IF_MATCH=etag,
        ).status_code
        == 412
    )
    etag = client.get("/api/v1/consents")["ETag"]
    response = post(
        client, "consents", {"disclosure_id": str(ai.pk), "decision": "GRANT"}, HTTP_IF_MATCH=etag
    )
    assert response.status_code == 201
    captured = response.json()["version"]
    assert has_consent(user, "PERSONAL_AI", captured)
    etag = client.get("/api/v1/consents")["ETag"]
    assert (
        post(
            client,
            "consents",
            {"disclosure_id": str(ai.pk), "decision": "REVOKE"},
            HTTP_IF_MATCH=etag,
        ).status_code
        == 201
    )
    assert not has_consent(user, "PERSONAL_AI", captured)
    Disclosure.objects.create(
        purpose="PERSONAL_AI", version=2, disclosure="New synthetic notice", available=True
    )
    assert (
        post(
            client,
            "consents",
            {"disclosure_id": str(ai.pk), "decision": "GRANT"},
            HTTP_IF_MATCH=client.get("/api/v1/consents")["ETag"],
        ).status_code
        == 409
    )
    assert ConsentRecord.objects.filter(account=user).count() == 3


def test_audit_consent_and_deletion_snapshots_are_database_immutable(policy):
    user = account()
    event = PrivacyAudit.objects.create(actor_id=user.pk, action="test", outcome="ALLOW")
    with pytest.raises(IntegrityError), transaction.atomic():
        PrivacyAudit.objects.filter(pk=event.pk).update(reason="changed")
    with pytest.raises(IntegrityError), transaction.atomic():
        RetentionPolicy.objects.filter(pk=policy.pk).update(recovery_days=1)
    disclosure = Disclosure.objects.create(
        purpose="PRIVACY", version=1, disclosure="Synthetic notice"
    )
    consent = ConsentRecord.objects.create(
        account=user, disclosure=disclosure, version=1, state="GRANTED"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ConsentRecord.objects.filter(pk=consent.pk).update(state="REVOKED")
    record = DeletionRequest.objects.create(
        account=user,
        policy=policy,
        recovery_days=30,
        confirmed_at=timezone.now(),
        restore_until=timezone.now() + timedelta(days=30),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        DeletionRequest.objects.filter(pk=record.pk).update(restore_until=timezone.now())


def test_delete_legal_gate_and_reauthentication_binding(client, policy):
    user = account()
    login(client, user)
    assert (
        post(
            client,
            "account/deletions",
            {"confirm_impact": True, "reauthentication_token": "x" * 40},
        ).status_code
        == 400
    )
    token = post(client, "session/reauthentications", {"password": PASSWORD}).json()[
        "reauthentication_token"
    ]
    second = APIClient(enforce_csrf_checks=True)
    login(second, user)
    assert (
        post(
            second, "account/deletions", {"confirm_impact": True, "reauthentication_token": token}
        ).status_code
        == 400
    )
    LegalEnvelope.objects.filter(pk=policy.legal_envelope_id).update(approved=False)
    assert request_deletion(client).status_code == 503
    user.refresh_from_db()
    assert user.state == "ACTIVE" and not DeletionRequest.objects.exists()


@pytest.mark.parametrize(
    "offset,expected",
    [(timedelta(microseconds=-1), 200), (timedelta(0), 403), (timedelta(microseconds=1), 403)],
)
def test_exact_30_day_utc_restore_boundary(client, policy, offset, expected):
    user = account()
    login(client, user)
    start = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
    with patch("django.utils.timezone.now", return_value=start):
        response = request_deletion(client)
    assert response.status_code == 201
    deletion = DeletionRequest.objects.get(account=user)
    assert deletion.restore_until == start + timedelta(days=30)
    assert client.get("/api/v1/session").status_code == 401
    with patch(
        "django.utils.timezone.now", return_value=deletion.restore_until - timedelta(minutes=1)
    ):
        assert post(client, "account/recovery-requests", {"email": user.email}).status_code == 202
        token = email_token()
    with patch("django.utils.timezone.now", return_value=deletion.restore_until + offset):
        result = post(client, "account/restorations", {"challenge_token": token})
    assert result.status_code == expected, result.content
    user.refresh_from_db()
    assert user.state == ("ACTIVE" if expected == 200 else "DELETION_PENDING")
    if expected == 200:
        assert post(client, "account/restorations", {"challenge_token": token}).status_code == 403
        assert client.get("/api/v1/session").status_code == 401


def test_retention_edits_are_prospective_and_admin_proof_bound(client, policy):
    first = account()
    login(client, first)
    assert request_deletion(client).status_code == 201
    deletion = DeletionRequest.objects.get(account=first)
    saved = deletion.restore_until
    admin = account("privacy-admin@example.invalid", role="ADMIN", admin_scopes=["PRIVACY"])
    admin_client = APIClient(enforce_csrf_checks=True)
    login(admin_client, admin)
    session = proof(admin_client)
    with pytest.raises(IdentityError):
        publish_retention(admin, session, 10, policy.legal_envelope, policy.version)
    session.mfa_verified_at = timezone.now()
    session.save(update_fields=["mfa_verified_at"])
    newer = publish_retention(admin, session, 10, policy.legal_envelope, policy.version)
    deletion.refresh_from_db()
    assert deletion.restore_until == saved and deletion.recovery_days == 30
    second = account("next@example.invalid")
    login(client, second)
    assert request_deletion(client).status_code == 201
    next_deletion = DeletionRequest.objects.get(account=second)
    assert next_deletion.policy == newer
    assert next_deletion.restore_until - next_deletion.confirmed_at == timedelta(days=10)
    with pytest.raises(IdentityError):
        require_admin(first, session)


def test_file_purge_queue_waits_for_cutoff_is_exact_and_idempotent(client, policy):
    user = account()
    asset = PrivateAsset.objects.create(
        owner=user, object_version="exact-synthetic-version", state="ACCEPTED"
    )
    login(client, user)
    assert request_deletion(client).status_code == 201
    deletion = DeletionRequest.objects.get(account=user)
    assert queue_expired_deletion(user.pk) == 0
    with patch("django.utils.timezone.now", return_value=deletion.restore_until):
        assert queue_expired_deletion(user.pk) == 1
        assert queue_expired_deletion(user.pk) == 0
    task = FilePurgeTask.objects.get(asset=asset)
    assert task.object_key == asset.object_key and task.object_version == asset.object_version
    assert task.state == "BLOCKED_STORAGE"
    with pytest.raises(IntegrityError), transaction.atomic():
        FilePurgeTask.objects.filter(pk=task.pk).update(object_version="changed-target")
    assert DeletionRequest.objects.get(pk=deletion.pk).state == "PURGING"
    assert not FilePurgeTask.objects.filter(state="PURGED").exists()


def test_audit_failure_prevents_success_and_returns_no_private_details(client):
    user = account()
    login(client, user)
    with patch(
        "privacy.models.PrivacyAudit.objects.create",
        side_effect=RuntimeError("secret-internal-marker"),
    ):
        response = client.get("/api/v1/files")
        assert response.status_code == 503
        assert "secret-internal-marker" not in response.content.decode()


def test_missing_google_configuration_fails_closed(client):
    with override_settings(GOOGLE_CLIENT_ID="", GOOGLE_CLIENT_SECRET="", GOOGLE_REDIRECT_URI=""):
        assert post(client, "auth/google/authorizations", {"intent": "SIGN_IN"}).status_code == 503
    assert not AuthIdentity.objects.exists()


@override_settings(
    GOOGLE_CLIENT_ID="synthetic-client",
    GOOGLE_CLIENT_SECRET="synthetic-only",  # noqa: S106 -- synthetic provider fixture, no live credential.
    GOOGLE_REDIRECT_URI="http://127.0.0.1:3000/ar/account",
)
def test_google_link_state_session_pkce_unique_subject_and_no_email_auto_merge(client):
    user = account()
    login(client, user)
    assert post(client, "auth/google/authorizations", {"intent": "LINK"}).status_code == 403
    post(client, "session/reauthentications", {"password": PASSWORD})
    response = post(client, "auth/google/authorizations", {"intent": "LINK"})
    assert response.status_code == 200
    parameters = parse_qs(urlparse(response.json()["authorization_url"]).query)
    assert parameters["code_challenge_method"] == ["S256"]
    state = parameters["state"][0]
    other = APIClient(enforce_csrf_checks=True)
    assert (
        post(other, "auth/google/callbacks", {"code": "synthetic", "state": state}).status_code
        == 400
    )
    with patch.object(google, "exchange", return_value={"sub": "synthetic-google-subject"}):
        assert (
            post(client, "auth/google/callbacks", {"code": "synthetic", "state": state}).status_code
            == 200
        )
        assert (
            post(client, "auth/google/callbacks", {"code": "synthetic", "state": state}).status_code
            == 400
        )
    assert AuthIdentity.objects.get(subject="synthetic-google-subject").account == user
    post(client, "session/logout")
    start = post(client, "auth/google/authorizations", {"intent": "SIGN_IN"})
    state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]
    with patch.object(
        google, "exchange", return_value={"sub": "unknown-subject", "email": user.email}
    ):
        assert (
            post(client, "auth/google/callbacks", {"code": "synthetic", "state": state}).status_code
            == 409
        )
    assert Account.objects.count() == 1 and AuthIdentity.objects.count() == 1


@override_settings(
    GOOGLE_CLIENT_ID="synthetic-client",
    GOOGLE_CLIENT_SECRET="synthetic-only",  # noqa: S106 -- synthetic provider fixture, no live credential.
    GOOGLE_REDIRECT_URI="http://127.0.0.1:3000/ar/account",
)
@pytest.mark.parametrize(
    "bad_claim", [{"nonce": "wrong"}, {"aud": "wrong"}, {"iss": "wrong"}, {"email_verified": False}]
)
def test_google_adapter_rejects_bad_verified_claims(bad_claim):
    claims = {
        "sub": "synthetic-subject",
        "aud": "synthetic-client",
        "iss": "accounts.google.com",
        "email_verified": True,
        "nonce": "synthetic-nonce",
        **bad_claim,
    }
    with patch.object(google.requests, "post") as token_exchange:
        token_exchange.return_value.json.return_value = {"id_token": "synthetic-token"}
        with patch.object(google.id_token, "verify_oauth2_token", return_value=claims):
            with pytest.raises(IdentityError, match="Google verification failed"):
                google.exchange("synthetic-code", "synthetic-verifier", "synthetic-nonce")


def test_audit_content_contains_metadata_only(client):
    user = account()
    login(client, user)
    post(client, "session/reauthentications", {"password": PASSWORD})
    payload = json.dumps(list(PrivacyAudit.objects.values()), default=str)
    assert all(
        value not in payload
        for value in [user.email, PASSWORD, user.password, str(user.birth_date)]
    )


def test_delete_revokes_ai_consent_without_regrant_on_restore(client, policy):
    user = account()
    disclosure = Disclosure.objects.create(
        purpose="PERSONAL_AI", version=1, disclosure="Synthetic AI notice", available=True
    )
    user.consent_version = 1
    user.save(update_fields=["consent_version"])
    ConsentRecord.objects.create(account=user, disclosure=disclosure, version=1, state="GRANTED")
    login(client, user)
    assert has_consent(user, "PERSONAL_AI", 1)
    assert request_deletion(client).status_code == 201
    deletion = DeletionRequest.objects.get(account=user)
    token = issue(user, "RESTORE", deletion=deletion.pk)
    restore_account(token, None)
    assert not has_consent(user, "PERSONAL_AI")
    assert not has_consent(user, "PERSONAL_AI", 1)


def test_changed_policy_requires_fresh_impact_review(client, policy):
    user = account()
    login(client, user)
    client.get("/api/v1/account/deletions/impact")
    token = post(client, "session/reauthentications", {"password": PASSWORD}).json()[
        "reauthentication_token"
    ]
    changed = RetentionPolicy.objects.create(
        version=3, recovery_days=10, legal_envelope=policy.legal_envelope
    )
    RetentionHead.objects.filter(pk=1).update(policy=changed)
    body = {"confirm_impact": True, "reauthentication_token": token}
    assert post(client, "account/deletions", body).status_code == 409
    assert not DeletionRequest.objects.exists()
    client.get("/api/v1/account/deletions/impact")
    assert post(client, "account/deletions", body).status_code == 201


def test_verification_resend_invalidates_prior_challenge(client):
    body = {
        "email": "resend@example.invalid",
        "password": PASSWORD,
        "birth_date": "2000-01-01",
        "locale": "en",
    }
    assert post(client, "auth/registrations", body).status_code == 202
    old = email_token()
    assert (
        post(client, "auth/email-verification-requests", {"email": body["email"]}).status_code
        == 202
    )
    current = email_token()
    assert current != old
    assert post(client, "auth/email-verifications", {"challenge_token": old}).status_code == 400
    assert post(client, "auth/email-verifications", {"challenge_token": current}).status_code == 200
