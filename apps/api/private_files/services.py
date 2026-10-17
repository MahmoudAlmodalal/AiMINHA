"""Owner-scoped exact-byte scan/accept/read boundary. Never hold locks across I/O."""

import hashlib
import secrets
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, digest, require_student
from privacy.models import PrivateAsset, TicketShare
from privacy.services import asset_data, ticket_asset

from private_files import scanner, storage, validation
from private_files.models import AccessGrant, ScanReceipt, StorageLock, StoredFile


def _owner(owner_id: Any) -> Account:
    actor = Account.objects.get(pk=owner_id)
    require_student(actor)
    return actor


def _owned(owner_id: Any, asset_id: Any) -> StoredFile:
    _owner(owner_id)
    file = (
        StoredFile.objects.select_related("asset")
        .filter(asset_id=asset_id, asset__owner_id=owner_id)
        .first()
    )
    if file is None:
        raise IdentityError("OWNERSHIP_REQUIRED", 404)
    return file


def _accepted(file: StoredFile) -> None:
    receipt = ScanReceipt.objects.filter(file=file).first()
    if (
        file.asset.state != "ACCEPTED"
        or file.capacity_state != "RETAINED"
        or not receipt
        or receipt.verdict != "CLEAN"
        or receipt.sha256 != file.sha256
        or receipt.size != file.size
        or file.asset.object_version != file.sha256
        or file.asset.declared_size != file.size
    ):
        raise IdentityError("FILE_NOT_READY", 409, "File is not available")


def _same(file: StoredFile, name: str, mime: str, data: bytes) -> None:
    if (file.sha256, file.size, file.name, file.mime) != (
        hashlib.sha256(data).hexdigest(),
        len(data),
        name,
        mime,
    ):
        raise IdentityError("IDEMPOTENCY_CONFLICT", 409)


def _release_after_cleanup(file: StoredFile) -> bool:
    try:
        with storage.lease(file):
            storage.remove(file)
            with transaction.atomic():
                StorageLock.objects.select_for_update().get(pk=1)
                current = StoredFile.objects.select_for_update().get(pk=file.pk)
                if current.capacity_state != "RELEASED":
                    current.capacity_state, current.capacity_bytes = "RELEASED", 0
                    current.save(update_fields=["capacity_state", "capacity_bytes"])
                    PrivateAsset.objects.filter(pk=file.pk).update(state="PURGED")
    except (OSError, IdentityError):
        return False
    return True


def _assert_writable(file: StoredFile) -> None:
    """Called under the physical lease, including after any delayed worker resumes."""
    current = StoredFile.objects.select_related("asset").get(pk=file.pk)
    if (
        current.capacity_state != "RESERVED"
        or current.asset.state != "QUARANTINED"
        or current.lease_expires_at <= timezone.now()
    ):
        raise IdentityError("FILE_LEASE_EXPIRED", 409, "File processing expired; retry upload")


def recover_abandoned(limit: int = 100) -> dict[str, int]:
    """Trusted local worker: purge expired attempts; never accepts or bills a result."""
    recovered, pending = 0, 0
    candidates = list(
        StoredFile.objects.filter(
            lease_expires_at__lte=timezone.now(),
            asset__state__in=["QUARANTINED", "PURGE_PENDING"],
        )
        .exclude(capacity_state="RELEASED")
        .order_by("created_at")[: max(0, min(limit, 1000))]
    )
    for file in candidates:
        try:
            with storage.lease(file):
                with transaction.atomic():
                    StorageLock.objects.select_for_update().get(pk=1)
                    current = (
                        StoredFile.objects.select_for_update()
                        .select_related("asset")
                        .get(pk=file.pk)
                    )
                    if (
                        current.capacity_state == "RELEASED"
                        or current.asset.state == "ACCEPTED"
                        or current.lease_expires_at > timezone.now()
                    ):
                        continue
                    PrivateAsset.objects.filter(pk=file.pk).update(state="PURGE_PENDING")
                storage.remove(file)
                with transaction.atomic():
                    StorageLock.objects.select_for_update().get(pk=1)
                    current = StoredFile.objects.select_for_update().get(pk=file.pk)
                    if current.capacity_state != "RELEASED":
                        current.capacity_state, current.capacity_bytes = "RELEASED", 0
                        current.save(update_fields=["capacity_state", "capacity_bytes"])
                        PrivateAsset.objects.filter(pk=file.pk).update(state="PURGED")
                audit(None, "private_file_crash_recovered", resource=file.pk)
                recovered += 1
        except (OSError, IdentityError):
            pending += 1
    return {"recovered": recovered, "pending": pending}


