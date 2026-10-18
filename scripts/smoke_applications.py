"""Isolated real HTTP tracker/inbox flow using authored synthetic source evidence.

Requires the production web build and local PostgreSQL. The deadline worker uses
the real server clock; no provider, sponsor website, email service or paid API runs.
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
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dev import ROOT, stop
from smoke_documents import fixture


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Application smoke needs loopback ports3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    origin = "http://127.0.0.1:3000"
    database = "minhaai_smoke_applications_" + uuid.uuid4().hex
    database_created = False
    message_path: Path | None = None
    environment = dict(os.environ)
    environment["POSTGRES_DB"] = database

    def local_fixture(source: str, values: dict[str, Any]) -> dict[str, Any]:
        return fixture(source, values, environment)

    def command(*arguments: str) -> dict[str, Any]:
        result = subprocess.run(
            [sys.executable, "apps/api/manage.py", *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            check=True,
            timeout=60,
        )
        return dict(json.loads(result.stdout.splitlines()[-1]))

    def call(
        path: str,
        body: dict | None = None,
        expected: int = 200,
        *,
        method: str | None = None,
        revision: int | None = None,
        key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Origin": origin}
        if body is not None:
            with browser.open(origin + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310 -- fixed loopback.
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": key or str(uuid.uuid4())}
            )
        if revision is not None:
            headers["If-Match"] = f'"{revision}"'
        request = Request(  # noqa: S310 -- fixed loopback and server-owned paths/UUIDs.
            origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = browser.open(request, timeout=20)  # noqa: S310 -- fixed loopback.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"Unexpected tracker HTTP {response.status}; expected {expected}: {path}"
                )
            if "no-store" not in response.headers.get("Cache-Control", ""):
                raise RuntimeError("Private tracker/inbox HTTP must be no-store")
            return {} if expected == 204 else dict(json.load(response))

    def transition(value: dict, target: str, *, confirm: bool = False, expected: int = 200) -> dict:
        return call(
            f"/api/v1/applications/{value['id']}/transitions",
            {
                "to_state": target,
                "observed_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                "evidence": "Synthetic student report of external portal; no official claim.",
                "confirm_external_submission": confirm,
            },
            expected,
            revision=value["revision"],
        )

    try:
        fixture(
            """
