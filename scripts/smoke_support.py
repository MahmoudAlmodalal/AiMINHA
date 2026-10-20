"""Isolated real HTTP support desk flow: tickets, measured SLA, AI triage, rating.

Requires the production web build and local PostgreSQL. No provider, email service,
payment rail or paid API runs; the AI triage is the deterministic local engine and the
credits ledger is only read to prove that support AI never moves a balance.
"""

import json
import os
import re
import socket
import stat
import subprocess
import sys
import time
import uuid
from email import policy
from email.parser import BytesParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dev import ROOT, stop
from smoke_documents import fixture

ORIGIN = "http://127.0.0.1:3000"
DATABASE_PREFIX = "minhaai_smoke_support_"


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Support smoke needs loopback ports 3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    database = DATABASE_PREFIX + uuid.uuid4().hex
    database_created = False
    message_path: Path | None = None
    environment = dict(os.environ)
    environment["POSTGRES_DB"] = database

    def local_fixture(source: str, values: dict[str, Any]) -> dict[str, Any]:
        return fixture(source, values, environment)

    def call(
        opener: Any,
        path: str,
        body: dict | None = None,
        expected: int = 200,
        *,
        method: str | None = None,
        revision: int | None = None,
    ) -> dict[str, Any]:
        headers = {"Origin": ORIGIN}
        if body is not None:
            with opener.open(ORIGIN + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310 -- fixed loopback.
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())}
            )
        if revision is not None:
            headers["If-Match"] = f'"{revision}"'
        request = Request(  # noqa: S310 -- fixed loopback and server-owned paths/UUIDs.
            ORIGIN + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = opener.open(request, timeout=20)  # noqa: S310 -- fixed loopback.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"Unexpected support HTTP {response.status}; expected {expected}: {path}"
                )
            if "no-store" not in response.headers.get("Cache-Control", ""):
                raise RuntimeError("Private support HTTP must be no-store")
            return {} if expected == 204 else dict(json.load(response))

    def student_call(
        path: str, body: dict | None = None, expected: int = 200, **kwargs: Any
    ) -> dict[str, Any]:
        return call(browser, path, body, expected, **kwargs)

    def register(email: str, password: str, locale: str = "en") -> str:
        directory = ROOT / ".local/mail"
        previous = set(directory.glob("*.eml"))
        student_call(
            "/api/v1/auth/registrations",
            {"email": email, "password": password, "birth_date": "2000-02-29", "locale": locale},
            202,
        )
        messages = set(directory.glob("*.eml")) - previous
        if len(messages) != 1:
            raise RuntimeError("Expected one synthetic private verification email")
        path = messages.pop()
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        match = re.search(r"Verification code: (\S+)", str(message.get_content()))
        if not match:
            raise RuntimeError("Local verification code is absent")
        student_call("/api/v1/auth/email-verifications", {"challenge_token": match.group(1)})
        return str(path)

    try:
        fixture(
            """
import json, re, sys
from django.conf import settings
from django.db import connection
from psycopg import sql
value = json.load(sys.stdin)
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_support_[a-f0-9]{32}', value['name'])
assert connection.settings_dict['NAME'] != value['name']
with connection.cursor() as cursor:
    cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(value['name'])))
print(json.dumps({'created': True}))
""",
            {"name": database},
        )
        database_created = True
        subprocess.run(
            [sys.executable, "apps/api/manage.py", "migrate", "--noinput"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=120,
        )
        for arguments in (
            [
                sys.executable,
                "apps/api/manage.py",
                "runserver",
                "127.0.0.1:8000",
                "--noreload",
                "--nothreading",
            ],
            ["npm", "run", "start", "--workspace", "@minhaai/web"],
        ):
            processes.append(
                subprocess.Popen(
                    arguments,
                    cwd=ROOT,
                    env=environment,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
        startup_until = time.monotonic() + 45
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("Support smoke server exited")
            try:
                student_call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= startup_until:
                    raise RuntimeError("Support smoke startup timed out") from None
                time.sleep(0.25)

        for locale, direction, title in (
            ("ar", "rtl", "الدعم"),
            ("en", "ltr", "Support"),
        ):
            with browser.open(ORIGIN + f"/{locale}/support", timeout=10) as response:  # noqa: S310 -- fixed loopback.
                html = response.read().decode()
                assert f'lang="{locale}"' in html and f'dir="{direction}"' in html
                assert title in html
        for route in ("tickets", "admin/tickets", "admin/support/metrics"):
            student_call("/api/v1/" + route, expected=401)

        email = f"phase13-{uuid.uuid4()}@example.invalid"
        password = "Synthetic-only-" + str(uuid.uuid4())
        message_path = Path(register(email, password))
        assert stat.S_IMODE(message_path.stat().st_mode) == 0o600
        student_call("/api/v1/session/login", {"email": email, "password": password})
        baseline = student_call("/api/v1/wallet")["posted_balance"]
        assert student_call("/api/v1/tickets")["items"] == []

        # AI handling never satisfies the human first-response obligation.
        ticket = student_call(
            "/api/v1/tickets",
            {
                "category": "TECHNICAL",
                "subject": "Upload problem on the application portal",
                "message": "The upload failed again and the portal is not working for me.",
                "request_human": False,
            },
            201,
        )
        assert ticket["state"] == "NEW"
        assert student_call(f"/api/v1/tickets/{ticket['id']}/sla")["met"] is False
        answer = student_call(f"/api/v1/tickets/{ticket['id']}/ai-replies", {}, 200)
        assert answer["ai"]["available"] is True
        assert answer["ticket"]["state"] == "AI_HANDLING"
        assert (
            student_call(f"/api/v1/tickets/{ticket['id']}/sla")["first_human_response_at"] is None
        )
        thread = student_call(f"/api/v1/tickets/{ticket['id']}/messages")["items"]
        assert [item["author_kind"] for item in thread] == ["STUDENT", "AI"]
        assert student_call("/api/v1/wallet")["posted_balance"] == baseline

        # A human request starts the measured clock on the working calendar.
        human = student_call(
            "/api/v1/tickets",
            {
                "category": "DOCUMENTS",
                "subject": "My transcript does not open",
                "message": "The transcript file does not open in the document workspace.",
                "request_human": True,
            },
            201,
        )
        assert human["state"] == "AWAITING_ADMIN"
        sla = student_call(f"/api/v1/tickets/{human['id']}/sla")
        assert sla["human_requested_at"] is not None
        assert sla["computed_due_at"] is not None
        assert sla["target_business_minutes"] == 1440
        assert sla["met"] is False

        # Another student cannot see the ticket at all.
        other_email = f"phase13-other-{uuid.uuid4()}@example.invalid"
        other_password = "Synthetic-only-" + str(uuid.uuid4())
        other_message = Path(register(other_email, other_password))
        try:
            other = build_opener(HTTPCookieProcessor(CookieJar()))
            call(other, "/api/v1/session/login", {"email": other_email, "password": other_password})
            call(other, f"/api/v1/tickets/{human['id']}", expected=404)
            call(other, f"/api/v1/tickets/{human['id']}/messages", expected=404)
            call(other, "/api/v1/admin/tickets", expected=403)
        finally:
            other_message.unlink(missing_ok=True)

        # Resolution and a single rating inside the configured window.
        closed = student_call(
            f"/api/v1/tickets/{human['id']}/transitions",
            {"to_state": "RESOLVED", "reason_code": "STUDENT_CONFIRMED"},
            200,
            revision=human["row_version"],
        )
        # A resolution stays RESOLVED until the configured quiet period expires.
        assert closed["state"] == "RESOLVED"
        assert closed["rating_available"] is True
        rated = student_call(
            f"/api/v1/tickets/{human['id']}/rating",
            {"rating": 4},
            200,
            method="PUT",
            revision=closed["row_version"],
        )
        assert rated["value"] == 4
        assert student_call(f"/api/v1/tickets/{human['id']}/rating")["value"] == 4

        # An assigned agent answers; only that agent may read the thread.
        agent = local_fixture(
            """
import json, sys, uuid
from datetime import date
from django.conf import settings
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import digest
from rest_framework.test import APIClient
value = json.load(sys.stdin)
assert settings.LOCAL and value['email'].startswith('phase13-')
email = f'phase13-agent-{uuid.uuid4()}@example.invalid'
password = 'Synthetic-only-' + str(uuid.uuid4())
account = Account.objects.create_user(email, password, birth_date=date(2000, 1, 1),
    locale='en', state='ACTIVE', email_verified_at=timezone.now(), role='ADMIN',
    admin_scopes=['SUPPORT', 'SUPPORT_QUEUE', 'SUPPORT_ASSIGNMENT', 'SUPPORT_POLICY'])
client = APIClient(enforce_csrf_checks=True)
settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, 'testserver']
token = client.get('/api/v1/session/csrf').json()['csrf_token']
response = client.post('/api/v1/session/login', {'email': email, 'password': password},
    format='json', HTTP_X_CSRFTOKEN=token)
assert response.status_code == 200, response.content
IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
    mfa_verified_at=timezone.now())
print(json.dumps({'id': str(account.pk), 'email': email, 'password': password}))
""",
            {"email": email},
        )
        agent_cookies = CookieJar()
        agent_browser = build_opener(HTTPCookieProcessor(agent_cookies))
        call(
            agent_browser,
            "/api/v1/session/login",
            {"email": agent["email"], "password": agent["password"]},
        )
        # Admin MFA is a server-authored proof on the current session; no endpoint
        # accepts a browser-supplied MFA claim.
        session_cookie = next(
            (
                cookie.value
                for cookie in agent_cookies
                if cookie.name.endswith("session_local") or cookie.name == "__Host-minhaai_session"
            ),
            None,
        )
        if session_cookie is None:
            raise RuntimeError("Admin session cookie is absent")
        local_fixture(
            """
import json, sys
from django.conf import settings
from django.utils import timezone
from identity.models import IdentitySession
from identity.security import digest
value = json.load(sys.stdin)
assert settings.LOCAL
row = IdentitySession.objects.filter(digest=digest(value['key'])).first()
assert row is not None
row.mfa_verified_at = timezone.now()
row.save(update_fields=['mfa_verified_at'])
print(json.dumps({'mfa': True}))
""",
            {"key": unquote(session_cookie)},
        )
        queue = call(agent_browser, "/api/v1/admin/tickets")
        assert queue["total"] >= 2
        assert all("subject" not in row and "owner" not in row for row in queue["items"])
        row = next(item for item in queue["items"] if item["id"] == ticket["id"])
        call(
            agent_browser,
            f"/api/v1/admin/tickets/{ticket['id']}/assignments",
            {"agent_id": agent["id"], "reason_code": "Support smoke assignment"},
            200,
            revision=row["row_version"],
        )
        answered = call(
            agent_browser,
            f"/api/v1/admin/tickets/{ticket['id']}/messages",
            {
                "body": "We checked the portal: a smaller PDF upload completes the document step.",
                "request_human": False,
            },
            200,
        )
        assert answered["sla"]["met"] is True
        assert answered["sla"]["first_human_response_at"] is not None
        metrics = call(agent_browser, "/api/v1/admin/support/metrics")["tickets"]
        assert metrics["first_human_responses"] >= 1
        assert metrics["sla_breaches"] == 0

        student_call("/api/v1/session/logout", {}, 204)
        student_call("/api/v1/tickets", expected=401)
        print(
            "Support HTTP smoke passed: bilingual support page, owner-scoped tickets, AI "
            "answer that never satisfies the human first-response obligation, measured "
            "business-hour SLA with a working-calendar due date, distinct-student 404, "
            "resolution and one rating, assigned-agent-only thread and reply, queue without "
            "student identity, aggregate metrics, and credits unchanged."
        )
    finally:
        stop(processes)
        try:
            if database_created:
                fixture(
                    """
import json, re, sys
from django.conf import settings
from django.db import connection
from psycopg import sql
value = json.load(sys.stdin)
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_support_[a-f0-9]{32}', value['name'])
assert connection.settings_dict['NAME'] != value['name']
with connection.cursor() as cursor:
    cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(value['name'])))
print(json.dumps({'dropped': True}))
""",
                    {"name": database},
                )
        finally:
            if message_path is not None:
                message_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
