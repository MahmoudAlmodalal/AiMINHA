from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
from identity.models import Account, Challenge, IdentitySession
from identity.security import IdentityError, audit, digest, require_admin, require_student
from identity.services import challenge_owner, consume, deliver, issue

from privacy.models import (
    ConsentRecord,
    DeletionRequest,
    Disclosure,
    FilePurgeTask,
    LegalEnvelope,
    PrivateAsset,
    RetentionHead,
    RetentionPolicy,
    TicketAccess,
    TicketShare,
)


def legal_policy(policy: RetentionPolicy) -> None:
    envelope = LegalEnvelope.objects.select_for_update().filter(pk=policy.legal_envelope_id).first()
    if (
        not envelope
        or not envelope.approved
        or not envelope.min_days <= policy.recovery_days <= envelope.max_days
        or policy.recovery_timezone != "UTC"
        or policy.cutoff_algorithm != "UTC_ELAPSED_DAYS"
    ):
        raise IdentityError(
            "LEGAL_RETENTION_UNAVAILABLE",
            503,
            "Account deletion is unavailable pending policy approval",
        )


@transaction.atomic
def publish_retention(
    actor: Account,
    proof: IdentitySession,
    days: int,
    envelope: LegalEnvelope,
    expected_version: int,
) -> RetentionPolicy:
    actor = Account.objects.select_for_update().get(pk=actor.pk)
    require_admin(actor, proof)
    head = RetentionHead.objects.select_for_update().select_related("policy").get(pk=1)
    if head.policy.version != expected_version:
        raise IdentityError("STALE_POLICY", 412)
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise IdentityError("INVALID_POLICY", 400)
    policy = RetentionPolicy(
        version=head.policy.version + 1, recovery_days=days, legal_envelope=envelope
    )
    legal_policy(policy)
    policy.save()
    head.policy = policy
    head.save(update_fields=["policy"])
    audit(actor, "retention_policy_published", resource=policy.pk)
    return policy


def deletion_data(deletion: DeletionRequest) -> dict[str, Any]:
    return {
        "id": str(deletion.pk),
        "state": deletion.state,
        "confirmed_at": deletion.confirmed_at.isoformat().replace("+00:00", "Z"),
        "restore_until": deletion.restore_until.isoformat().replace("+00:00", "Z"),
        "policy_id": str(deletion.policy_id),
        "recovery_days": deletion.recovery_days,
        "recovery_timezone": deletion.recovery_timezone,
    }


@transaction.atomic
def delete_account(request: Any, token: str) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=request.user.pk)
    require_student(user)
    policy = RetentionHead.objects.select_related("policy__legal_envelope").get(pk=1).policy
    legal_policy(policy)
    consume(user, token, "REAUTH", session=digest(request.session.session_key))
    now = timezone.now()
    impact = request.session.get("deletion_impact", {})
    if (
        impact.get("policy") != str(policy.pk)
        or impact.get("actor") != str(user.pk)
        or not impact.get("seen_at")
        or now >= datetime.fromisoformat(impact["seen_at"]) + timedelta(minutes=5)
    ):
        raise IdentityError(
            "IMPACT_REVIEW_REQUIRED", 409, "Review the current deletion impact first"
        )
    deletion = DeletionRequest.objects.create(
        account=user,
        policy=policy,
        recovery_days=policy.recovery_days,
        recovery_timezone=policy.recovery_timezone,
        cutoff_algorithm=policy.cutoff_algorithm,
        confirmed_at=now,
        restore_until=now + timedelta(days=policy.recovery_days),
    )
    user.state, user.session_epoch = Account.State.DELETION_PENDING, user.session_epoch + 1
    user.consent_version += 1  # Invalidate captured processing snapshots immediately.
    user.save(update_fields=["state", "session_epoch", "consent_version"])
    prior_ai = (
        ConsentRecord.objects.filter(account=user, disclosure__purpose="PERSONAL_AI")
        .order_by("-version")
        .first()
    )
    if prior_ai and prior_ai.state == "GRANTED":
        ConsentRecord.objects.create(
            account=user,
            disclosure=prior_ai.disclosure,
            version=user.consent_version,
            state="REVOKED",
        )
        audit(
            user,
            "personal_ai_revoked_on_deletion",
            resource=prior_ai.disclosure_id,
            correlation=request.correlation_id,
        )
    IdentitySession.objects.filter(account=user, revoked_at__isnull=True).update(revoked_at=now)
    Challenge.objects.filter(account=user, consumed_at__isnull=True).update(consumed_at=now)
    audit(
        user, "account_deletion_confirmed", resource=deletion.pk, correlation=request.correlation_id
    )
    # No erasure before cutoff; object pointers are queued only by the guarded planner below.
    return deletion_data(deletion)


