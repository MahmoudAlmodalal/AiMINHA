from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from catalog.views import PublicView
from django.test import RequestFactory, override_settings
from django.utils import timezone
from identity.security import IdentityError, digest, get_client_ip
from identity.services import sign_in
from identity.views import IdentityView


def make_request(remote_addr="127.0.0.1", forwarded_for=None):
    meta = {}
    if remote_addr is not None:
        meta["REMOTE_ADDR"] = remote_addr
    if forwarded_for is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded_for
    request = RequestFactory().get("/test")
    request.META = meta
    return request


def test_untrusted_remote_addr_ignores_forwarded_for():
    request = make_request(remote_addr="198.51.100.5", forwarded_for="203.0.113.10")
    assert get_client_ip(request) == "198.51.100.5"


def test_trusted_loopback_extracts_client_ip():
    request_v4 = make_request(remote_addr="127.0.0.1", forwarded_for="203.0.113.10")
    assert get_client_ip(request_v4) == "203.0.113.10"

    request_v6 = make_request(remote_addr="::1", forwarded_for="203.0.113.11")
    assert get_client_ip(request_v6) == "203.0.113.11"


@override_settings(TRUSTED_PROXIES=["10.0.0.1", "10.0.0.2"])
def test_configured_trusted_proxies_allow_forwarding():
    request = make_request(remote_addr="10.0.0.1", forwarded_for="198.51.100.20")
    assert get_client_ip(request) == "198.51.100.20"


@override_settings(TRUSTED_PROXIES=["10.0.0.1"])
def test_chained_proxies_extracts_rightmost_untrusted():
    # Chain: spoofed_ip -> real_client (203.0.113.10)
    # -> trusted proxy (10.0.0.1) -> ingress (127.0.0.1)
    request = make_request(
        remote_addr="127.0.0.1",
        forwarded_for="1.2.3.4, 203.0.113.10, 10.0.0.1",
    )
    assert get_client_ip(request) == "203.0.113.10"


@override_settings(TRUSTED_PROXIES=["10.0.0.1"])
def test_all_trusted_forwarding_chain_falls_back_to_remote_addr():
    request = make_request(remote_addr="127.0.0.1", forwarded_for="10.0.0.1, 127.0.0.1")
    assert get_client_ip(request) == "127.0.0.1"


def test_trusted_proxy_without_forwarded_for_returns_remote_addr():
    request = make_request(remote_addr="127.0.0.1", forwarded_for=None)
    assert get_client_ip(request) == "127.0.0.1"


def test_missing_remote_addr_returns_unknown():
    request = make_request(remote_addr=None, forwarded_for="203.0.113.10")
    assert get_client_ip(request) == "unknown"


def test_identity_view_limit_resolves_client_ip():
    view = IdentityView()

    # Case 1: Untrusted client with spoofed header
    req_untrusted = make_request(remote_addr="198.51.100.5", forwarded_for="203.0.113.10")
    view.request = req_untrusted
    with patch("identity.views.throttle") as mock_throttle:
        view.limit("login", "user@example.invalid")
        mock_throttle.assert_any_call("login:ip", "198.51.100.5")
        mock_throttle.assert_any_call("login:identity", "user@example.invalid")

    # Case 2: Trusted ingress with forwarded client
    req_trusted = make_request(remote_addr="127.0.0.1", forwarded_for="203.0.113.10")
    view.request = req_trusted
    with patch("identity.views.throttle") as mock_throttle:
        view.limit("login", "user@example.invalid")
        mock_throttle.assert_any_call("login:ip", "203.0.113.10")


@override_settings(TRUSTED_PROXIES=["10.0.0.1"])
def test_public_view_initial_resolves_client_ip():
    view = PublicView()

    # Case 1: Untrusted client with spoofed header
    req_untrusted = view.initialize_request(
        make_request(remote_addr="198.51.100.5", forwarded_for="203.0.113.10")
    )
    mock_bucket = MagicMock(attempts=1, window_started=timezone.now())
    with (
        patch(
            "identity.models.RateBucket.objects.get_or_create",
            return_value=(mock_bucket, False),
        ) as mock_goc,
        patch("identity.models.RateBucket.objects.select_for_update") as mock_sfu,
        patch("django.db.transaction.atomic"),
    ):
        mock_sfu.return_value.get.return_value = mock_bucket
        view.initial(req_untrusted)
        mock_goc.assert_called_once_with(key=digest("public_catalog:198.51.100.5"))

    # Case 2: Trusted ingress with chained proxies
    req_trusted = view.initialize_request(
        make_request(remote_addr="127.0.0.1", forwarded_for="spoofed, 203.0.113.50, 10.0.0.1")
    )
    mock_bucket2 = MagicMock(attempts=1, window_started=timezone.now())
    with (
        patch(
            "identity.models.RateBucket.objects.get_or_create",
            return_value=(mock_bucket2, False),
        ) as mock_goc,
        patch("identity.models.RateBucket.objects.select_for_update") as mock_sfu,
        patch("django.db.transaction.atomic"),
    ):
        mock_sfu.return_value.get.return_value = mock_bucket2
        view.initial(req_trusted)
        mock_goc.assert_called_once_with(key=digest("public_catalog:203.0.113.50"))


def test_failed_sign_in_conceals_account_membership_and_triggers_hashing():
    dummy_request = SimpleNamespace(correlation_id=str(uuid4()))
    credentials = {"email": "test@example.invalid", "password": "SecretPassword123!"}
    fn = getattr(sign_in, "__wrapped__", sign_in)

    # Path 1: Unknown account triggers make_password
    mock_qs = MagicMock()
    mock_qs.select_for_update.return_value.filter.return_value.first.return_value = None
    with (
        patch("identity.models.Account.objects", mock_qs),
        patch("identity.services.make_password") as mock_make_pw,
    ):
        with pytest.raises(IdentityError) as exc_unknown:
            fn(dummy_request, credentials)
        mock_make_pw.assert_called_once_with("SecretPassword123!")

    # Path 2: Existing account with wrong password triggers check_password
    mock_user = MagicMock()
    mock_user.check_password.return_value = False
    mock_qs.select_for_update.return_value.filter.return_value.first.return_value = mock_user
    with patch("identity.models.Account.objects", mock_qs):
        with pytest.raises(IdentityError) as exc_existing:
            fn(dummy_request, credentials)
        mock_user.check_password.assert_called_once_with("SecretPassword123!")

    # Both paths return identical status code (401),
    # code (INVALID_CREDENTIALS), and detail (Sign in failed)
    assert exc_unknown.value.status_code == 401
    assert exc_existing.value.status_code == 401
    assert exc_unknown.value.code == "INVALID_CREDENTIALS"
    assert exc_existing.value.code == "INVALID_CREDENTIALS"
    assert exc_unknown.value.safe_title == "Sign in failed"
    assert exc_existing.value.safe_title == "Sign in failed"
