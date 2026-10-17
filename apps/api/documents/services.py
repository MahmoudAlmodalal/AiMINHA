import hashlib
import html
import json
import re
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, digest, require_student

from documents.models import (
    Document,
    DocumentApproval,
    DocumentExport,
    DocumentExportRequest,
    DocumentVersion,
    SubmissionSnapshot,
)
from documents.serializers import DocumentInputSerializer, VersionInputSerializer


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


def content_hash(kind: str, title: str, language: str, content: str) -> str:
    # PostgreSQL jsonb array text uses the same comma-space Unicode representation.
    body = json.dumps([kind, title, language, content], ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()


def owned(user: Account, document_id: UUID, *, lock: bool = False) -> Document:
    rows = Document.objects.select_for_update() if lock else Document.objects
    value = rows.filter(pk=document_id, owner=user).first()
    if value is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    return value


def version_owned(user: Account, document_id: UUID, version_id: UUID) -> DocumentVersion:
    value = DocumentVersion.objects.filter(
        pk=version_id, document_id=document_id, owner=user
    ).first()
    if value is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    return value


def version_data(value: DocumentVersion) -> dict[str, Any]:
    direction = "rtl" if value.language == "ar" else "ltr"
    return {
        "id": str(value.pk),
        "number": value.number,
        "title": value.title,
        "language": value.language,
        "content": value.content,
        "content_hash": value.content_hash,
        "preview_html": (
            f'<div lang="{value.language}" dir="{direction}"><h1>'
            f"{html.escape(value.title)}</h1><pre>{html.escape(value.content)}</pre></div>"
        ),
        "provenance": value.provenance,
        "restored_from_id": str(value.restored_from_id) if value.restored_from_id else None,
        "created_at": value.created_at,
        "approved": DocumentApproval.objects.filter(version=value).exists(),
    }


def document_data(value: Document) -> dict[str, Any]:
    return {
        "id": str(value.pk),
        "kind": value.kind,
        "revision": value.revision,
        "current": version_data(value.current),
    }


def validate_version(data: dict[str, Any], *, create: bool = False) -> dict[str, Any]:
    serializer = DocumentInputSerializer if create else VersionInputSerializer
    value = serializer(data=data)
    value.is_valid(raise_exception=True)
    return dict(value.validated_data)


def append_version(
    document: Document,
    data: dict[str, Any],
    *,
    provenance: str = "MANUAL",
    restored_from: DocumentVersion | None = None,
) -> DocumentVersion:
    value = DocumentVersion.objects.create(
        document=document,
        owner_id=document.owner_id,
        number=document.revision + 1,
        title=data["title"],
        language=data["language"],
        content=data["content"],
        content_hash=content_hash(document.kind, data["title"], data["language"], data["content"]),
        provenance=provenance,
        restored_from=restored_from,
    )
    document.current, document.revision = value, value.number
    document.save(update_fields=["current", "revision"])
    return value


@transaction.atomic
def create_document(
    user: Account,
    proof: IdentitySession,
    data: dict[str, Any],
    correlation: Any = None,
    *,
    provenance: str = "MANUAL",
) -> Document:
    user = student(user, proof)
    data = validate_version(data, create=True)
    if provenance not in {"MANUAL", "SYNTHETIC_LOCAL"}:
        raise IdentityError("DOCUMENT_OUTPUT_INVALID", 409, "Invalid document provenance")
    document = Document.objects.create(owner=user, kind=data["kind"])
    append_version(document, data, provenance=provenance)
    audit(user, "document_created", resource=document.pk, correlation=correlation)
    return document


@transaction.atomic
def create_synthetic_document(owner_id: UUID, data: dict[str, Any]) -> Document:
    """Internal local test artifact, never a session bypass for real documents."""
    if not settings.LOCAL:
        raise IdentityError("SYNTHETIC_EXECUTION_DISABLED", 503, "Local proof is unavailable")
    user = Account.objects.select_for_update().get(pk=owner_id)
    require_student(user)
    data = validate_version(data, create=True)
    document = Document.objects.create(owner=user, kind=data["kind"])
    append_version(document, data, provenance="SYNTHETIC_LOCAL")
    audit(user, "document_synthetic_saved", resource=document.pk)
    return document


def asset_is_frozen(asset_id: UUID) -> bool:
    return SubmissionSnapshot.objects.filter(version__documentexport__asset_id=asset_id).exists()


def asset_is_protected(asset_id: UUID) -> bool:
    """Retained export rows require their exact bytes until approved erasure exists."""
    return DocumentExport.objects.filter(asset_id=asset_id).exists()


@transaction.atomic
def read_document(
    user: Account, proof: IdentitySession, document_id: UUID, correlation: Any = None
) -> Document:
    user = student(user, proof)
    value = owned(user, document_id)
    audit(user, "document_read", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def list_documents(
    user: Account, proof: IdentitySession, correlation: Any = None
) -> list[Document]:
    user = student(user, proof)
    audit(user, "document_library_list", correlation=correlation)
    return list(Document.objects.filter(owner=user).select_related("current").order_by("pk")[:100])


def check_revision(document: Document, expected: int) -> None:
    if expected != document.revision:
        raise IdentityError("STALE_REVISION", 412, "Reload the current document before saving")


@transaction.atomic
def save_version(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    data: dict[str, Any],
    expected_revision: int,
    correlation: Any = None,
) -> Document:
    user = student(user, proof)
    document = owned(user, document_id, lock=True)
    check_revision(document, expected_revision)
    append_version(document, validate_version(data))
    audit(user, "document_version_saved", resource=document.current_id, correlation=correlation)
    return document


@transaction.atomic
def restore_version(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    version_id: UUID,
    expected_revision: int,
    correlation: Any = None,
) -> Document:
    user = student(user, proof)
    document = owned(user, document_id, lock=True)
    check_revision(document, expected_revision)
    source = version_owned(user, document_id, version_id)
    append_version(
        document,
        {"title": source.title, "language": source.language, "content": source.content},
        restored_from=source,
    )
    audit(user, "document_version_restored", resource=document.current_id, correlation=correlation)
    return document


@transaction.atomic
def list_versions(
    user: Account, proof: IdentitySession, document_id: UUID, correlation: Any = None
) -> list[DocumentVersion]:
    user = student(user, proof)
    owned(user, document_id)
    audit(user, "document_history_read", resource=document_id, correlation=correlation)
    return list(
        DocumentVersion.objects.filter(document_id=document_id, owner=user).order_by("number")
    )


@transaction.atomic
def approve_version(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    version_id: UUID,
    expected_hash: str,
    confirm: bool,
    correlation: Any = None,
) -> DocumentVersion:
    user = student(user, proof)
    owned(user, document_id, lock=True)
    value = version_owned(user, document_id, version_id)
    if confirm is not True or value.content_hash != expected_hash:
        raise IdentityError("DOCUMENT_APPROVAL_MISMATCH", 409, "Review the exact saved version")
    DocumentApproval.objects.get_or_create(
        version=value, defaults={"owner": user, "content_hash": value.content_hash}
    )
    audit(user, "document_version_approved", resource=value.pk, correlation=correlation)
    return value


def export_data(value: DocumentExport) -> dict[str, Any]:
    return {
        "id": str(value.pk),
        "version_id": str(value.version_id),
        "format": value.format,
        "asset_id": str(value.asset_id),
        "content_hash": value.content_hash,
        "created_at": value.created_at,
    }


@transaction.atomic
def approved_version(
    user: Account, proof: IdentitySession, document_id: UUID, version_id: UUID
) -> DocumentVersion:
    user = student(user, proof)
    owned(user, document_id)
    value = version_owned(user, document_id, version_id)
    if not DocumentApproval.objects.filter(
        version=value, owner=user, content_hash=value.content_hash
    ).exists():
        raise IdentityError("DOCUMENT_APPROVAL_REQUIRED", 409, "Approve the saved version first")
    return value


def export_version(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    version_id: UUID,
    output_format: str,
    correlation: Any = None,
) -> DocumentExport:
    """No credit admission occurs here. Rendering/storage failure leaves history intact."""
    from private_files.services import store_bytes

    from documents.rendering import render

    value = approved_version(user, proof, document_id, version_id)
    if output_format not in {"PDF", "DOCX"}:
        raise IdentityError("INVALID_EXPORT_FORMAT", 400, "Choose PDF or DOCX")
    previous = DocumentExport.objects.filter(version=value, format=output_format).first()
    if previous is not None:
        with transaction.atomic():
            student(user, proof)
            audit(user, "document_export_read", resource=previous.pk, correlation=correlation)
        return previous
    # External scanner/storage I/O runs after the immutable approved snapshot is read,
    # outside account/document transactions. Store identity survives a response retry.
    data, mime = render(value, output_format)
    asset = store_bytes(
        user.pk,
        f"document.{output_format.lower()}",
        mime,
        data,
        key=f"document-export:{value.pk}:{output_format}",
    )
    with transaction.atomic():
        user = student(user, proof)
        approved_version(user, proof, document_id, version_id)
        result, _ = DocumentExport.objects.get_or_create(
            version=value,
            format=output_format,
            defaults={"owner": user, "asset": asset, "content_hash": value.content_hash},
        )
        audit(user, "document_export_saved", resource=result.pk, correlation=correlation)
        return result


@transaction.atomic
def bind_export_request(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    version_id: UUID,
    output_format: str,
    key: str,
) -> None:
    user = student(user, proof)
    value = approved_version(user, proof, document_id, version_id)
    if re.fullmatch(r"[A-Za-z0-9._~-]{16,128}", key) is None:
        raise IdentityError("IDEMPOTENCY_REQUIRED", 400, "A valid Idempotency-Key is required")
    if output_format not in {"PDF", "DOCX"}:
        raise IdentityError("INVALID_EXPORT_FORMAT", 400, "Choose PDF or DOCX")
    intent, _ = DocumentExportRequest.objects.get_or_create(
        owner=user,
        key_digest=digest("document-export:" + key),
        defaults={"version": value, "format": output_format},
    )
    if intent.version_id != value.pk or intent.format != output_format:
        raise IdentityError("IDEMPOTENCY_CONFLICT", 409, "Idempotency key already used")


@transaction.atomic
def freeze_approved_version(
    user: Account,
    proof: IdentitySession,
    document_id: UUID,
    version_id: UUID,
    *,
    trusted_application_id: UUID,
    correlation: Any = None,
) -> SubmissionSnapshot:
    """Internal primitive only: caller MUST prove owned, student-confirmed submission.

    No HTTP route exposes this parameter. Phase12's authoritative application binding
    and lifecycle do not exist yet and are an explicit independent integration gate.
    """
    user = student(user, proof)
    value = approved_version(user, proof, document_id, version_id)
    previous = SubmissionSnapshot.objects.filter(application_ref=trusted_application_id).first()
    if previous is not None and previous.owner_id != user.pk:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    result, _ = SubmissionSnapshot.objects.get_or_create(
        application_ref=trusted_application_id,
        version=value,
        defaults={"owner": user, "content_hash": value.content_hash},
    )
    audit(user, "document_submission_frozen", resource=result.pk, correlation=correlation)
    return result