def store_bytes(owner_id: Any, name: str, mime: str, data: bytes, key: str) -> PrivateAsset:
    _owner(owner_id)
    if not isinstance(data, bytes):
        raise IdentityError("INVALID_FILE", 400)
    validation.envelope(name, mime, data)
    if not isinstance(key, str) or not 1 <= len(key) <= 128:
        raise IdentityError("IDEMPOTENCY_KEY_REQUIRED", 400)
    operation = digest("private-file:" + str(owner_id) + ":" + key)
    with transaction.atomic():
        StorageLock.objects.select_for_update().get(pk=1)
        actor = Account.objects.select_for_update().get(pk=owner_id)
        require_student(actor)
        existing = (
            StoredFile.objects.select_related("asset")
            .filter(operation_digest=operation)
            .order_by("-created_at")
            .first()
        )
        if existing:
            _same(existing, name, mime, data)
            if existing.capacity_state != "RELEASED":
                _accepted(existing)
                return existing.asset
    storage.root()
    scanner.health()  # Reject outage/stale signatures before capacity or persistent bytes.
    with transaction.atomic():
        StorageLock.objects.select_for_update().get(pk=1)
        actor = Account.objects.select_for_update().get(pk=owner_id)
        require_student(actor)
        existing = (
            StoredFile.objects.select_related("asset")
            .filter(operation_digest=operation)
            .exclude(capacity_state="RELEASED")
            .first()
        )
        if existing:
            _same(existing, name, mime, data)
            _accepted(existing)
            return existing.asset
        total = StoredFile.objects.aggregate(total=Sum("capacity_bytes"))["total"] or 0
        owned = (
            StoredFile.objects.filter(asset__owner_id=owner_id).aggregate(
                total=Sum("capacity_bytes")
            )["total"]
            or 0
        )
        if (
            total + len(data) > validation.MAX_GLOBAL_BYTES
            or owned + len(data) > validation.MAX_STUDENT_BYTES
        ):
            raise IdentityError("STORAGE_QUOTA_EXCEEDED", 409, "Private storage limit reached")
        sha256 = hashlib.sha256(data).hexdigest()
        asset = PrivateAsset.objects.create(
            owner=actor, object_version=sha256, declared_size=len(data)
        )
        file = StoredFile.objects.create(
            asset=asset,
            storage_token=asset.object_key,
            operation_digest=operation,
            sha256=sha256,
            size=len(data),
            mime=mime,
            name=name,
            capacity_bytes=len(data),
        )
    try:
        with storage.lease(file):
            _assert_writable(file)
            storage.write(file, data)
            evidence = scanner.scan(data)
            validation.structural(mime, data)
            # Re-read exact stored object: scanner's immutable receipt must bind actual bytes.
            if hashlib.sha256(storage.read(file)).hexdigest() != file.sha256:
                raise IdentityError("FILE_INTEGRITY_FAILED", 409)
            with transaction.atomic():
                StorageLock.objects.select_for_update().get(pk=1)
                actor = Account.objects.select_for_update().get(pk=owner_id)
                require_student(actor)
                file = StoredFile.objects.select_for_update().get(pk=file.pk)
                if file.capacity_state != "RESERVED" or file.lease_expires_at <= timezone.now():
                    raise IdentityError("FILE_NOT_READY", 409)
                ScanReceipt.objects.create(
                    file=file,
                    sha256=sha256,
                    size=len(data),
                    engine=evidence.engine,
                    signature_version=evidence.signature_version,
                    signature_at=evidence.signature_at,
                )
                file.capacity_state = "RETAINED"
                file.save(update_fields=["capacity_state"])
                PrivateAsset.objects.filter(pk=asset.pk).update(state="ACCEPTED")
                audit(actor, "private_file_accepted", resource=asset.pk)
            asset.refresh_from_db()
            return asset
    except Exception as exc:
        PrivateAsset.objects.filter(pk=asset.pk).exclude(state="PURGED").update(
            state="PURGE_PENDING"
        )
        _release_after_cleanup(file)
        if isinstance(exc, IdentityError):
            raise
        raise IdentityError(
            "PRIVATE_STORAGE_UNAVAILABLE", 503, "File was not accepted; use manual data entry"
        ) from exc


def _read_exact(file: StoredFile) -> bytes:
    _accepted(file)
    try:
        data = storage.read(file)
    except (OSError, IdentityError) as exc:
        raise IdentityError("PRIVATE_STORAGE_UNAVAILABLE", 503) from exc
    if len(data) != file.size or hashlib.sha256(data).hexdigest() != file.sha256:
        raise IdentityError("FILE_INTEGRITY_FAILED", 409)
    return data


