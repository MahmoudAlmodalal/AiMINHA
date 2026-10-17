"""Fixed local fixtures exercise real persistence/accounting, never private AI."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from credits import services as credits
from credits.models import LedgerEntry, Operation, SavedOutput, Wallet
from django.db import DatabaseError, close_old_connections, transaction
from django.utils import timezone
from documents import generation
from documents.models import Document, DocumentApproval, DocumentVersion, SyntheticDocumentJob
from identity.models import Account
from identity.security import IdentityError

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def setup_local(settings):
    settings.LOCAL = True
    credits.initialize_policy()


def student(**changes):
    values = {
        "email": f"document-{uuid.uuid4()}@example.invalid",
        "birth_date": date(2000, 1, 1),
        "state": "ACTIVE",
        "email_verified_at": timezone.now(),
    }
    user = Account.objects.create(**(values | changes))
    if user.role == "STUDENT" and user.email_verified_at and user.state == "ACTIVE":
        credits.grant_signup(user.pk)
    return user


class CountingAdapter(generation.LocalDocumentAdapter):
    def __init__(self):
        self.calls = 0

    def generate(self, kind, language, evidence):
        self.calls += 1
        return super().generate(kind, language, evidence)


@pytest.mark.parametrize("kind", ["CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"])
@pytest.mark.parametrize("language", ["ar", "en"])
def test_valid_synthetic_document_is_persisted_before_once_only_debit(kind, language):
    user = student()
    key = str(uuid.uuid4())
    job = generation.prepare_synthetic(user.pk, kind, language, key)
    assert not Document.objects.exists() and not SavedOutput.objects.exists()
    assert Wallet.objects.get(owner=user).reserved_balance == 6
    adapter = CountingAdapter()
    original_settle = credits.settle

    def settle_after_saved(*args, **kwargs):
        saved = SyntheticDocumentJob.objects.select_related("version").get(pk=job.pk)
        assert saved.version is not None
        assert saved.version.provenance == "SYNTHETIC_LOCAL"
        assert saved.version.owner_id == user.pk
        assert saved.version.content == "\n".join(generation.EVIDENCE[language])
        assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()
        return original_settle(*args, **kwargs)

    with patch.object(credits, "settle", side_effect=settle_after_saved):
        saved = generation.complete_synthetic(user.pk, job.pk, adapter)
    assert saved.version.language == language and saved.version.document.kind == kind
    assert not DocumentApproval.objects.exists()  # Technical validation is not student approval.
    assert generation.prepare_synthetic(user.pk, kind, language, key).pk == job.pk
    assert generation.complete_synthetic(user.pk, job.pk, adapter).version_id == saved.version_id
    assert adapter.calls == 1
    assert DocumentVersion.objects.count() == 1
    assert LedgerEntry.objects.get(owner=user, kind="DEBIT").amount == -6
    wallet = Wallet.objects.get(owner=user)
    assert (wallet.posted_balance, wallet.reserved_balance) == (24, 0)


def test_extraction_proposal_is_saved_before_charge_and_never_trusted_as_profile():
    user = student()
    job = generation.prepare_synthetic(user.pk, "CV_EXTRACTION", "en", str(uuid.uuid4()))
    saved = generation.complete_synthetic(user.pk, job.pk)
    assert saved.version_id is None and saved.proposal == generation.extraction_payload("en")
    assert saved.proposal["trusted"] is False
    assert all(item["review_required"] for item in saved.proposal["facts"])
    assert not Document.objects.exists()
    assert LedgerEntry.objects.get(owner=user, kind="DEBIT").amount == -4
    assert generation.complete_synthetic(user.pk, job.pk).proposal == saved.proposal
    assert LedgerEntry.objects.filter(owner=user, kind="DEBIT").count() == 1


@pytest.mark.parametrize("field", ["kind", "language"])
def test_reused_key_cannot_change_captured_manifest(field):
    user, key = student(), str(uuid.uuid4())
    generation.prepare_synthetic(user.pk, "CV", "en", key)
    changed = {"kind": "CV", "language": "en"} | {field: "ESSAY" if field == "kind" else "ar"}
    with pytest.raises(IdentityError, match="Idempotency"):
        generation.prepare_synthetic(user.pk, key=key, **changed)
    assert Operation.objects.count() == 1


@pytest.mark.parametrize("kind", ["CV", "CV_EXTRACTION"])
def test_fake_provider_success_with_unsupported_credentials_never_saves_or_charges(kind):
    class Liar:
        def generate(self, requested_kind, language, evidence):
            return {
                "kind": requested_kind,
                "language": language,
                "title": "Synthetic document",
                "content": "GPA 4.0, doctorate, invented award",
                "claims": ["GPA 4.0, doctorate, invented award"],
                "success": True,
            }

    user = student()
    job = generation.prepare_synthetic(user.pk, kind, "en", str(uuid.uuid4()))
    with pytest.raises(IdentityError) as error:
        generation.complete_synthetic(user.pk, job.pk, Liar())
    assert error.value.code == "DOCUMENT_OUTPUT_INVALID"
    assert Operation.objects.get(pk=job.operation_id).state == "RELEASED"
    assert not DocumentVersion.objects.exists() and not SavedOutput.objects.exists()
    assert not LedgerEntry.objects.filter(kind="DEBIT").exists()
    assert Wallet.objects.get(owner=user).reserved_balance == 0


def test_known_failure_releases_once_but_unknown_outcome_retains_hold():
    class Failure:
        def __init__(self, error):
            self.error = error

        def generate(self, kind, language, evidence):
            raise self.error

    for error, state, reserved in (
        (generation.SyntheticProviderFailure(), "RELEASED", 0),
        (TimeoutError(), "RECONCILING", 6),
    ):
        user = student()
        job = generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
        with pytest.raises(IdentityError):
            generation.complete_synthetic(user.pk, job.pk, Failure(error))
        assert Operation.objects.get(pk=job.operation_id).state == state
        assert Wallet.objects.get(owner=user).reserved_balance == reserved
        assert not LedgerEntry.objects.filter(owner=user, kind="DEBIT").exists()


def test_save_or_settle_crash_rolls_back_artifact_and_keeps_hold_for_reconciliation():
    user = student()
    job = generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
    with patch.object(credits, "settle", side_effect=RuntimeError("synthetic save fault")):
        with pytest.raises(RuntimeError):
            generation.complete_synthetic(user.pk, job.pk)
    job.refresh_from_db()
    assert job.version_id is None and not DocumentVersion.objects.exists()
    assert (
        not SavedOutput.objects.exists() and not LedgerEntry.objects.filter(kind="DEBIT").exists()
    )
    assert Operation.objects.get(pk=job.operation_id).state == "RECONCILING"
    assert Wallet.objects.get(owner=user).reserved_balance == 6


def test_local_proof_cannot_be_enabled_for_nonlocal_private_processing(settings):
    user = student()
    settings.LOCAL = False
    with pytest.raises(IdentityError):
        generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
    assert not Operation.objects.exists()


def test_cross_owner_and_staff_cannot_complete_another_students_job():
    user, other, admin = student(), student(), student(role="ADMIN")
    job = generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
    adapter = CountingAdapter()
    for actor in (other, admin):
        with pytest.raises(IdentityError):
            generation.complete_synthetic(actor.pk, job.pk, adapter)
    assert adapter.calls == 0 and not SavedOutput.objects.exists()


def test_sql_rejects_settlement_without_persisted_document_witness():
    user = student()
    job = generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
    token = credits.claim(user.pk, job.operation_id)
    operation = Operation.objects.get(pk=job.operation_id)
    with pytest.raises(DatabaseError), transaction.atomic():
        credits.settle(
            user.pk,
            operation.pk,
            token,
            {"fixture_id": str(operation.fixture_id), "result": "SYNTHETIC_OK"},
        )
    assert (
        not SavedOutput.objects.exists() and not LedgerEntry.objects.filter(kind="DEBIT").exists()
    )


def test_completed_job_evidence_cannot_be_replaced_or_removed_directly():
    user = student()
    job = generation.prepare_synthetic(user.pk, "CV", "en", str(uuid.uuid4()))
    generation.complete_synthetic(user.pk, job.pk)
    for change in ({"version_id": None}, {"language": "ar"}, {"proposal": {"trusted": True}}):
        with pytest.raises(DatabaseError), transaction.atomic():
            SyntheticDocumentJob.objects.filter(pk=job.pk).update(**change)
    with pytest.raises(DatabaseError), transaction.atomic():
        SyntheticDocumentJob.objects.filter(pk=job.pk).delete()


def test_concurrent_document_admission_keeps_one_manifest_and_one_reservation():
    user, key = student(), str(uuid.uuid4())
    barrier = Barrier(2)

    def admit():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return generation.prepare_synthetic(user.pk, "CV", "en", key).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: admit(), range(2)))
    assert results[0] == results[1]
    assert SyntheticDocumentJob.objects.count() == Operation.objects.count() == 1
    assert Wallet.objects.get(owner=user).reserved_balance == 6