@transaction.atomic
def request_recovery(email: str, correlation: Any) -> None:
    user = Account.objects.select_for_update().filter(email__iexact=email.strip()).first()
    if user and user.state == Account.State.DELETION_PENDING:
        deletion = DeletionRequest.objects.filter(account=user, state="PENDING").first()
        now = timezone.now()
        if deletion and now < deletion.restore_until:
            token = issue(
                user,
                "RESTORE",
                deletion=deletion.pk,
                lifetime=min(timedelta(minutes=30), deletion.restore_until - now),
            )
            deliver(user, "RESTORE", token)
    audit(None, "account_recovery_requested", correlation=correlation)


@transaction.atomic
def restore_account(token: str, correlation: Any) -> None:
    # Canonical account lock serializes restore with purge planning. The trusted
    # receipt is accepted here after lock acquisition, never from client timestamps.
    user = Account.objects.select_for_update().get(pk=challenge_owner(token, "RESTORE"))
    deletion = (
        DeletionRequest.objects.select_for_update().filter(account=user, state="PENDING").first()
    )
    now = timezone.now()
    if (
        not deletion
        or user.state != Account.State.DELETION_PENDING
        or now >= deletion.restore_until
    ):
        raise IdentityError("RESTORATION_EXPIRED", 403, "Account restoration is unavailable")
    consume(user, token, "RESTORE", deletion=deletion.pk)
    deletion.state = DeletionRequest.State.RESTORED
    deletion.save(update_fields=["state"])
    user.state, user.session_epoch = Account.State.ACTIVE, user.session_epoch + 1
    user.save(update_fields=["state", "session_epoch"])
    Challenge.objects.filter(account=user, consumed_at__isnull=True).update(consumed_at=now)
    audit(user, "account_restored", resource=deletion.pk, correlation=correlation)
    # Restore grants neither a session nor Credits. A fresh sign-in is required.


@transaction.atomic
def record_consent(request: Any, disclosure_id: Any, decision: str) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=request.user.pk)
    require_student(user)
    expected = f'"consent-{user.consent_version}"'
    if request.headers.get("If-Match") != expected:
        raise IdentityError("STALE_CONSENT", 412, "Refresh consent state before changing it")
    disclosure = Disclosure.objects.filter(pk=disclosure_id).first()
    if disclosure is None:
        raise IdentityError("DISCLOSURE_UNAVAILABLE", 400)
    current = Disclosure.objects.filter(purpose=disclosure.purpose).order_by("-version").first()
    if current != disclosure or (decision == "GRANT" and not disclosure.available):
        raise IdentityError("DISCLOSURE_UNAVAILABLE", 409, "Review the current disclosure")
    user.consent_version += 1
    user.save(update_fields=["consent_version"])
    consent = ConsentRecord.objects.create(
        account=user,
        disclosure=disclosure,
        version=user.consent_version,
        state="GRANTED" if decision == "GRANT" else "REVOKED",
    )
    audit(
        user,
        "consent_" + decision.lower(),
        resource=disclosure.pk,
        correlation=request.correlation_id,
    )
    return consent_data(consent)


def consent_data(record: ConsentRecord) -> dict[str, Any]:
    return {
        "version": record.version,
        "state": record.state,
        "disclosure_id": str(record.disclosure_id),
        "recorded_at": record.recorded_at.isoformat(),
    }


def has_consent(user: Account, purpose: str, captured_version: int | None = None) -> bool:
    user.refresh_from_db()
    if not user.is_active or (
        captured_version is not None and captured_version != user.consent_version
    ):
        return False
    disclosure = Disclosure.objects.filter(purpose=purpose).order_by("-version").first()
    if not disclosure or not disclosure.available:
        return False
    record = (
        ConsentRecord.objects.filter(account=user, disclosure__purpose=purpose)
        .order_by("-version")
        .first()
    )
    return bool(record and record.disclosure_id == disclosure.pk and record.state == "GRANTED")


def asset_data(asset: PrivateAsset) -> dict[str, Any]:
    return {
        "id": str(asset.pk),
        "state": asset.state,
        "declared_size": asset.declared_size,
        "created_at": asset.created_at.isoformat().replace("+00:00", "Z"),
    }


@transaction.atomic
def owned_asset(actor: Account, asset_id: Any) -> dict[str, Any]:
    actor = Account.objects.select_for_update().get(pk=actor.pk)
    require_student(actor)  # Staff never acquire library access, even to an owned ID.
    asset = PrivateAsset.objects.filter(pk=asset_id, owner=actor).first()
    if asset is None:
        raise IdentityError("OWNERSHIP_REQUIRED")
    audit(actor, "private_file_metadata_read", resource=asset.pk)
    return asset_data(asset)


