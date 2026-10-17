"""Synthetic local HTTP document flow; opt-in live ClamAV export recovery proof.

Run after migrations and the production web build. Set MINHAAI_LIVE_SCANNER_TEST=1
only with a real, configured ClamAV daemon on loopback3310. No provider is called.
"""

import hashlib
import io
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from email import policy
from email.parser import BytesParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dev import ROOT, stop


def fixture(
    source: str, values: dict[str, Any], environment: dict[str, str] | None = None
) -> dict[str, Any]:
    """Only fixed server-authored fixture code and generated local identities."""
    result = subprocess.run(
        [sys.executable, "apps/api/manage.py", "shell", "--verbosity", "0", "-c", source],
        input=json.dumps(values).encode(),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=True,
        timeout=20,
    )
    return dict(json.loads(result.stdout.splitlines()[-1]))


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Document smoke needs loopback ports3000/8000 free.")
    live = os.environ.get("MINHAAI_LIVE_SCANNER_TEST") == "1"
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    origin = "http://127.0.0.1:3000"
    message_path: Path | None = None
    private = tempfile.TemporaryDirectory(prefix="minhaai-document-smoke-")
    database = "minhaai_smoke_documents_" + uuid.uuid4().hex
    database_created = False
    environment = dict(os.environ)
    environment["POSTGRES_DB"] = database

    def local_fixture(source: str, values: dict[str, Any]) -> dict[str, Any]:
        return fixture(source, values, environment)

    def call(
        path: str,
        body: dict | None = None,
        expected: int = 200,
        *,
        revision: int | None = None,
        key: str | None = None,
        method: str | None = None,
        grant: str | None = None,
    ) -> Any:
        headers = {"Origin": origin}
        if body is not None:
            with browser.open(origin + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310 -- fixed loopback.
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": key or str(uuid.uuid4())}
            )
        if revision is not None:
            headers["If-Match"] = f'"{revision}"'
        if grant is not None:
            headers["X-File-Access-Grant"] = grant
        request = Request(  # noqa: S310 -- fixed loopback; application paths/generated UUIDs only.
            origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = browser.open(request, timeout=40)  # noqa: S310 -- fixed loopback.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"Unexpected document HTTP {response.status}; expected {expected}: {path}"
                )
            if "no-store" not in response.headers.get("Cache-Control", ""):
                raise RuntimeError("Private document HTTP must be no-store")
            if grant is not None and expected == 200:
                if response.headers.get("X-Content-Type-Options") != "nosniff":
                    raise RuntimeError("Private download omitted nosniff")
                if not response.headers.get("Content-Disposition", "").startswith("attachment;"):
                    raise RuntimeError("Private download must be an attachment")
                return response.read()
            return {} if expected == 204 else dict(json.load(response))

    def start_api(enabled: bool) -> subprocess.Popen[bytes]:
        server_environment = dict(environment)
        server_environment.update(
            PRIVATE_FILES_ROOT=private.name if enabled else "",
            PRIVATE_FILES_STORAGE_APPROVED="1" if enabled else "0",
            PRIVATE_FILES_SCANNER_HOST="127.0.0.1",
            PRIVATE_FILES_SCANNER_PORT="3310" if enabled else "1",
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "apps/api/manage.py",
                "runserver",
                "127.0.0.1:8000",
                "--noreload",
                "--nothreading",
            ],
            cwd=ROOT,
            env=server_environment,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(process)
        return process

    def ready() -> None:
        deadline = time.monotonic() + 45
        while True:
            if processes[-1].poll() is not None:
                raise RuntimeError("Document smoke server exited")
            try:
                call("/api/v1/health")
                return
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Document smoke startup timed out") from None
                time.sleep(0.25)

    try:
        fixture(
            """
import json, re, sys
from django.conf import settings
from django.db import connection
from psycopg import sql
value = json.load(sys.stdin)
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_documents_[a-f0-9]{32}', value['name'])
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
        api = start_api(False)
        processes.append(
            subprocess.Popen(
                ["npm", "run", "start", "--workspace", "@minhaai/web"],
                cwd=ROOT,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        ready()
        for locale, direction, title in (
            ("ar", "rtl", "ملفاتي ومستنداتي"),
            ("en", "ltr", "My files and documents"),
        ):
            with browser.open(origin + f"/{locale}/documents", timeout=10) as response:  # noqa: S310 -- fixed loopback.
                html = response.read().decode()
                if (
                    f'lang="{locale}"' not in html
                    or f'dir="{direction}"' not in html
                    or title not in html
                ):
                    raise RuntimeError("Document bilingual page markup failed")
        call("/api/v1/documents", expected=401)
        directory = ROOT / ".local/mail"
        previous = set(directory.glob("*.eml"))
        email = f"phase11-{uuid.uuid4()}@example.invalid"
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
        if stat.S_IMODE(message_path.stat().st_mode) != 0o600:
            raise RuntimeError("Synthetic verification email is not private")
        message = BytesParser(policy=policy.default).parsebytes(message_path.read_bytes())
        match = re.search(r"Verification code: (\S+)", str(message.get_content()))
        if not match:
            raise RuntimeError("Local verification code is absent")
        call("/api/v1/documents", expected=401)
        call("/api/v1/auth/email-verifications", {"challenge_token": match.group(1)})
        session = call("/api/v1/session/login", {"email": email, "password": password})
        baseline = call("/api/v1/wallet")
        assert baseline["posted_balance"] == 30 and baseline["reserved_balance"] == 0
        assert call("/api/v1/documents")["items"] == []
        assert call("/api/v1/documents/capabilities")["private_ai"] is False
        assert call("/api/v1/files/capabilities")["upload_available"] is False
        body = {
            "kind": "CV",
            "title": "Synthetic CV",
            "language": "en",
            "content": "Synthetic student\n<script>synthetic text only</script>",
        }
        key = str(uuid.uuid4())
        document = call("/api/v1/documents", body, 201, key=key)
        assert call("/api/v1/documents", body, 201, key=key) == document
        path = "/api/v1/documents/" + document["id"]
        original = document["current"]
        assert "<script>" not in original["preview_html"]
        assert "&lt;script&gt;" in original["preview_html"]
        edited = call(
            path + "/versions",
            {"title": "Edited synthetic CV", "language": "en", "content": "Edited synthetic text"},
            revision=document["revision"],
        )
        restored = call(
            path + "/restore", {"version_id": original["id"]}, revision=edited["revision"]
        )
        saved = restored["current"]
        assert saved["id"] != original["id"] and saved["restored_from_id"] == original["id"]
        assert saved["content"] == original["content"]
        assert len(call(path + "/versions")["items"]) == 3
        compared = call(path + "/compare?left=" + original["id"] + "&right=" + saved["id"])
        assert compared["left"]["content_hash"] == compared["right"]["content_hash"]
        approved = call(
            path + "/approvals",
            {"version_id": saved["id"], "content_hash": saved["content_hash"], "confirm": True},
        )
        assert approved["approved"] is True
        for kind in ("MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"):
            call(
                "/api/v1/documents",
                {
                    "kind": kind,
                    "title": "مستند اصطناعي",
                    "language": "ar",
                    "content": "طالب اصطناعي",
                },
                201,
            )
        call("/api/v1/documents?owner_id=" + session["actor_id"], expected=400)
        call("/api/v1/documents/" + str(uuid.uuid4()), expected=403)
        assert call("/api/v1/documents/generate", {**body, "consent": False}, 403)["code"] == (
            "DOCUMENT_AI_CONSENT_REQUIRED"
        )
        assert call("/api/v1/documents/generate", {**body, "consent": True}, 503)["code"] == (
            "PRIVATE_AI_PIPELINE_UNAVAILABLE"
        )
        # Metadata-only quarantine fixture never represents an accepted/uploaded file.
        asset = local_fixture(
            """
import json, sys
from django.conf import settings
from identity.models import Account
from privacy.models import PrivateAsset
value = json.load(sys.stdin)
assert settings.LOCAL and value['email'].startswith('phase11-')
assert value['email'].endswith('@example.invalid')
owner = Account.objects.get(pk=value['id'], email=value['email'])
asset = PrivateAsset.objects.create(owner=owner, object_version='SYNTHETIC_NO_BYTES')
assert asset.state == 'QUARANTINED'
print(json.dumps({'id': str(asset.pk)}))
""",
            {"id": session["actor_id"], "email": email},
        )
        assert call("/api/v1/documents/extract", {"asset_id": asset["id"], "consent": False}, 403)[
            "code"
        ] == ("DOCUMENT_AI_CONSENT_REQUIRED")
        assert call("/api/v1/documents/extract", {"asset_id": asset["id"], "consent": True}, 503)[
            "code"
        ] == ("PRIVATE_AI_PIPELINE_UNAVAILABLE")
        export = {"version_id": saved["id"], "format": "DOCX"}
        assert call(path + "/exports", export, 503)["code"] == "PRIVATE_STORAGE_UNAVAILABLE"
        assert call(path)["current"]["id"] == saved["id"]
        assert call("/api/v1/wallet") == baseline
        if live:
            stop([api])
            start_api(True)
            ready()
            assert call("/api/v1/files/capabilities")["upload_available"] is True
            for output_format, prefix in (("PDF", b"%PDF-"), ("DOCX", b"PK\x03\x04")):
                export["format"] = output_format
                result = call(path + "/exports", export)
                assert call(path + "/exports", export) == result
                grant = call("/api/v1/files/" + result["asset_id"] + "/access-grants", {}, 201)
                data = call(
                    "/api/v1/files/" + result["asset_id"] + "/content", grant=grant["token"]
                )
                assert data.startswith(prefix)
                if output_format == "PDF":
                    from pypdf import PdfReader

                    assert len(PdfReader(io.BytesIO(data), strict=True).pages) >= 1
                else:
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        assert "word/document.xml" in archive.namelist()
                proof = local_fixture(
                    """
import json, sys
from django.conf import settings
from private_files.models import ScanReceipt
value = json.load(sys.stdin)
assert settings.LOCAL
receipt = ScanReceipt.objects.get(file_id=value['asset_id'])
assert receipt.verdict == 'CLEAN' and receipt.engine.startswith('ClamAV ')
assert receipt.sha256 == value['sha256'] and receipt.size == value['size']
print(json.dumps({'verified': True}))
""",
                    {
                        "asset_id": result["asset_id"],
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    },
                )
                assert proof["verified"] is True
            assert call("/api/v1/wallet") == baseline
            assert len(list(Path(private.name).glob("*.blob"))) == 2
        call("/api/v1/session/logout", {}, 204)
        call("/api/v1/documents", expected=401)
        print(
            "Document HTTP smoke passed: bilingual pages, verified adult, four manual types, "
            "sanitized preview, edit/restore/approval, private AI safe failure, saved-version "
            "export failure and unchanged credits; "
            + (
                "actual ClamAV PDF/DOCX export recovery/re-export/grants passed."
                if live
                else "live scanner export checks SKIPPED (set MINHAAI_LIVE_SCANNER_TEST=1)."
            )
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
assert settings.LOCAL and re.fullmatch(r'minhaai_smoke_documents_[a-f0-9]{32}', value['name'])
assert connection.settings_dict['NAME'] != value['name']
with connection.cursor() as cursor:
    cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(value['name'])))
print(json.dumps({'dropped': True}))
""",
                    {"name": database},
                )
        finally:
            private.cleanup()
            if message_path is not None:
                message_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