import json, re, sys
from django.conf import settings
from django.db import connection
from psycopg import sql
value = json.load(sys.stdin)
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_applications_[a-f0-9]{32}', value['name'])
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
            timeout=60,
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
                raise RuntimeError("Application smoke server exited")
            try:
                call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= startup_until:
                    raise RuntimeError("Application smoke startup timed out") from None
                time.sleep(0.25)
        for locale, direction, titles in (
            ("ar", "rtl", ("طلباتي والمنح المحفوظة", "الإشعارات")),
            ("en", "ltr", ("My applications and saved scholarships", "Notifications")),
        ):
            for route, title in zip(("applications", "notifications"), titles, strict=True):
                with browser.open(origin + f"/{locale}/{route}", timeout=10) as response:  # noqa: S310 -- fixed loopback.
                    html = response.read().decode()
                    assert f'lang="{locale}"' in html and f'dir="{direction}"' in html
                    assert title in html
        for route in ("applications", "notifications", "notification-preferences"):
            call("/api/v1/" + route, expected=401)

        directory = ROOT / ".local/mail"
        previous = set(directory.glob("*.eml"))
        email = f"phase12-{uuid.uuid4()}@example.invalid"
        password = "Synthetic-only-" + str(uuid.uuid4())
        call(
            "/api/v1/auth/registrations",
            {"email": email, "password": password, "birth_date": "2000-02-29", "locale": "en"},
            202,
        )
        messages = set(directory.glob("*.eml")) - previous
        if len(messages) != 1:
            raise RuntimeError("Expected one synthetic private verification email")
        message_path = messages.pop()
        assert stat.S_IMODE(message_path.stat().st_mode) == 0o600
        message = BytesParser(policy=policy.default).parsebytes(message_path.read_bytes())
        match = re.search(r"Verification code: (\S+)", str(message.get_content()))
        if not match:
            raise RuntimeError("Local verification code is absent")
        call("/api/v1/session/login", {"email": email, "password": password}, 401)
        call("/api/v1/auth/email-verifications", {"challenge_token": match.group(1)})
        session = call("/api/v1/session/login", {"email": email, "password": password})
        baseline = call("/api/v1/wallet")
        assert call("/api/v1/applications")["items"] == []
        preferences = call("/api/v1/notification-preferences")
        preferences = call(
            "/api/v1/notification-preferences",
            {
                "timezone": "Asia/Kathmandu",
                "deadline_enabled": True,
                "source_enabled": True,
                "document_enabled": True,
            },
            method="PUT",
            revision=preferences["revision"],
        )
        assert preferences["timezone"] == "Asia/Kathmandu"

        # Fixed local fixture builds reviewed source evidence through existing APIs.
        # MFA is a server-authored synthetic proof, never a browser-supplied claim.
        catalog = local_fixture(
            """
import json, sys, uuid
from datetime import UTC, date, timedelta
from django.conf import settings
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import digest
from rest_framework.test import APIClient
value = json.load(sys.stdin)
assert settings.LOCAL and value['email'].startswith('phase12-')
assert value['email'].endswith('@example.invalid')
assert Account.objects.get(pk=value['id'], email=value['email']).state == 'ACTIVE'
settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, 'testserver']
admin_email = f'phase12-admin-{uuid.uuid4()}@example.invalid'
admin_password = 'Synthetic-only-' + str(uuid.uuid4())
admin = Account.objects.create_user(admin_email, admin_password, birth_date=date(2000, 1, 1),
    locale='en', state='ACTIVE', email_verified_at=timezone.now(), role='ADMIN',
    admin_scopes=['MODERATION', 'SOURCE_APPROVAL'])
client = APIClient(enforce_csrf_checks=True)
def post(path, body, status=200, revision=None):
    token = client.get('/api/v1/session/csrf').json()['csrf_token']
    headers = {'HTTP_X_CSRFTOKEN': token, 'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
    if revision is not None:
        headers['HTTP_IF_MATCH'] = f'"{revision}"'
    response = client.post('/api/v1/' + path, body, format='json', **headers)
    assert response.status_code == status, (path, response.status_code, response.content)
    return response.json()
post('session/login', {'email': admin_email, 'password': admin_password})
IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
    mfa_verified_at=timezone.now())
now = timezone.now()
source = post('admin/sources', {
    'name': 'Authored Phase12 synthetic source',
    'url': 'https://fixtures.example.invalid/phase12',
    'permission_status': 'APPROVED', 'license_basis': 'Original authored synthetic fixture.',
    'permission_evidence': 'Synthetic authorization only; no external site accessed.',
    'date_checked': now.isoformat(), 'valid_until': (now + timedelta(days=90)).isoformat(),
    'allow_manual': True, 'allow_import': False, 'freshness_days': 30,
    'reason': 'Synthetic source fixture.'}, 201)
closes = now + timedelta(days=1, seconds=20)
candidate = post('admin/scholarships', {
    'source_id': source['id'], 'title': 'Authored Phase12 synthetic scholarship',
    'provider': 'Synthetic university', 'summary': 'Not a real scholarship.',
    'education_levels': ['MASTER'], 'disciplines': ['engineering'], 'countries': ['PS'],
    'languages': ['en'], 'funding': 'PARTIAL', 'criteria': ['Synthetic criterion.'],
    'required_documents': ['Synthetic CV'],
    'submission_url': 'https://fixtures.example.invalid/apply',
    'rounds': [{'kind': 'CONFIRMED', 'label': 'Synthetic confirmed round',
        'closes_at': closes.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
        'timezone': 'Asia/Hebron', 'source_text': 'Authored exact synthetic closing instant.'},
        {'kind': 'UNKNOWN', 'label': 'Synthetic unknown next round'}],
    'source_checked_at': now.isoformat(), 'internal_notes': '', 'origin': 'MANUAL',
    'reason': 'Authored synthetic candidate.'}, 201)
published = post(f"admin/scholarships/{candidate['id']}/moderation", {
    'version_id': candidate['latest']['id'], 'action': 'APPROVE',
    'reason': 'Synthetic exact-version human decision.'}, revision=candidate['revision'])
other_email = f'phase12-other-{uuid.uuid4()}@example.invalid'
other_password = 'Synthetic-only-' + str(uuid.uuid4())
Account.objects.create_user(other_email, other_password, birth_date=date(2000, 1, 1),
    locale='en', state='ACTIVE', email_verified_at=timezone.now())
print(json.dumps({'id': published['id'], 'other_email': other_email,
    'other_password': other_password, 'admin_email': admin_email,
    'admin_password': admin_password, 'due_at': (closes - timedelta(days=1)).isoformat()}))
""",
            {"id": session["actor_id"], "email": email},
        )
        scholarship_id = catalog["id"]
        call("/api/v1/saved-scholarships", {"scholarship_id": scholarship_id})
        initial_worker = command("process_deadline_reminders")
        assert initial_worker["delivered"] == 0
        schedules = local_fixture(
            """
import json, sys
from django.conf import settings
from notifications.models import DeadlineReminder
value = json.load(sys.stdin)
assert settings.LOCAL
rows = list(DeadlineReminder.objects.filter(owner_id=value['owner_id']).values(
    'offset_minutes', 'event__round_key', 'due_at'))
assert len(rows) == 1 and rows[0]['offset_minutes'] == 1440
print(json.dumps({'round_key': rows[0]['event__round_key']}))
""",
            {"owner_id": session["actor_id"]},
        )
        options = call("/api/v1/applications/round-options?scholarship_id=" + scholarship_id)
        confirmed = next(row for row in options["items"] if row["kind"] == "CONFIRMED")
        unknown = next(row for row in options["items"] if row["kind"] == "UNKNOWN")
        assert schedules["round_key"] == confirmed["round_key"]
        creation = {"scholarship_id": scholarship_id, "round_key": confirmed["round_key"]}
        key = str(uuid.uuid4())
        application = call("/api/v1/applications", creation, 201, key=key)
        assert call("/api/v1/applications", creation, 201, key=key) == application
        call("/api/v1/applications", creation, 409)
        assert application["state"] == "PREPARING" and application["missing_count"] == 1
        assert application["deadline"]["eligible"] is True
        assert application["deadline"]["source_timezone"] == "Asia/Hebron"
        assert application["deadline"]["display_timezone"] == "Asia/Kathmandu"
        assert not application["official_integration_available"]
        assert application["official_reports"] == []
        app_path = "/api/v1/applications/" + application["id"]
        application = call(
            app_path + "/notes",
            {"notes": "Synthetic owner note; external submission remains the student's job."},
            method="PUT",
            revision=application["revision"],
        )
        transition(application, "READY", expected=409)
        document = call(
            "/api/v1/documents",
            {
                "kind": "CV",
                "title": "Synthetic Phase12 CV",
                "language": "en",
                "content": "Original synthetic application CV.",
            },
            201,
        )
        original = document["current"]
        call(
            f"/api/v1/documents/{document['id']}/approvals",
            {
                "version_id": original["id"],
                "content_hash": original["content_hash"],
                "confirm": True,
            },
        )
        requirement_key = application["requirements"][0]["key"]
        application = call(
            app_path + "/requirements/" + requirement_key + "/artifact",
            {"version_id": original["id"], "content_hash": original["content_hash"]},
            method="PUT",
            revision=application["revision"],
        )
        assert application["missing_count"] == 0
        application = transition(application, "READY")
        transition(application, "SUBMITTED", expected=409)
        application = transition(application, "SUBMITTED", confirm=True)
        snapshots = call(app_path + "/submitted-artifacts")["items"]
        assert len(snapshots) == 1 and snapshots[0]["content_hash"] == original["content_hash"]
        edited = call(
            f"/api/v1/documents/{document['id']}/versions",
            {"title": "Edited master CV", "language": "en", "content": "New synthetic master."},
            revision=document["revision"],
        )
        assert edited["current"]["id"] != original["id"]
        assert call(app_path + "/submitted-artifacts")["items"] == snapshots
        call(
            app_path + "/requirements/" + requirement_key + "/artifact",
            {"clear": True},
            409,
            method="PUT",
            revision=application["revision"],
        )
        application = transition(application, "UNDER_REVIEW")
        application = transition(application, "ACCEPTED")
        transition(application, "PREPARING", expected=409)
        history = call(app_path + "/history")["items"]
        assert all(row["source"] == "STUDENT_REPORTED" for row in history)
        submitted = next(row for row in history if row["to_state"] == "SUBMITTED")
        assert submitted["student_submission_confirmation"] is True
        assert submitted["manifest_snapshot"][0]["content_hash"] == original["content_hash"]
        call(
            app_path + "/transitions",
            {"to_state": "REJECTED", "source": "VERIFIED_OFFICIAL"},
            400,
            revision=application["revision"],
        )
        legal_request = call(
            app_path + "/artifact-deletion-requests",
            {
                "artifact_id": snapshots[0]["id"],
                "reason": "Synthetic lawful erasure review request.",
            },
            202,
        )
        assert legal_request["state"] == "PENDING_LEGAL_REVIEW"
        assert call(app_path + "/submitted-artifacts")["items"] == snapshots
        unknown_application = call(
            "/api/v1/applications",
            {"scholarship_id": scholarship_id, "round_key": unknown["round_key"]},
            201,
        )
        assert unknown_application["id"] != application["id"]
        assert unknown_application["deadline"]["eligible"] is False
        assert unknown_application["deadline"]["closes_at"] is None
        assert unknown_application["deadline"]["display_at"] is None
        assert call("/api/v1/applications?page=2&page_size=1")["total"] == 2
        call("/api/v1/applications?owner_id=" + session["actor_id"], expected=400)

        # Real clock reaches this pre-scheduled 24h offset; no client clock input exists.
        due = datetime.fromisoformat(catalog["due_at"])
        wait_until = time.monotonic() + 25
        while datetime.now(UTC) <= due:
            if time.monotonic() >= wait_until:
                raise RuntimeError("Synthetic real-clock deadline did not become due")
            time.sleep(0.2)
        worker = command("process_deadline_reminders")
        assert worker["delivered"] == 1
        assert command("process_deadline_reminders")["delivered"] == 0
        inbox = call("/api/v1/notifications")
        deadlines = [row for row in inbox["items"] if row["category"] == "DEADLINE"]
        assert len(deadlines) == 1
        notification = deadlines[0]
        assert notification["offset_minutes"] == 1440 and notification["read_at"] is None
        assert notification["deadline"]["source_timezone"] == "Asia/Hebron"
        assert notification["deadline"]["display_timezone"] == "Asia/Kathmandu"
        assert notification["deadline"]["display_at"].endswith("+05:45")
        read_path = f"/api/v1/notifications/{notification['id']}/read"
        read = call(read_path, {})
        assert read["read_at"] is not None and call(read_path, {})["read_at"] == read["read_at"]
        preferences = call(
            "/api/v1/notification-preferences",
            {
                "timezone": "UTC",
                "deadline_enabled": True,
                "source_enabled": True,
                "document_enabled": True,
            },
            method="PUT",
            revision=preferences["revision"],
        )
        assert preferences["timezone"] == "UTC"
        updated = call(read_path, {})
        assert updated["read_at"] == read["read_at"]
        assert updated["deadline"]["display_timezone"] == "UTC"
        assert call("/api/v1/wallet") == baseline
        check = local_fixture(
            """
import json, sys
from django.conf import settings
from notifications.models import DeadlineReminder
value = json.load(sys.stdin)
assert settings.LOCAL
assert not DeadlineReminder.objects.filter(owner_id=value['owner_id'],
    event__round_key=value['unknown_key']).exists()
assert DeadlineReminder.objects.filter(owner_id=value['owner_id']).count() == 1
print(json.dumps({'verified': True}))
""",
            {"owner_id": session["actor_id"], "unknown_key": unknown["round_key"]},
        )
        assert check["verified"]

        # Separate sessions prove object ownership and the Admin privacy boundary.
        owner_browser = browser
        browser = build_opener(HTTPCookieProcessor(CookieJar()))
        call(
            "/api/v1/session/login",
            {"email": catalog["other_email"], "password": catalog["other_password"]},
        )
        for suffix in ("", "/history", "/submitted-artifacts", "/requirements"):
            call(app_path + suffix, expected=403)
        call(read_path, {}, 404)
        assert call("/api/v1/notifications")["total"] == 0
        assert call("/api/v1/applications")["total"] == 0
        call("/api/v1/session/logout", {}, 204)
        call(
            "/api/v1/session/login",
            {"email": catalog["admin_email"], "password": catalog["admin_password"]},
        )
        call("/api/v1/applications", expected=403)
        call("/api/v1/notifications", expected=403)
        call(app_path, expected=403)
        call("/api/v1/session/logout", {}, 204)
        browser = owner_browser
        assert call(app_path + "/history")["items"] == history
        assert call(app_path + "/submitted-artifacts")["items"] == snapshots
        call("/api/v1/session/logout", {}, 204)
        call(app_path, expected=401)
        call("/api/v1/notifications", expected=401)
        print(
            "Application HTTP smoke passed: bilingual tracker/inbox, verified adult, owner "
            "and Admin isolation, approved round/checklist, explicit submission, immutable "
            "history/artifacts after master edits, separate lawful-erasure request, new round, "
            "unknown deadline safe display/no schedule, real-clock 24h reminder exactly once, "
            "sponsor/user timezones and stable read receipts; credits unchanged."
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
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_applications_[a-f0-9]{32}', value['name'])
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