@transaction.atomic
def share_asset(request: Any, ticket_id: Any, asset_id: Any) -> dict[str, Any]:
    actor = Account.objects.select_for_update().get(pk=request.user.pk)
    require_student(actor)
    ticket = TicketAccess.objects.select_for_update().filter(pk=ticket_id, owner=actor).first()
    asset = PrivateAsset.objects.filter(pk=asset_id, owner=actor, state="ACCEPTED").first()
    if not ticket or not asset:
        raise IdentityError("OWNERSHIP_REQUIRED")
    share, created = TicketShare.objects.get_or_create(
        ticket=ticket, asset=asset, defaults={"owner": actor}
    )
    if not created and share.revoked_at:
        raise IdentityError("SHARE_REVOKED", 409)
    audit(actor, "ticket_asset_shared", resource=share.pk, correlation=request.correlation_id)
    return {"id": str(share.pk), "version": share.version}


@transaction.atomic
def revoke_share(request: Any, ticket_id: Any, share_id: Any) -> None:
    actor = Account.objects.select_for_update().get(pk=request.user.pk)
    require_student(actor)
    share = (
        TicketShare.objects.select_for_update()
        .filter(pk=share_id, ticket_id=ticket_id, owner=actor)
        .first()
    )
    if share is None:
        raise IdentityError("OWNERSHIP_REQUIRED")
    if request.headers.get("If-Match") != f'"share-{share.pk}-{share.version}"':
        raise IdentityError("STALE_SHARE", 412)
    share.revoked_at, share.version = timezone.now(), share.version + 1
    share.save(update_fields=["revoked_at", "version"])
    audit(actor, "ticket_asset_revoked", resource=share.pk, correlation=request.correlation_id)


@transaction.atomic
def ticket_asset(
    actor: Account, proof: IdentitySession, ticket_id: Any, share_id: Any
) -> dict[str, Any]:
    actor = Account.objects.select_for_update().get(pk=actor.pk)
    require_admin(actor, proof, "SUPPORT")
    owner_id = (
        TicketAccess.objects.filter(pk=ticket_id, assigned_admin=actor)
        .values_list("owner_id", flat=True)
        .first()
    )
    if owner_id is None:
        raise IdentityError("ASSIGNED_EXPLICIT_SHARE_REQUIRED")
    owner = Account.objects.select_for_update().get(pk=owner_id)
    require_student(owner)
    ticket = (
        TicketAccess.objects.select_for_update()
        .filter(pk=ticket_id, assigned_admin=actor, owner=owner)
        .first()
    )
    if not ticket:
        raise IdentityError("ASSIGNED_EXPLICIT_SHARE_REQUIRED")
    share = (
        TicketShare.objects.select_related("asset")
        .filter(
            pk=share_id,
            ticket=ticket,
            owner=ticket.owner,
            revoked_at__isnull=True,
            asset__owner=ticket.owner,
            asset__state="ACCEPTED",
        )
        .first()
    )
    if not share:
        raise IdentityError("ASSIGNED_EXPLICIT_SHARE_REQUIRED")
    audit(actor, "ticket_asset_metadata_read", resource=share.pk)
    return asset_data(share.asset)


@transaction.atomic
def queue_expired_deletion(account_id: Any) -> int:
    user = Account.objects.select_for_update().get(pk=account_id)
    deletion = (
        DeletionRequest.objects.select_for_update(of=("self",))
        .select_related("policy__legal_envelope")
        .filter(account=user, state="PENDING")
        .first()
    )
    if (
        not deletion
        or timezone.now() < deletion.restore_until
        or user.state != Account.State.DELETION_PENDING
    ):
        return 0
    legal_policy(deletion.policy)
    deletion.state, user.state = DeletionRequest.State.PURGING, Account.State.PURGING
    deletion.save(update_fields=["state"])
    user.save(update_fields=["state"])
    count = 0
    for asset in (
        PrivateAsset.objects.select_for_update().filter(owner=user).exclude(state="PURGED")
    ):
        _, created = FilePurgeTask.objects.get_or_create(
            deletion=deletion,
            asset=asset,
            defaults={"object_key": asset.object_key, "object_version": asset.object_version},
        )
        count += int(created)
        asset.state = "PURGE_PENDING"
        asset.save(update_fields=["state"])
    audit(user, "file_purge_queued", resource=deletion.pk)
    # No object deletion, retries against a changed object key/version, or completion
    # acknowledgment is possible without the Phase11 storage adapter and legal gates.
    return count
