import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from identity.models import Account, AuthIdentity, GoogleAuthorization
from identity.security import (
    IdentityError,
    adult,
    audit,
    digest,
    open_session,
    require_student,
    session_data,
)


def configuration() -> None:
    if any(
        not value or value.startswith("replace-with-")
        for value in (
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            settings.GOOGLE_REDIRECT_URI,
        )
    ):
        raise IdentityError("GOOGLE_UNAVAILABLE", 503, "Google account linking is not configured")
    uri = urlparse(settings.GOOGLE_REDIRECT_URI)
    origin = f"{uri.scheme}://{uri.netloc}"
    if (
        origin not in settings.CSRF_TRUSTED_ORIGINS
        or uri.username
        or uri.password
        or uri.fragment
        or uri.query
    ):
        raise IdentityError("GOOGLE_UNAVAILABLE", 503, "Google redirect configuration is invalid")


def start(request: Any, intent: str) -> dict[str, Any]:
    configuration()
    user = None
    if intent == "LINK":
        if not request.user.is_authenticated:
            raise IdentityError("AUTHENTICATION_REQUIRED", 401)
        require_student(request.user)
        reauth = request.session.get("reauthenticated_at")
        if not reauth or timezone.now() >= datetime.fromisoformat(reauth) + timedelta(minutes=5):
            raise IdentityError("REAUTHENTICATION_REQUIRED")
        user = request.user
        # One recent authentication authorizes one linking attempt.
        del request.session["reauthenticated_at"]
    if not request.session.session_key:
        request.session.create()
    state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
    expires = timezone.now() + timedelta(minutes=5)
    GoogleAuthorization.objects.create(
        state_digest=digest(state),
        session_digest=digest(request.session.session_key),
        account=user,
        intent=intent,
        expires_at=expires,
    )
    request.session["google_authorization"] = {
        "state": digest(state),
        "nonce": nonce,
        "verifier": verifier,
    }
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    audit(user, "google_authorization_started", correlation=request.correlation_id)
    return {"authorization_url": url, "expires_at": expires.isoformat()}


def exchange(code: str, verifier: str, nonce: str) -> dict[str, Any]:
    configuration()
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            timeout=5,
        )
        response.raise_for_status()
        claims = id_token.verify_oauth2_token(
            response.json()["id_token"], GoogleRequest(), settings.GOOGLE_CLIENT_ID
        )
        if (
            claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or claims.get("aud") != settings.GOOGLE_CLIENT_ID
            or claims.get("email_verified") is not True
            or not isinstance(claims.get("sub"), str)
            or not 1 <= len(claims["sub"]) <= 255
            or not hmac.compare_digest(str(claims.get("nonce", "")), nonce)
        ):
            raise ValueError("Invalid identity proof")
        return claims
    except Exception:
        raise IdentityError(
            "GOOGLE_VERIFICATION_FAILED", 400, "Google verification failed"
        ) from None


def callback(request: Any, code: str, state: str) -> dict[str, Any]:
    configuration()
    context = request.session.pop("google_authorization", None)
    if not context or not hmac.compare_digest(context["state"], digest(state)):
        raise IdentityError("INVALID_OAUTH_STATE", 400)
    # Consume state before network I/O: provider errors must not make it reusable.
    with transaction.atomic():
        authorization = (
            GoogleAuthorization.objects.select_for_update()
            .filter(state_digest=digest(state))
            .first()
        )
        if (
            not authorization
            or authorization.consumed_at
            or timezone.now() >= authorization.expires_at
            or authorization.session_digest != digest(request.session.session_key)
        ):
            raise IdentityError("INVALID_OAUTH_STATE", 400)
        authorization.consumed_at = timezone.now()
        authorization.save(update_fields=["consumed_at"])
    claims = exchange(code, context["verifier"], context["nonce"])
    with transaction.atomic():
        if authorization.intent == "LINK":
            if not request.user.is_authenticated or request.user.pk != authorization.account_id:
                raise IdentityError("ACCOUNT_LINK_DENIED")
            user = Account.objects.select_for_update().get(pk=authorization.account_id)
            require_student(user)
            try:
                with transaction.atomic():
                    AuthIdentity.objects.create(
                        account=user, provider="GOOGLE", subject=claims["sub"]
                    )
            except IntegrityError:
                raise IdentityError("IDENTITY_ALREADY_LINKED", 409) from None
        else:
            identity = AuthIdentity.objects.filter(provider="GOOGLE", subject=claims["sub"]).first()
            if identity is None:
                # A matching email alone never creates, activates, or merges an account.
                raise IdentityError(
                    "EXPLICIT_ACCOUNT_LINK_REQUIRED",
                    409,
                    "Sign in with email and link Google first",
                )
            user = Account.objects.select_for_update().get(pk=identity.account_id)
            if not user.email_verified_at or not user.is_active or not adult(user.birth_date):
                raise IdentityError("INVALID_CREDENTIALS", 401)
        proof = open_session(request, user)
        audit(user, "google_identity_verified", correlation=request.correlation_id)
        return session_data(user, proof)
