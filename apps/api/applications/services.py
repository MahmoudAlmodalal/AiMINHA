"""Transactional tracker commands. No command submits to an external portal."""

from datetime import timedelta
from typing import Any
from uuid import UUID

from catalog.models import Scholarship, ScholarshipVersion, Source
from catalog.services import published_query
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from documents.models import DocumentApproval, DocumentVersion
from eligibility.models import ProfileHead
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, require_student
from private_files.models import ScanReceipt, StoredFile

from applications.models import (
    Application,
    ApplicationEvent,
    ApplicationRequirement,
    OfficialStatusReport,
    SavedScholarship,
    SelectedArtifact,
    SubmissionArtifact,
    SubmittedArtifactDeletionRequest,
)
from applications.rounds import round_options

EDGES = {
    "PREPARING": ["READY", "WITHDRAWN"],
    "READY": ["PREPARING", "SUBMITTED", "WITHDRAWN"],
    "SUBMITTED": ["UNDER_REVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"],
    "UNDER_REVIEW": ["ACCEPTED", "REJECTED", "WITHDRAWN"],
    "ACCEPTED": [],
    "REJECTED": [],
    "WITHDRAWN": [],
}


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


def owned(user: Account, application_id: UUID, *, lock: bool = False) -> Application:
    query = Application.objects.select_for_update() if lock else Application.objects
    value = query.filter(pk=application_id, owner=user).first()
    if value is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    return value


def current_catalog(scholarship_id: UUID, *, lock: bool = False) -> ScholarshipVersion:
    value = published_query().filter(scholarship_id=scholarship_id).first()
    if value is None:
        raise IdentityError(
            "CATALOG_UNAVAILABLE", 409, "Reviewed scholarship information is unavailable"
        )
    if lock:
        # Catalog moderation takes source then scholarship. Recheck after the same
        # ordered locks so revocation/publication cannot race readiness/submission.
        source_id = value.source_revision.source_id
        Source.objects.select_for_update().get(pk=source_id)
        Scholarship.objects.select_for_update().get(pk=scholarship_id)
        value = published_query().filter(scholarship_id=scholarship_id).first()
        if value is None or value.source_revision.source_id != source_id:
            raise IdentityError("CATALOG_UNAVAILABLE", 409, "Reload the reviewed source")
    return value


def require_revision(value: Any, expected: int) -> None:
    if value.revision != expected:
        raise IdentityError("STALE_REVISION", 412, "Reload the current tracker before saving")


def validate_observed(value: Any) -> None:
    if value is None or timezone.is_naive(value) or value > timezone.now():
        raise IdentityError(
            "INVALID_OBSERVED_AT", 400, "Use an explicit past or present observation time"
        )


def requirements_data(value: Application) -> list[dict[str, Any]]:
    selected = {
        row.requirement_id: row
        for row in SelectedArtifact.objects.filter(
            requirement__application=value,
            requirement__scholarship_version_id=value.scholarship_version_id,
        )
    }
    return [
        {
            "key": row.key,
            "label": row.label,
            "kind": "DOCUMENT",
            "status": "COMPLETE"
            if row.pk in selected
            and artifact_is_available(
                value.owner_id,
                selected[row.pk].version_id,
                selected[row.pk].asset_id,
                selected[row.pk].content_hash,
            )
            else "MISSING",
            "version_id": str(selected[row.pk].version_id)
            if row.pk in selected and selected[row.pk].version_id
            else None,
            "asset_id": str(selected[row.pk].asset_id)
            if row.pk in selected and selected[row.pk].asset_id
            else None,
            "content_hash": selected[row.pk].content_hash if row.pk in selected else None,
        }
        for row in value.requirements.filter(
            scholarship_version_id=value.scholarship_version_id
        ).order_by("position")
    ]


def manifest(value: Application) -> list[dict[str, Any]]:
    return [
        {key: row[key] for key in ("key", "version_id", "asset_id", "content_hash")}
        for row in requirements_data(value)
        if row["version_id"] is not None or row["asset_id"] is not None
    ]


