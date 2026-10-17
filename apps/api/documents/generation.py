"""Server-only local fixtures prove the document/accounting boundary.

There is deliberately no client route to this module. It cannot accept a CV,
profile, prompt or caller-provided evidence. Real student processing remains
closed by the private AI gateway. A synthetic artifact is saved before the
existing local credit kernel records its once-only synthetic debit.
"""

from typing import Any, Protocol

from credits import services as credits
from credits.models import Operation
from django.db import transaction
from identity.security import IdentityError, audit, digest

from documents import services
from documents.models import SyntheticDocumentJob
from documents.validation import validate_grounded_output

KINDS = {"CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY", "CV_EXTRACTION"}
EVIDENCE = {
    "en": ["Synthetic Student", "Synthetic training course"],
    "ar": ["طالب اصطناعي", "دورة تدريبية اصطناعية"],
}


class SyntheticProviderFailure(Exception):
    """The synchronous local fixture proves that no output was produced."""


class SyntheticAdapter(Protocol):
    def generate(self, kind: str, language: str, evidence: tuple[str, ...]) -> object: ...


class LocalDocumentAdapter:
    def generate(self, kind: str, language: str, evidence: tuple[str, ...]) -> object:
        if kind == "CV_EXTRACTION":
            return extraction_payload(language)
        return {
            "kind": kind,
            "language": language,
            "title": "مستند اصطناعي" if language == "ar" else "Synthetic document",
            "content": "\n".join(evidence),
            "claims": list(evidence),
        }


def extraction_payload(language: str) -> dict[str, Any]:
    return {
        "language": language,
        "trusted": False,
        "facts": [
            {
                "field": "qualification",
                "value": EVIDENCE[language][1],
                "source": "SYNTHETIC_FIXTURE",
                "review_required": True,
            }
        ],
    }


@transaction.atomic
def prepare_synthetic(owner_id: Any, kind: str, language: str, key: str) -> SyntheticDocumentJob:
    credits.local_synthetic_only()
    user = credits.owner_lock(owner_id)
    if kind not in KINDS or language not in EVIDENCE:
        raise IdentityError("INVALID_DOCUMENT_REQUEST", 400, "Invalid document request")
    if not isinstance(key, str):
        raise IdentityError("INVALID_DOCUMENT_REQUEST", 400, "Invalid document request")
    manifest_hash = credits.payload_hash({"kind": kind, "language": language})
    previous = Operation.objects.filter(owner=user, key_digest=digest(key)).first()
    if previous is not None:
        job = SyntheticDocumentJob.objects.filter(operation=previous, owner=user).first()
        if job is None or job.request_hash != manifest_hash:
            raise IdentityError("IDEMPOTENCY_CONFLICT", 409, "Idempotency key already used")
        return job
    fixture = credits.create_synthetic_input(user.pk)
    operation = credits.reserve(
        user.pk, "CV_EXTRACTION" if kind == "CV_EXTRACTION" else "DOCUMENT_NEW", key, fixture
    )
    return SyntheticDocumentJob.objects.create(
        owner=user,
        operation=operation,
        kind=kind,
        language=language,
        request_hash=manifest_hash,
    )


def _locked(owner_id: Any, job_id: Any) -> tuple[Any, Any, SyntheticDocumentJob]:
    first = SyntheticDocumentJob.objects.filter(pk=job_id, owner_id=owner_id).first()
    if first is None:
        raise IdentityError("DOCUMENT_ACCESS_DENIED")
    user, operation = credits.lock_for_gateway(owner_id, first.operation_id)
    job = SyntheticDocumentJob.objects.select_for_update().get(pk=first.pk, owner=user)
    return user, operation, job


def complete_synthetic(
    owner_id: Any, job_id: Any, adapter: SyntheticAdapter | None = None
) -> SyntheticDocumentJob:
    credits.local_synthetic_only()
    with transaction.atomic():
        _, operation, job = _locked(owner_id, job_id)
        if operation.state == "SETTLED":
            return job
        token = credits.claim(owner_id, operation.pk)

    # Only local, server-authored synthetic evidence reaches this port. No network
    # I/O or provider request occurs under database locks or elsewhere here.
    try:
        raw = (adapter or LocalDocumentAdapter()).generate(
            job.kind, job.language, tuple(EVIDENCE[job.language])
        )
    except SyntheticProviderFailure:
        credits.fail(owner_id, operation.pk, token)
        raise IdentityError(
            "DOCUMENT_GENERATION_FAILED", 503, "Use manual document entry"
        ) from None
    except Exception:
        credits.reconcile_system(operation.pk)
        raise IdentityError(
            "DOCUMENT_OUTCOME_UNCERTAIN", 503, "Document generation needs reconciliation"
        ) from None

    try:
        with transaction.atomic():
            user, operation, job = _locked(owner_id, job_id)
            credits.fence(operation, token)
            if job.kind == "CV_EXTRACTION":
                expected = extraction_payload(job.language)
                if raw != expected:
                    raise IdentityError(
                        "DOCUMENT_OUTPUT_INVALID", 409, "Output could not be verified"
                    )
                job.proposal = expected
                job.save(update_fields=["proposal"])
            else:
                value = validate_grounded_output(raw, EVIDENCE[job.language])
                if value["kind"] != job.kind or value["language"] != job.language:
                    raise IdentityError(
                        "DOCUMENT_OUTPUT_INVALID", 409, "Output could not be verified"
                    )
                document = services.create_synthetic_document(user.pk, value)
                job.version = document.current
                job.save(update_fields=["version"])
            # The additional document SQL witness checks the persisted exact
            # artifact before the legacy synthetic output/debit is allowed.
            credits.settle(
                user.pk,
                operation.pk,
                token,
                {"fixture_id": str(operation.fixture_id), "result": "SYNTHETIC_OK"},
            )
            audit(user, "synthetic_document_saved", resource=job.pk, reason="LOCAL_FIXTURE_ONLY")
            return job
    except IdentityError as error:
        if error.code == "DOCUMENT_OUTPUT_INVALID":
            credits.fail(owner_id, operation.pk, token)
        else:
            credits.reconcile_system(operation.pk)
        raise
    except Exception:
        # A save/settle rollback never leaves an accepted document or a debit.
        # Retain the original hold for investigation rather than blind refund.
        credits.reconcile_system(operation.pk)
        raise
