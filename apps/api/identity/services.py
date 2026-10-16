import json
import re
import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.utils import timezone

from identity.models import Account, Challenge, CommandReceipt, IdentitySession
from identity.security import IdentityError, adult, audit, digest, open_session, session_data


def deliver(user: Account, purpose: str, token: str) -> None:
    if not settings.LOCAL and not settings.EMAIL_HOST:
        raise IdentityError("EMAIL_UNAVAILABLE", 503, "Email delivery is unavailable")
    try:
        send_mail(
            "MinhaAI account verification",
            f"{purpose}\nVerification code: {token}\n"
            "Enter this code only in MinhaAI. It expires and can be used once.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        raise IdentityError("EMAIL_UNAVAILABLE", 503, "Email delivery is unavailable") from None


def issue(
    user: Account,
    purpose: str,
    *,
    session: str = "",
    deletion: Any = None,
    lifetime: timedelta = timedelta(minutes=30),
) -> str:
    token = secrets.token_urlsafe(48)
    now = timezone.now()
    Challenge.objects.filter(account=user, purpose=purpose, consumed_at__isnull=True).update(
        consumed_at=now
    )
    Challenge.objects.create(
        account=user,
        purpose=purpose,
        digest=digest(token),
        session_digest=session,
        deletion_id=deletion,
        expires_at=now + lifetime,
    )
    return token


def challenge_owner(token: str, purpose: str) -> Any:
    owner = (
        Challenge.objects.filter(digest=digest(token), purpose=purpose)
        .values_list("account_id", flat=True)
        .first()
    )
    if owner is None:
        raise IdentityError("INVALID_PROOF", 400, "Verification failed")
    return owner


def consume(
    user: Account, token: str, purpose: str, *, session: str = "", deletion: Any = None
) -> Challenge:
    proof = (
        Challenge.objects.select_for_update()
        .filter(account=user, digest=digest(token), purpose=purpose)
        .first()
    )
    now = timezone.now()
    if (
        proof is None
        or proof.consumed_at
        or now >= proof.expires_at
        or proof.session_digest != session
        or proof.deletion_id != deletion
    ):
        raise IdentityError("INVALID_PROOF", 400, "Verification failed")
    proof.consumed_at = now
    proof.save(update_fields=["consumed_at"])
    return proof


def password_valid(password: str, user: Account) -> None:
    try:
        validate_password(password, user)
    except ValidationError:
        raise IdentityError("PASSWORD_POLICY", 400, "Choose a stronger password") from None


@transaction.atomic
def register(data: dict[str, Any], correlation: Any) -> None:
    if not adult(data["birth_date"]):
        raise IdentityError("ADULT_REQUIRED", 400, "An adult date of birth is required")
    email = data["email"].strip().lower()
    user = Account(email=email, birth_date=data["birth_date"], locale=data["locale"])
    password_valid(data["password"], user)
    user.set_password(data["password"])
    try:
        with transaction.atomic():
            user.save(force_insert=True)
    except IntegrityError:
        # Same acknowledgment, password work, and no account identity disclosure.
        audit(None, "registration", "DENY", reason="EXISTING_IDENTITY", correlation=correlation)
        return
    token = issue(user, "VERIFY_EMAIL", lifetime=timedelta(hours=24))
    deliver(user, "VERIFY_EMAIL", token)
    audit(user, "registration", correlation=correlation)


@transaction.atomic
def verify_email(token: str, correlation: Any) -> None:
    user = Account.objects.select_for_update().get(pk=challenge_owner(token, "VERIFY_EMAIL"))
    consume(user, token, "VERIFY_EMAIL")
    if user.state != Account.State.PENDING or not adult(user.birth_date):
        raise IdentityError("ACTIVATION_DENIED")
    user.email_verified_at, user.state = timezone.now(), Account.State.ACTIVE
    user.save(update_fields=["email_verified_at", "state"])
    audit(user, "email_verified", correlation=correlation)
    # The grant shares activation's account lock and transaction: neither commits alone.
    from credits.services import grant_signup

    grant_signup(user.pk)


@transaction.atomic
def sign_in(request: Any, data: dict[str, Any]) -> dict[str, Any]:
    user = Account.objects.select_for_update().filter(email__iexact=data["email"].strip()).first()
    if user is None:
        check_password(data["password"], make_password(None))
        # Perform the normal password hasher work too for an unknown identity.
        make_password(data["password"])
        raise IdentityError("INVALID_CREDENTIALS", 401, "Sign in failed")
    if (
        not user.check_password(data["password"])
        or not user.is_active
        or not user.email_verified_at
        or not adult(user.birth_date)
    ):
        raise IdentityError("INVALID_CREDENTIALS", 401, "Sign in failed")
    proof = open_session(request, user)
    audit(user, "sign_in", correlation=request.correlation_id)
    return session_data(user, proof)


@transaction.atomic
def reauthenticate(request: Any, password: str) -> str:
    user = Account.objects.select_for_update().get(pk=request.user.pk)
    if not user.is_active or not user.check_password(password):
        raise IdentityError("REAUTHENTICATION_FAILED")
    token = issue(
        user, "REAUTH", session=digest(request.session.session_key), lifetime=timedelta(minutes=5)
    )
    request.session["reauthenticated_at"] = timezone.now().isoformat()
    audit(user, "reauthentication", correlation=request.correlation_id)
    return token


@transaction.atomic
def reset_request(email: str, correlation: Any, purpose: str = "RESET_PASSWORD") -> None:
    user = Account.objects.select_for_update().filter(email__iexact=email.strip()).first()
    allowed = {Account.State.PENDING} if purpose == "VERIFY_EMAIL" else {Account.State.ACTIVE}
    if user is not None and user.state in allowed:
        token = issue(user, purpose)
        deliver(user, purpose, token)
    audit(None, "verification_requested", correlation=correlation)


@transaction.atomic
def reset_password(token: str, password: str, correlation: Any) -> None:
    user = Account.objects.select_for_update().get(pk=challenge_owner(token, "RESET_PASSWORD"))
    if not user.is_active:
        raise IdentityError("INVALID_PROOF", 400, "Verification failed")
    consume(user, token, "RESET_PASSWORD")
    password_valid(password, user)
    user.set_password(password)
    user.session_epoch += 1
    user.save(update_fields=["password", "session_epoch"])
    IdentitySession.objects.filter(account=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    Challenge.objects.filter(account=user, consumed_at__isnull=True).update(
        consumed_at=timezone.now()
    )
    audit(user, "password_reset", correlation=correlation)


def command(
    request: Any, name: str, data: dict[str, Any], handler: Any, status: int
) -> tuple[dict[str, Any], int]:
    key = request.headers.get("Idempotency-Key", "")
    if re.fullmatch(r"[A-Za-z0-9._~-]{16,128}", key) is None:
        raise IdentityError("IDEMPOTENCY_REQUIRED", 400, "A valid Idempotency-Key is required")
    if not request.session.session_key:
        request.session.create()
    principal = (
        str(request.user.pk) if request.user.is_authenticated else request.session.session_key
    )
    scope = digest(name + ":" + principal)
    body = digest(json.dumps(data, sort_keys=True, cls=DjangoJSONEncoder))
    with transaction.atomic():
        receipt, _ = CommandReceipt.objects.get_or_create(
            scope=scope, key_digest=digest(key), defaults={"body_digest": body}
        )
        receipt = CommandReceipt.objects.select_for_update().get(pk=receipt.pk)
        if receipt.body_digest != body:
            raise IdentityError("IDEMPOTENCY_CONFLICT", 409, "Idempotency key already used")
        if receipt.status:
            result = dict(receipt.response)
            if "correlation_id" in result:
                result["correlation_id"] = request.correlation_id
            return result, receipt.status
        result = handler()
        receipt.response, receipt.status = result, status
        receipt.save(update_fields=["response", "status"])
        return result, status