def official_data(row: OfficialStatusReport) -> dict[str, Any]:
    return {
        "id": str(row.pk),
        "status": row.status,
        "source_url": row.source_url,
        "observed_at": row.observed_at,
        "recorded_at": row.recorded_at,
        "evidence_ref": row.evidence_ref,
        "origin": row.origin,
        "verified_official": row.origin == "VERIFIED_OFFICIAL",
    }


def application_data(value: Application) -> dict[str, Any]:
    from notifications.services import deadline_for_application

    requirements = requirements_data(value)
    current = published_query().filter(scholarship_id=value.scholarship_id).first()
    source_changed = current is None or current.pk != value.scholarship_version_id
    can_rebase = False
    if current is not None and source_changed and value.state == "PREPARING":
        try:
            can_rebase = any(
                row["round_key"] == value.round_key for row in round_options(current.rounds)
            )
        except IdentityError:
            pass
    return {
        "id": str(value.pk),
        "scholarship_id": str(value.scholarship_id),
        "scholarship_version_id": str(value.scholarship_version_id),
        "title": value.scholarship_version.title,
        "round_key": value.round_key,
        "round_snapshot": value.round_snapshot,
        "profile_version_id": str(value.profile_version_id) if value.profile_version_id else None,
        "state": value.state,
        "revision": value.revision,
        "submitted_sequence": value.submitted_sequence,
        "notes": value.head.notes_snapshot if value.head_id else "",
        "requirements_known": value.requirements_known,
        "requirements": requirements,
        "missing_count": sum(row["status"] == "MISSING" for row in requirements),
        "allowed_transitions": EDGES[value.state],
        "official_integration_available": False,
        "official_reports": [
            official_data(row) for row in value.official_reports.order_by("recorded_at", "pk")
        ],
        "created_at": value.created_at,
        "deadline": deadline_for_application(value),
        "source_changed": source_changed,
        "can_rebase": can_rebase,
    }


def event_data(row: ApplicationEvent) -> dict[str, Any]:
    return {
        key: getattr(row, key)
        for key in (
            "sequence",
            "from_state",
            "to_state",
            "kind",
            "source",
            "observed_at",
            "recorded_at",
            "evidence",
            "reason",
            "notes_snapshot",
            "manifest_snapshot",
            "correction_of_sequence",
            "student_submission_confirmation",
        )
    } | {
        "scholarship_version_id": str(row.scholarship_version_id),
        "profile_version_id": str(row.profile_version_id) if row.profile_version_id else None,
    }


def append_event(
    value: Application,
    user: Account,
    proof: IdentitySession,
    *,
    kind: str,
    to_state: str | None = None,
    observed_at: Any = None,
    evidence: str = "",
    reason: str = "",
    notes: str | None = None,
    confirmation: bool = False,
    correction: int | None = None,
) -> ApplicationEvent:
    observed_at = observed_at or timezone.now()
    validate_observed(observed_at)
    target = to_state or value.state
    row = ApplicationEvent.objects.create(
        application=value,
        sequence=value.revision + 1,
        actor=user,
        session_proof=proof,
        scholarship_version_id=value.scholarship_version_id,
        profile_version_id=value.profile_version_id,
        from_state=value.state if value.revision else "",
        to_state=target,
        kind=kind,
        observed_at=observed_at,
        evidence=evidence,
        reason=reason,
        notes_snapshot=notes
        if notes is not None
        else (value.head.notes_snapshot if value.head_id else ""),
        manifest_snapshot=manifest(value),
        student_submission_confirmation=confirmation,
        correction_of_sequence=correction,
    )
    value.head, value.revision, value.state = row, row.sequence, target
    if target == "SUBMITTED" and kind == "TRANSITION":
        value.submitted_sequence = row.sequence
    value.save(
        update_fields=[
            "head",
            "revision",
            "state",
            "submitted_sequence",
            "scholarship_version",
            "profile_version",
            "round_snapshot",
            "requirements_known",
        ]
    )
    return row