def read_owned_bytes(owner_id: Any, asset_id: Any) -> bytes:
    file = _owned(owner_id, asset_id)
    data = _read_exact(file)
    _accepted(_owned(owner_id, asset_id))  # Account/state revocation after storage I/O.
    audit(Account.objects.get(pk=owner_id), "private_file_bytes_read", resource=file.pk)
    return data


def delete_owned(owner_id: Any, asset_id: Any) -> None:
    with transaction.atomic():
        StorageLock.objects.select_for_update().get(pk=1)
        file = _owned(owner_id, asset_id)
        Account.objects.select_for_update().get(pk=owner_id)
        # Submitted document snapshots must retain immutable downloadable bytes.
        from documents.services import asset_is_protected

        if asset_is_protected(file.pk):
            raise IdentityError("FILE_FROZEN", 409)
        if file.capacity_state == "RELEASED":
            return
        if file.asset.state == "QUARANTINED":
            raise IdentityError("FILE_NOT_READY", 409)
        PrivateAsset.objects.filter(pk=file.pk).update(state="PURGE_PENDING")
    if not _release_after_cleanup(file):
        raise IdentityError(
            "FILE_CLEANUP_PENDING", 503, "Deletion pending; storage capacity remains reserved"
        )
    audit(Account.objects.get(pk=owner_id), "private_file_deleted", resource=file.pk)


def issue_grant(
    actor: Account, proof: IdentitySession, asset_id: Any, share: TicketShare | None = None
) -> dict[str, str]:
    if share:
        ticket_asset(actor, proof, share.ticket_id, share.pk)
        file = StoredFile.objects.select_related("asset").filter(pk=share.asset_id).first()
        if not file:
            raise IdentityError("FILE_NOT_READY", 409)
    else:
        file = _owned(actor.pk, asset_id)
    _accepted(file)
    if (
        proof.account_id != actor.pk
        or proof.revoked_at
        or proof.epoch != actor.session_epoch
        or proof.expires_at <= timezone.now()
    ):
        raise IdentityError("SESSION_EXPIRED", 401)
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(seconds=60)
    AccessGrant.objects.create(
        file=file,
        actor=actor,
        session=proof,
        share=share,
        digest=digest(token),
        sha256=file.sha256,
        expires_at=expires_at,
    )
    audit(actor, "private_file_grant_issued", resource=file.pk)
    return {"token": token, "expires_at": expires_at.isoformat()}


def read_granted(
    actor: Account,
    proof: IdentitySession,
    asset_id: Any,
    token: str,
    share: TicketShare | None = None,
) -> tuple[StoredFile, bytes]:
    def authorize() -> StoredFile:
        proof.refresh_from_db()
        actor.refresh_from_db()
        if (
            not token
            or len(token) > 128
            or proof.account_id != actor.pk
            or proof.revoked_at
            or proof.epoch != actor.session_epoch
            or proof.expires_at <= timezone.now()
        ):
            raise IdentityError("ACCESS_GRANT_INVALID", 403)
        grant = (
            AccessGrant.objects.select_related("file__asset")
            .filter(
                digest=digest(token),
                actor=actor,
                session=proof,
                file_id=asset_id,
                share=share,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
        if not grant or grant.sha256 != grant.file.sha256:
            raise IdentityError("ACCESS_GRANT_INVALID", 403)
        if share:
            ticket_asset(actor, proof, share.ticket_id, share.pk)
        else:
            _owner(actor.pk)
            if grant.file.asset.owner_id != actor.pk:
                raise IdentityError("OWNERSHIP_REQUIRED", 404)
        _accepted(grant.file)
        return grant.file

    file = authorize()
    data = _read_exact(file)
    authorize()  # Assignment/share/session/account revoked during I/O immediately denies delivery.
    audit(actor, "ticket_file_bytes_read" if share else "private_file_bytes_read", resource=file.pk)
    return file, data


def capabilities() -> dict[str, Any]:
    available = True
    try:
        storage.root()
        scanner.health()
    except IdentityError:
        available = False
    return {
        "upload_available": available,
        "manual_entry_available": True,
        "allowed_mime_types": list(dict.fromkeys(validation.MIMES.values())),
        "max_file_bytes": validation.MAX_FILE_BYTES,
        "max_student_bytes": validation.MAX_STUDENT_BYTES,
        "max_global_bytes": validation.MAX_GLOBAL_BYTES,
    }


def upload_data(asset: PrivateAsset) -> dict[str, Any]:
    return asset_data(asset)
