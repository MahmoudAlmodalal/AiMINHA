import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from config.urls import urlpatterns as runtime_urls
from core.errors import ProblemSerializer
from core.middleware import MetadataFormatter
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.test import Client, override_settings
from django.urls import path
from jsonschema import Draft202012Validator, FormatChecker
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = json.loads((ROOT / "docs/architecture/openapi.json").read_text())["components"][
    "schemas"
]["Problem"]
effects = []


def csrf_token(request):
    return JsonResponse({"token": get_token(request)})


class UnsafeProbe(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        effects.append("changed")
        return Response({"accepted": True})


class CrashProbe(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("sensitive-content-marker")


class ClosedProbe(APIView):
    def get(self, request):
        return Response({"should_never_be_returned": True})


urlpatterns = runtime_urls + [
    path("test/csrf", csrf_token),
    path("test/unsafe", UnsafeProbe.as_view()),
    path("test/crash", CrashProbe.as_view()),
    path("test/closed", ClosedProbe.as_view()),
]
handler400 = "core.errors.bad_request"
handler403 = "core.errors.forbidden"
handler404 = "core.errors.not_found"
handler500 = "core.errors.server_error"


@pytest.fixture(autouse=True)
def local_test_settings(settings):
    settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
    effects.clear()


def assert_problem(response, status, code):
    assert response.status_code == status
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json()
    Draft202012Validator(PROBLEM, format_checker=FormatChecker()).validate(body)
    assert ProblemSerializer(data=body).is_valid()
    assert body["status"] == status and body["code"] == code
    UUID(body["correlation_id"])
    assert response.headers["X-Correlation-ID"] == body["correlation_id"]
    return body


def test_public_liveness_has_no_dependencies_or_secrets(client):
    response = client.get("/api/v1/health", HTTP_X_CORRELATION_ID="untrusted-value")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["X-Correlation-ID"])
    assert response.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in response.headers
    assert not response.cookies
    assert client.head("/api/v1/health").content == b""


def test_foreign_origin_receives_no_cors_grant(client):
    response = client.get("/api/v1/health", HTTP_ORIGIN="https://foreign.invalid")
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_unrecognized_host_fails_closed(client):
    assert_problem(
        client.get("/api/v1/health", HTTP_HOST="foreign.invalid"), 400, "INVALID_REQUEST"
    )


def test_unknown_path_returns_problem_without_url_or_query(client):
    response = client.get("/api/v1/missing?content=sensitive-content-marker")
    body = assert_problem(response, 404, "NOT_FOUND")
    assert "sensitive-content-marker" not in response.content.decode()
    assert response.headers["X-Correlation-ID"] == body["correlation_id"]


@override_settings(ROOT_URLCONF=__name__)
def test_new_endpoint_defaults_to_denied(client):
    assert_problem(client.get("/test/closed"), 403, "FORBIDDEN")


@override_settings(ROOT_URLCONF=__name__)
def test_unexpected_error_is_redacted(client):
    response = client.get("/test/crash")
    assert_problem(response, 500, "INTERNAL_ERROR")
    assert "sensitive-content-marker" not in response.content.decode()


@override_settings(ROOT_URLCONF=__name__)
def test_anonymous_unsafe_drf_request_requires_csrf():
    client = Client(enforce_csrf_checks=True)
    assert_problem(
        client.post("/test/unsafe", {}, content_type="application/json"), 403, "CSRF_FAILED"
    )
    assert effects == []


@override_settings(ROOT_URLCONF=__name__)
def test_valid_token_still_rejects_foreign_origin_then_accepts_same_origin():
    client = Client(enforce_csrf_checks=True)
    token = client.get("/test/csrf").json()["token"]
    assert_problem(
        client.post(
            "/test/unsafe",
            {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://foreign.invalid",
        ),
        403,
        "CSRF_FAILED",
    )
    assert effects == []
    response = client.post(
        "/test/unsafe",
        {},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="http://testserver",
    )
    assert response.status_code == 200 and effects == ["changed"]


@override_settings(ROOT_URLCONF=__name__)
def test_https_unsafe_request_without_origin_or_referer_is_denied():
    client = Client(enforce_csrf_checks=True)
    token = client.get("/test/csrf", secure=True).json()["token"]
    response = client.post("/test/unsafe", {}, secure=True, HTTP_X_CSRFTOKEN=token)
    assert_problem(response, 403, "CSRF_FAILED")
    assert effects == []


def test_safe_method_error_is_structured(client):
    assert_problem(client.delete("/api/v1/health"), 405, "METHOD_NOT_ALLOWED")


def test_metadata_formatter_ignores_exception_message_and_extra_content():
    record = logging.LogRecord("test", logging.ERROR, "", 0, "sensitive-content-marker", (), None)
    record.correlation_id = "correlation"
    record.status = 500
    record.body = "private-input"
    assert json.loads(MetadataFormatter().format(record)) == {
        "event": "http_request",
        "correlation_id": "correlation",
        "status": 500,
        "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
    }


@pytest.mark.django_db
def test_real_postgresql_session_roundtrip_without_premature_auth_tables():
    assert connection.vendor == "postgresql"
    session = SessionStore()
    session["bootstrap_probe"] = True
    session.save()
    assert SessionStore(session_key=session.session_key)["bootstrap_probe"] is True
    assert "django_session" in connection.introspection.table_names()
    assert "auth_user" not in connection.introspection.table_names()


@pytest.mark.django_db
def test_worker_preflight_uses_database_but_execution_remains_disabled():
    call_command("worker", check=True)
    with pytest.raises(CommandError, match="execution disabled"):
        call_command("worker")


def test_local_cookie_exception_is_explicit_and_http_only():
    assert settings.LOCAL
    assert not settings.SESSION_COOKIE_SECURE and not settings.CSRF_COOKIE_SECURE
    assert settings.SESSION_COOKIE_HTTPONLY and settings.CSRF_COOKIE_HTTPONLY
    assert not settings.DEBUG