@transaction.atomic
def create_application(
    user: Account,
    proof: IdentitySession,
    scholarship_id: UUID,
    round_key: str,
    correlation: Any = None,
) -> Application:
    import hashlib

    user = student(user, proof)
    version = current_catalog(scholarship_id, lock=True)
    options = round_options(version.rounds)
    chosen = next((row for row in options if row["round_key"] == round_key), None)
    if chosen is None:
        raise IdentityError("INVALID_ROUND", 409, "Select a reviewed scholarship round")
    if Application.objects.filter(
        owner=user, scholarship_id=scholarship_id, round_key=round_key
    ).exists():
        raise IdentityError("APPLICATION_ROUND_EXISTS", 409, "This round already has a tracker")
    profile = ProfileHead.objects.filter(owner=user).first()
    value = Application.objects.create(
        owner=user,
        scholarship_id=scholarship_id,
        scholarship_version=version,
        profile_version_id=profile.current_id if profile else None,
        round_key=round_key,
        round_snapshot=chosen,
        requirements_known=bool(version.required_documents),
    )
    for position, label in enumerate(version.required_documents):
        key = hashlib.sha256(f"{position}:{label}".encode()).hexdigest()
        ApplicationRequirement.objects.create(
            application=value, scholarship_version=version, key=key, label=label, position=position
        )
    append_event(value, user, proof, kind="CREATED", reason="TRACKER_CREATED")
    audit(user, "application_created", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def read_application(
    user: Account, proof: IdentitySession, application_id: UUID, correlation: Any = None
) -> Application:
    user = student(user, proof)
    value = owned(user, application_id)
    audit(user, "application_read", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def list_applications(
    user: Account,
    proof: IdentitySession,
    correlation: Any = None,
    *,
    page: int = 1,
    page_size: int = 20,
) -> list[Application]:
    user = student(user, proof)
    audit(user, "application_list", correlation=correlation)
    return list(
        Application.objects.filter(owner=user)
        .select_related("head", "scholarship_version")
        .order_by("created_at", "pk")[(page - 1) * page_size : page * page_size]
    )


def validate_artifact(
    user: Account, version_id: UUID | None, asset_id: UUID | None, expected_hash: str
) -> tuple[DocumentVersion | None, Any]:
    from privacy.models import PrivateAsset

    if bool(version_id) == bool(asset_id):
        raise IdentityError(
            "INVALID_ARTIFACT", 400, "Select exactly one document version or upload"
        )
    if version_id:
        version = DocumentVersion.objects.filter(pk=version_id, owner=user).first()
        if version is None:
            raise IdentityError("FORBIDDEN", 403, "Access denied")
        if (
            expected_hash != version.content_hash
            or not DocumentApproval.objects.filter(
                version=version, owner=user, content_hash=expected_hash
            ).exists()
        ):
            raise IdentityError(
                "DOCUMENT_APPROVAL_REQUIRED", 409, "Approve the exact saved version first"
            )
        return version, None
    asset = PrivateAsset.objects.select_for_update().filter(pk=asset_id, owner=user).first()
    if asset is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    stored = StoredFile.objects.filter(
        asset=asset, capacity_state="RETAINED", sha256=expected_hash
    ).first()
    if (
        asset.state != "ACCEPTED"
        or stored is None
        or not ScanReceipt.objects.filter(
            file=stored, sha256=stored.sha256, size=stored.size, verdict="CLEAN"
        ).exists()
    ):
        raise IdentityError(
            "ARTIFACT_UNAVAILABLE", 409, "The exact accepted scanned file is required"
        )
    return None, asset


def artifact_is_available(
    owner_id: UUID, version_id: UUID | None, asset_id: UUID | None, expected_hash: str
) -> bool:
    """Current availability projection; historical manifests keep unavailable refs."""
    if bool(version_id) == bool(asset_id):
        return False
    if version_id:
        return DocumentVersion.objects.filter(
            pk=version_id,
            owner_id=owner_id,
            content_hash=expected_hash,
            documentapproval__owner_id=owner_id,
            documentapproval__content_hash=expected_hash,
        ).exists()
    return StoredFile.objects.filter(
        asset_id=asset_id,
        asset__owner_id=owner_id,
        asset__state="ACCEPTED",
        capacity_state="RETAINED",
        sha256=expected_hash,
        scanreceipt__sha256=expected_hash,
        scanreceipt__size=models.F("size"),
        scanreceipt__verdict="CLEAN",
    ).exists()


@transaction.atomic
def select_artifact(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    key: str,
    data: dict[str, Any],
    expected: int,
    correlation: Any = None,
) -> Application:
    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    require_revision(value, expected)
    if value.state != "PREPARING":
        raise IdentityError(
            "APPLICATION_MANIFEST_LOCKED", 409, "Return to Preparing before editing attachments"
        )
    slot = value.requirements.filter(
        scholarship_version_id=value.scholarship_version_id, key=key
    ).first()
    if slot is None:
        raise IdentityError("INVALID_REQUIREMENT", 400, "Select a reviewed document requirement")
    if data.get("clear"):
        SelectedArtifact.objects.filter(requirement=slot).delete()
    else:
        version, asset = validate_artifact(
            user, data.get("version_id"), data.get("asset_id"), data["content_hash"]
        )
        SelectedArtifact.objects.update_or_create(
            requirement=slot,
            defaults={"version": version, "asset": asset, "content_hash": data["content_hash"]},
        )
    append_event(value, user, proof, kind="ARTIFACT", reason="REQUIREMENT_SELECTION")
    audit(user, "application_artifact_selected", resource=value.pk, correlation=correlation)
    return value


def assert_ready(value: Application, user: Account) -> None:
    if current_catalog(value.scholarship_id, lock=True).pk != value.scholarship_version_id:
        raise IdentityError(
            "APPLICATION_SOURCE_CHANGED", 409, "Review and rebase the current approved requirements"
        )
    slots = list(value.requirements.filter(scholarship_version_id=value.scholarship_version_id))
    selected = list(
        SelectedArtifact.objects.filter(
            requirement__application=value,
            requirement__scholarship_version_id=value.scholarship_version_id,
        )
    )
    if not value.requirements_known or not slots or len(slots) != len(selected):
        raise IdentityError(
            "APPLICATION_INCOMPLETE", 409, "Unknown or missing requirements block Ready"
        )
    for item in selected:
        validate_artifact(user, item.version_id, item.asset_id, item.content_hash)


@transaction.atomic
def transition(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    data: dict[str, Any],
    expected: int,
    correlation: Any = None,
) -> Application:
    from documents.services import freeze_approved_version

    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    require_revision(value, expected)
    target = data["to_state"]
    if target not in EDGES[value.state]:
        raise IdentityError(
            "INVALID_APPLICATION_TRANSITION", 409, "This status transition is unavailable"
        )
    if target in {"READY", "SUBMITTED"}:
        assert_ready(value, user)
    confirmation = data.get("confirm_external_submission", False)
    if (target == "SUBMITTED") != confirmation:
        raise IdentityError(
            "STUDENT_SUBMISSION_CONFIRMATION_REQUIRED",
            409,
            "Only confirm Submitted after external submission",
        )
    event = append_event(
        value,
        user,
        proof,
        kind="TRANSITION",
        to_state=target,
        observed_at=data["observed_at"],
        evidence=data["evidence"],
        reason="STUDENT_STATUS_REPORT",
        confirmation=confirmation,
    )
    if target == "SUBMITTED":
        for item in SelectedArtifact.objects.filter(
            requirement__application=value,
            requirement__scholarship_version_id=value.scholarship_version_id,
        ).select_related("requirement", "version"):
            SubmissionArtifact.objects.create(
                application=value,
                event=event,
                requirement=item.requirement,
                version=item.version,
                asset=item.asset,
                content_hash=item.content_hash,
                label_snapshot=item.requirement.label,
            )
            if item.version_id:
                freeze_approved_version(
                    user,
                    proof,
                    item.version.document_id,
                    item.version_id,
                    trusted_application_id=value.pk,
                    correlation=correlation,
                )
    audit(user, "application_status_reported", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def rebase_application(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    expected: int,
    confirm: bool,
    correlation: Any = None,
) -> Application:
    import hashlib

    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    require_revision(value, expected)
    if value.state != "PREPARING" or not confirm:
        raise IdentityError(
            "APPLICATION_REBASE_DENIED",
            409,
            "Rebase requires explicit Preparing-state confirmation",
        )
    version = current_catalog(value.scholarship_id, lock=True)
    if version.pk == value.scholarship_version_id:
        raise IdentityError("APPLICATION_SOURCE_UNCHANGED", 409, "The pinned source is current")
    chosen = next(
        (row for row in round_options(version.rounds) if row["round_key"] == value.round_key), None
    )
    if chosen is None:
        raise IdentityError(
            "ROUND_IDENTITY_UNAVAILABLE", 503, "The current reviewed round cannot be matched"
        )
    SelectedArtifact.objects.filter(requirement__application=value).delete()
    value.scholarship_version, value.round_snapshot = version, chosen
    value.requirements_known = bool(version.required_documents)
    profile = ProfileHead.objects.filter(owner=user).first()
    value.profile_version_id = profile.current_id if profile else None
    for position, label in enumerate(version.required_documents):
        key = hashlib.sha256(f"{position}:{label}".encode()).hexdigest()
        ApplicationRequirement.objects.get_or_create(
            application=value,
            scholarship_version=version,
            key=key,
            defaults={"label": label, "position": position},
        )
    append_event(value, user, proof, kind="REBASE", reason="OWNER_REVIEWED_SOURCE_REBASE")
    audit(user, "application_source_rebased", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def edit_notes(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    notes: str,
    expected: int,
    correlation: Any = None,
) -> Application:
    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    require_revision(value, expected)
    append_event(value, user, proof, kind="NOTES", reason="OWNER_NOTES_EDIT", notes=notes)
    audit(user, "application_notes_saved", resource=value.pk, correlation=correlation)
    return value


@transaction.atomic
def correct_evidence(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    data: dict[str, Any],
    expected: int,
    correlation: Any = None,
) -> Application:
    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    require_revision(value, expected)
    if not value.events.filter(sequence=data["correction_of_sequence"]).exists():
        raise IdentityError("INVALID_CORRECTION", 400, "Select earlier evidence in this tracker")
    append_event(
        value,
        user,
        proof,
        kind="CORRECTION",
        observed_at=data["observed_at"],
        evidence=data["evidence"],
        reason=data["reason"],
        correction=data["correction_of_sequence"],
    )
    audit(user, "application_evidence_corrected", resource=value.pk, correlation=correlation)
    return value


def asset_is_submitted(asset_id: UUID) -> bool:
    return SubmissionArtifact.objects.filter(asset_id=asset_id).exists()


def artifact_options(value: Application) -> dict[str, Any]:
    versions = DocumentVersion.objects.filter(
        owner_id=value.owner_id,
        documentapproval__owner_id=value.owner_id,
        documentapproval__content_hash=models.F("content_hash"),
    ).order_by("document_id", "number")
    files = StoredFile.objects.filter(
        asset__owner_id=value.owner_id,
        asset__state="ACCEPTED",
        capacity_state="RETAINED",
        scanreceipt__sha256=models.F("sha256"),
        scanreceipt__size=models.F("size"),
        scanreceipt__verdict="CLEAN",
    ).order_by("asset_id")
    return {
        "versions": [
            {
                "id": str(row.pk),
                "document_id": str(row.document_id),
                "title": row.title,
                "language": row.language,
                "number": row.number,
                "content_hash": row.content_hash,
            }
            for row in versions[:100]
        ],
        "files": [
            {
                "asset_id": str(row.asset_id),
                "declared_size": row.size,
                "content_hash": row.sha256,
                "mime": row.mime,
            }
            for row in files[:100]
        ],
    }


def submission_data(row: SubmissionArtifact) -> dict[str, Any]:
    return {
        "id": str(row.pk),
        "requirement_key": row.requirement.key,
        "label_snapshot": row.label_snapshot,
        "version_id": str(row.version_id) if row.version_id else None,
        "document_id": str(row.version.document_id) if row.version_id else None,
        "asset_id": str(row.asset_id) if row.asset_id else None,
        "content_hash": row.content_hash,
        "submitted_sequence": row.event.sequence,
    }


def deletion_data(row: SubmittedArtifactDeletionRequest) -> dict[str, Any]:
    return {
        "id": str(row.pk),
        "artifact_id": str(row.artifact_id),
        "reason": row.reason,
        "state": row.state,
        "created_at": row.created_at,
    }


@transaction.atomic
def request_artifact_deletion(
    user: Account,
    proof: IdentitySession,
    application_id: UUID,
    artifact_id: UUID,
    reason: str,
    correlation: Any = None,
) -> SubmittedArtifactDeletionRequest:
    user = student(user, proof)
    value = owned(user, application_id, lock=True)
    artifact = SubmissionArtifact.objects.filter(pk=artifact_id, application=value).first()
    if artifact is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    if not reason.strip() or len(reason) > 1000:
        raise IdentityError("INVALID_REQUEST", 400, "A deletion request reason is required")
    row = SubmittedArtifactDeletionRequest.objects.create(
        owner=user, application=value, artifact=artifact, reason=reason
    )
    audit(user, "application_deletion_requested", resource=row.pk, correlation=correlation)
    return row


def erase_submitted_artifact(*args: Any, **kwargs: Any) -> None:
    raise IdentityError(
        "LEGAL_ERASURE_UNAVAILABLE", 503, "An approved scoped legal erasure plan is required"
    )


def relationship_exists(owner_id: UUID, scholarship_id: UUID, round_key: str | None = None) -> bool:
    if SavedScholarship.objects.filter(
        owner_id=owner_id, scholarship_id=scholarship_id, active=True
    ).exists():
        return True
    rows = Application.objects.filter(owner_id=owner_id, scholarship_id=scholarship_id).exclude(
        state="WITHDRAWN"
    )
    if round_key is not None:
        rows = rows.filter(round_key=round_key)
    return rows.exists()


def saved_data(value: SavedScholarship) -> dict[str, Any]:
    return {
        "id": str(value.pk),
        "scholarship_id": str(value.scholarship_id),
        "title": value.scholarship.published_version.title
        if value.scholarship.published_version_id
        else "",
        "active": value.active,
        "revision": value.revision,
    }


@transaction.atomic
def set_saved(
    user: Account,
    proof: IdentitySession,
    scholarship_id: UUID,
    *,
    active: bool,
    expected: int | None = None,
    correlation: Any = None,
) -> SavedScholarship:
    user = student(user, proof)
    if active:
        current_catalog(scholarship_id, lock=True)
    value = (
        SavedScholarship.objects.select_for_update()
        .filter(owner=user, scholarship_id=scholarship_id)
        .first()
    )
    if value is None:
        if not active:
            raise IdentityError("FORBIDDEN", 403, "Access denied")
        value = SavedScholarship.objects.create(owner=user, scholarship_id=scholarship_id)
    else:
        if expected is not None:
            require_revision(value, expected)
        if value.active != active:
            value.active, value.revision = active, value.revision + 1
            value.save(update_fields=["active", "revision"])
    audit(
        user,
        "scholarship_saved" if active else "scholarship_unsaved",
        resource=scholarship_id,
        correlation=correlation,
    )
    return value


def record_official_status(*args: Any, **kwargs: Any) -> None:
    raise IdentityError(
        "OFFICIAL_INTEGRATION_UNAVAILABLE",
        503,
        "A lawful documented status integration is unavailable",
    )


@transaction.atomic
def fixed_synthetic_official_proof(application_id: UUID) -> OfficialStatusReport:
    """No client route. Fixed local fixture proves separate streams without official claims."""
    if not settings.LOCAL:
        raise IdentityError("SYNTHETIC_EXECUTION_DISABLED", 503, "Local proof is unavailable")
    value = Application.objects.select_for_update().get(pk=application_id)
    return OfficialStatusReport.objects.create(
        application=value,
        status="UNDER_REVIEW",
        source_url="https://synthetic.example.invalid/application-status",
        observed_at=timezone.now(),
        evidence_ref="LOCAL_FIXED_SYNTHETIC_PROOF",
        origin="SYNTHETIC_LOCAL",
    )
