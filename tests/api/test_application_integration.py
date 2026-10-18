"""Cross-module submission evidence, file protection and legal-review isolation."""

import io
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from applications import services as tracker
from applications.models import Application, SubmissionArtifact
from applications.rounds import round_options
from catalog.models import ScholarshipVersion
from credits import services as credits
from django.db import DatabaseError, transaction
from django.utils import timezone
from documents import services as documents
from documents.models import DocumentVersion, SubmissionSnapshot
from identity.models import Account, IdentitySession
from identity.security import IdentityError, digest
from PIL import Image
from privacy.models import (
    DeletionRequest,
    FilePurgeTask,
    LegalEnvelope,
    PrivateAsset,
    RetentionPolicy,
)
from privacy.services import queue_expired_deletion
from private_files import scanner
from private_files import services as files
from private_files.models import StorageLock, StoredFile
from test_catalog import create_source, publish
from test_catalog import signed_client as catalog_client

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def phase12_settings(settings, tmp_path):
    settings.LOCAL = True
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    settings.PRIVATE_FILES_ROOT = str(tmp_path / "private")
    settings.PRIVATE_FILES_STORAGE_APPROVED = True
    credits.initialize_policy()
    StorageLock.objects.get_or_create(pk=1)


def student():
    user = Account.objects.create_user(
        f"tracker-{uuid.uuid4()}@example.invalid",
        "Synthetic-tracker-passphrase-529!",
        birth_date=date(2000, 1, 1),
        locale="en",
        state="ACTIVE",
        email_verified_at=timezone.now(),
    )
    proof = IdentitySession.objects.create(
        account=user,
        epoch=user.session_epoch,
        digest=digest(str(uuid.uuid4())),
        expires_at=timezone.now() + timedelta(days=1),
    )
    return user, proof


def scholarship():
    moderator, _ = catalog_client()
    source = create_source(moderator)
    value = publish(
        moderator,
        source,
        required_documents=["Reviewed synthetic CV requirement"],
        rounds=[
            {"kind": "UNKNOWN", "label": "Reviewed round A"},
            {"kind": "UNKNOWN", "label": "Reviewed round B"},
        ],
    )
    return ScholarshipVersion.objects.get(scholarship_id=value["id"], version=1)


def application(user, proof, version, index=0):
    key = round_options(version.rounds)[index]["round_key"]
    return tracker.create_application(user, proof, version.scholarship_id, key)


def change(user, proof, value, target, confirmation=False):
    return tracker.transition(
        user,
        proof,
        value.pk,
        {
            "to_state": target,
            "observed_at": timezone.now(),
            "evidence": "Synthetic student report; no external portal was contacted.",
            "confirm_external_submission": confirmation,
        },
        value.revision,
    )


def approved_document(user, proof):
    document = documents.create_document(
        user,
        proof,
        {"kind": "CV", "title": "Synthetic CV", "language": "en", "content": "Saved facts"},
    )
    documents.approve_version(
        user, proof, document.pk, document.current_id, document.current.content_hash, True
    )
    return document


def select(user, proof, value, *, version=None, asset=None):
    return tracker.select_artifact(
        user,
        proof,
        value.pk,
        tracker.requirements_data(value)[0]["key"],
        {
            "version_id": version.pk if version else None,
            "asset_id": asset.pk if asset else None,
            "content_hash": version.content_hash if version else asset.object_version,
        },
        value.revision,
    )


def upload(user):
    data = io.BytesIO()
    Image.new("RGB", (3, 3), "blue").save(data, format="PNG")
    clean = scanner.CleanScan("ClamAV synthetic-test", "12345", timezone.now())
    with (
        patch("private_files.scanner.health", return_value=clean),
        patch("private_files.scanner.scan", return_value=clean),
    ):
        return files.store_bytes(
            user.pk, "synthetic.png", "image/png", data.getvalue(), str(uuid.uuid4())
        )


def submitted_upload():
    user, proof = student()
    value = application(user, proof, scholarship())
    asset = upload(user)
    value = select(user, proof, value, asset=asset)
    value = change(user, proof, value, "READY")
    value = change(user, proof, value, "SUBMITTED", True)
    return user, proof, value, asset


