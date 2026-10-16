"""Bootstrap only: no auth models, student APIs or external integrations."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env", override=False)


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value or value.startswith("replace-with-"):
        raise ImproperlyConfigured(f"Configure {name}; run make setup for local development.")
    return value


SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must have at least 50 characters.")

LOCAL = os.environ.get("MINHAAI_ENV") == "local"
DEBUG = False
ALLOWED_HOSTS = required("DJANGO_ALLOWED_HOSTS").split(",")
CSRF_TRUSTED_ORIGINS = required("DJANGO_CSRF_TRUSTED_ORIGINS").split(",")
if any("*" in value for value in ALLOWED_HOSTS + CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Wildcard hosts and origins are forbidden.")
if any(
    not origin.startswith("https://")
    and (not LOCAL or origin not in {"http://localhost:3000", "http://127.0.0.1:3000"})
    for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("CSRF origins require HTTPS except explicit local web origins.")

INSTALLED_APPS = ["django.contrib.sessions", "rest_framework", "drf_spectacular", "core"]
MIDDLEWARE = [
    "core.middleware.RequestMetadataMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.StrictCsrfMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
APPEND_SLASH = False
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required("POSTGRES_DB"),
        "USER": required("POSTGRES_USER"),
        "PASSWORD": required("POSTGRES_PASSWORD"),
        "HOST": required("POSTGRES_HOST"),
        "PORT": required("POSTGRES_PORT"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
    }
}
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "العربية"), ("en", "English")]
USE_I18N = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Same browser origin through the web rewrite. No CORS middleware or access grants.
# Only explicit local mode permits non-Secure cookies for loopback HTTP.
SESSION_COOKIE_NAME = "minhaai_session_local" if LOCAL else "__Host-minhaai_session"
CSRF_COOKIE_NAME = "minhaai_csrf_local" if LOCAL else "__Host-minhaai_csrf"
SESSION_COOKIE_SECURE = not LOCAL
CSRF_COOKIE_SECURE = not LOCAL
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_PATH = CSRF_COOKIE_PATH = "/"
SESSION_COOKIE_DOMAIN = CSRF_COOKIE_DOMAIN = None
SECURE_SSL_REDIRECT = not LOCAL
SECURE_HSTS_SECONDS = 0 if LOCAL else 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_FAILURE_VIEW = "core.errors.csrf_failure"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["core.permissions.DenyAll"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "core.errors.exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "MinhaAI implemented bootstrap API",
    "DESCRIPTION": "Phase 05 runtime surface only. Health is liveness, not dependency readiness.",
    "VERSION": "0.1.0",
    "OAS_VERSION": "3.1.0",
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_INCLUDE_SCHEMA": False,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "core.schema.strict_objects",
    ],
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"metadata": {"()": "core.middleware.MetadataFormatter"}},
    "handlers": {
        "metadata": {"class": "logging.StreamHandler", "formatter": "metadata"},
        "discard": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["discard"], "level": "WARNING"},
    "loggers": {
        "minhaai.http": {"handlers": ["metadata"], "level": "INFO", "propagate": False},
        # Default request/server logging can expose URL queries or exception contents.
        "django": {"handlers": ["discard"], "propagate": False},
        "django.server": {"handlers": ["discard"], "propagate": False},
    },
}
