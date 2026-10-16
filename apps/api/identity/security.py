import hashlib
import hmac
from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import login
from django.db import transaction
from django.middleware.csrf import rotate_token
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission

from identity.models import Account, IdentitySession, RateBucket


class IdentityError(APIException):
    def __init__(self, code: str, status: int = 403, title: str = "Request not permitted") -> None:
        self.code = code
        self.status_code = status
        self.safe_title = title
        super().__init__(title)


def digest(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def adult(birth_date: date, today: date | None = None) -> bool:
    today = today or timezone.now().date()
    if birth_date > today or birth_date.year + 18 > today.year:
        return False
    # A Feb29 birthday is certainly 18 by March1 in a non-leap anniversary year.
    # Feb28 remains denied: no unapproved earlier legal birthday is assumed.
    try:
        anniversary = birth_date.replace(year=birth_date.year + 18)
    except ValueError:
        anniversary = date(birth_date.year + 18, 3, 1)
    return birth_date <= today and today >= anniversary


def audit(
    actor: Any,
    action: str,
    outcome: str = "ALLOW",
    resource: Any = None,
    reason: str = "",
    correlation: Any = None,
) -> None:
    from privacy.models import PrivacyAudit

    PrivacyAudit.objects.create(
        actor_id=getattr(actor, "pk", None),
        action=action,
        outcome=outcome,
        resource_id=resource,
        reason=reason,
        correlation_id=correlation,
    )


def throttle(operation: str, value: str) -> None:
    blocked = False
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateBucket.objects.get_or_create(key=digest(operation + ":" + value))
        bucket = RateBucket.objects.select_for_update().get(pk=bucket.pk)
        if now >= bucket.window_started + timedelta(minutes=15):
            bucket.window_started, bucket.attempts = now, 0
        bucket.attempts += 1
        blocked = bucket.attempts > settings.IDENTITY_RATE_LIMIT
        bucket.save(update_fields=["window_started", "attempts"])
    if blocked:
        raise IdentityError("RATE_LIMITED", 429, "Too many attempts; try later")


def require_student(user: Account) -> None:
    if (
        user.role != Account.Role.STUDENT
        or user.state != Account.State.ACTIVE
        or not user.email_verified_at
        or not adult(user.birth_date)
    ):
        raise IdentityError("VERIFIED_ADULT_REQUIRED")


def require_admin(user: Account, proof: IdentitySession | None, scope: str = "PRIVACY") -> None:
    if proof is not None:
        proof.refresh_from_db()
    now = timezone.now()
    if (
        user.role != Account.Role.ADMIN
        or not user.is_active
        or not user.email_verified_at
        or scope not in user.admin_scopes
        or not proof
        or proof.account_id != user.pk
        or proof.epoch != user.session_epoch
        or proof.revoked_at is not None
        or now >= proof.expires_at
        or not proof.mfa_verified_at
        or now >= proof.mfa_verified_at + timedelta(minutes=15)
    ):
        raise IdentityError("ADMIN_MFA_REQUIRED")


def open_session(request: Any, user: Account) -> IdentitySession:
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    # Always rotate even if the same actor signs in again.
    request.session.cycle_key()
    rotate_token(request)
    now = timezone.now()
    request.session.set_expiry(24 * 60 * 60)
    return IdentitySession.objects.create(
        account=user,
        digest=digest(request.session.session_key),
        epoch=user.session_epoch,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=7),
    )


class IdentityAuthentication(SessionAuthentication):
    def authenticate(self, request: Any) -> Any:
        result = super().authenticate(request)
        if result is None:
            return None
        user = result[0]
        proof = IdentitySession.objects.filter(
            digest=digest(request.session.session_key),
            account=user,
            epoch=user.session_epoch,
            revoked_at__isnull=True,
        ).first()
        now = timezone.now()
        if (
            proof is None
            or now >= proof.expires_at
            or now >= proof.last_seen_at + timedelta(hours=24)
        ):
            request.session.flush()
            raise IdentityError("SESSION_EXPIRED", 401, "Sign in again")
        IdentitySession.objects.filter(pk=proof.pk, revoked_at__isnull=True).update(
            last_seen_at=now
        )
        request.identity_session = proof
        return user, proof

    def authenticate_header(self, request: Any) -> str:
        return "Session"


class VerifiedAdult(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        if not request.user.is_authenticated:
            return False
        require_student(request.user)
        return True


class PublicCatalogRead(BasePermission):
    """Phase07 may opt its published projection into this permission; no private read follows."""

    def has_permission(self, request: Any, view: Any) -> bool:
        return request.method in {"GET", "HEAD", "OPTIONS"}


def session_data(user: Account, proof: IdentitySession) -> dict[str, Any]:
    expiry: datetime = min(proof.expires_at, timezone.now() + timedelta(hours=24))
    return {
        "actor_id": str(user.pk),
        "verified_email": bool(user.email_verified_at),
        "adult_eligible": adult(user.birth_date),
        "roles": [user.role],
        "expires_at": expiry.isoformat().replace("+00:00", "Z"),
    }
