import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def import_settings(**overrides):
    environment = os.environ.copy()
    environment.update(overrides)
    return subprocess.run(  # noqa: S603 -- fixed local interpreter and source.
        [
            sys.executable,
            "-c",
            "import config.settings as s; "
            "assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; "
            "assert s.SESSION_COOKIE_NAME.startswith('__Host-'); "
            "assert s.CSRF_COOKIE_NAME.startswith('__Host-'); "
            "assert s.SECURE_SSL_REDIRECT; assert not s.DEBUG",
        ],
        cwd=ROOT / "apps/api",
        env=environment,
        capture_output=True,
        text=True,
    )


def test_nonlocal_mode_uses_secure_cookies_and_redirects():
    result = import_settings(
        MINHAAI_ENV="secure",
        DJANGO_ALLOWED_HOSTS="app.example.invalid",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://app.example.invalid",
    )
    assert result.returncode == 0


def test_nonlocal_mode_rejects_local_http_origin():
    result = import_settings(
        MINHAAI_ENV="secure",
        DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:3000",
    )
    assert result.returncode != 0
    assert "CSRF origins require HTTPS" in result.stderr


def test_wildcard_origin_and_host_are_rejected():
    result = import_settings(DJANGO_ALLOWED_HOSTS="*")
    assert result.returncode != 0
    assert "Wildcard hosts and origins" in result.stderr


def test_placeholder_secret_fails_closed():
    result = import_settings(
        DJANGO_SECRET_KEY="replace-with-generated-local-secret",  # noqa: S106 -- rejected fixture.
    )
    assert result.returncode != 0
    assert "Configure DJANGO_SECRET_KEY" in result.stderr