def test_submitted_document_and_old_round_survive_master_edit_restore_and_new_round():
    user, proof = student()
    source = scholarship()
    value = application(user, proof, source)
    document = approved_document(user, proof)
    original = document.current
    value = select(user, proof, value, version=original)
    value = change(user, proof, value, "READY")
    value = change(user, proof, value, "SUBMITTED", True)
    saved = SubmissionArtifact.objects.get(application=value)
    frozen = SubmissionSnapshot.objects.get(application_ref=value.pk)
    assert saved.version_id == frozen.version_id == original.pk
    assert saved.content_hash == frozen.content_hash == original.content_hash
    document = documents.save_version(
        user,
        proof,
        document.pk,
        {"title": "Edited master", "language": "en", "content": "Changed facts"},
        document.revision,
    )
    documents.restore_version(user, proof, document.pk, original.pk, document.revision)
    saved.refresh_from_db()
    assert saved.version.content == "Saved facts" and saved.content_hash == original.content_hash
    assert DocumentVersion.objects.filter(document=document).count() == 3
    with pytest.raises(IdentityError):
        select(user, proof, value, version=original)
    second_round = application(user, proof, source, 1)
    assert second_round.pk != value.pk and second_round.state == "PREPARING"
    value.refresh_from_db()
    assert value.state == "SUBMITTED" and value.submitted_sequence == saved.event.sequence
    assert Application.objects.filter(owner=user).count() == 2


def test_submitted_upload_cannot_be_deleted_by_owner_or_direct_state_mutation():
    user, _, value, asset = submitted_upload()
    with pytest.raises(IdentityError) as denied:
        files.delete_owned(user.pk, asset.pk)
    assert denied.value.code == "FILE_FROZEN"
    with pytest.raises(DatabaseError), transaction.atomic():
        PrivateAsset.objects.filter(pk=asset.pk).update(state="PURGE_PENDING")
    assert files.read_owned_bytes(user.pk, asset.pk)
    assert SubmissionArtifact.objects.get(application=value).content_hash == asset.object_version


def test_legal_review_request_is_owned_and_does_not_claim_erasure_or_unfreeze():
    user, proof, value, asset = submitted_upload()
    artifact = SubmissionArtifact.objects.get(application=value)
    request = tracker.request_artifact_deletion(
        user, proof, value.pk, artifact.pk, "Synthetic authorized deletion review request"
    )
    assert request.state == "PENDING_LEGAL_REVIEW"
    stranger, foreign_proof = student()
    with pytest.raises(IdentityError):
        tracker.request_artifact_deletion(stranger, foreign_proof, value.pk, artifact.pk, "Foreign")
    with pytest.raises(IdentityError):
        tracker.erase_submitted_artifact(request.pk)
    with pytest.raises(IdentityError):
        files.delete_owned(user.pk, asset.pk)
    asset.refresh_from_db()
    assert asset.state == "ACCEPTED" and SubmissionArtifact.objects.filter(pk=artifact.pk).exists()


def test_real_application_reference_cannot_fabricate_unsubmitted_document_snapshot():
    user, proof = student()
    value = application(user, proof, scholarship())
    document = approved_document(user, proof)
    with pytest.raises(DatabaseError), transaction.atomic():
        documents.freeze_approved_version(
            user,
            proof,
            document.pk,
            document.current_id,
            trusted_application_id=value.pk,
        )
    assert not SubmissionSnapshot.objects.filter(application_ref=value.pk).exists()


def test_canonical_approved_expired_account_purge_is_not_blocked_by_submission_freeze():
    user, _, value, asset = submitted_upload()
    envelope = LegalEnvelope.objects.create(
        approved=True, min_days=1, max_days=60, evidence_ref=uuid.uuid4()
    )
    policy = RetentionPolicy.objects.create(version=2, recovery_days=1, legal_envelope=envelope)
    now = timezone.now()
    deletion = DeletionRequest.objects.create(
        account=user,
        policy=policy,
        recovery_days=1,
        confirmed_at=now - timedelta(days=2),
        restore_until=now - timedelta(days=1),
    )
    user.state = "DELETION_PENDING"
    user.save(update_fields=["state"])
    assert queue_expired_deletion(user.pk) == 1
    deletion.refresh_from_db()
    asset.refresh_from_db()
    assert deletion.state == "PURGING" and asset.state == "PURGE_PENDING"
    task = FilePurgeTask.objects.get(asset=asset)
    assert task.object_key == StoredFile.objects.get(pk=asset.pk).storage_token
    assert SubmissionArtifact.objects.filter(application=value).exists()
    # This is approved purge planning, not a fabricated physical erasure receipt.
    assert task.state == "BLOCKED_STORAGE"
    with pytest.raises(IdentityError):
        files.read_owned_bytes(user.pk, asset.pk)
