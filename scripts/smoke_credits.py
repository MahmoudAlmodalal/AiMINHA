"""Real wallet HTTP flow with isolated synthetic local identity fixtures only."""

import json
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
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dev import ROOT, stop


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Credit smoke needs loopback ports 3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    origin = "http://127.0.0.1:3000"

    def call(path: str, body: dict | None = None, expected: int = 200) -> dict[str, Any]:
        headers = {"Origin": origin}
        if body is not None:
            with browser.open(origin + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310 -- fixed loopback.
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())}
            )
        request = Request(  # noqa: S310 -- application-owned loopback paths only.
            origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        try:
            response = browser.open(request, timeout=10)  # noqa: S310 -- fixed loopback.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(f"Unexpected credit HTTP {response.status}; expected {expected}")
            if response.headers.get("Cache-Control") != "no-store":
                raise RuntimeError("Private credit HTTP must be no-store")
            return {} if expected == 204 else dict(json.load(response))

    try:
        for command in (
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
                    command,
                    cwd=ROOT,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
        deadline = time.monotonic() + 45
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("Credit smoke server exited")
            try:
                call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Credit startup timed out") from None
                time.sleep(0.25)
        for locale, direction, heading in (
            ("ar", "rtl", "رصيد الاستخدام وسجل الحركات"),
            ("en", "ltr", "Credit wallet and history"),
        ):
            with browser.open(origin + f"/{locale}/wallet", timeout=10) as response:  # noqa: S310 -- fixed loopback.
                html = response.read().decode()
                if (
                    f'lang="{locale}"' not in html
                    or f'dir="{direction}"' not in html
                    or heading not in html
                ):
                    raise RuntimeError("Credit locale markup failed")
        for path in ("/api/v1/wallet", "/api/v1/wallet/entries", "/api/v1/operations"):
            call(path, expected=401)

        directory = ROOT / ".local/mail"
        previous = set(directory.glob("*.eml"))
        email = f"phase09-{uuid.uuid4()}@example.invalid"
        password = "Synthetic-only-" + str(uuid.uuid4())
        call(
            "/api/v1/auth/registrations",
            {"email": email, "password": password, "birth_date": "2000-02-29", "locale": "ar"},
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
        call("/api/v1/session/login", {"email": email, "password": password}, 401)
        call("/api/v1/wallet", expected=401)
        call("/api/v1/auth/email-verifications", {"challenge_token": match.group(1)})
        session = call("/api/v1/session/login", {"email": email, "password": password})
        wallet = call("/api/v1/wallet")
        if (
            wallet["posted_balance"] != 30
            or wallet["available_balance"] != 30
            or wallet["reserved_balance"] != 0
            or wallet["signup_grant"]["awarded"] is not True
            or wallet["signup_grant"]["amount"] != 30
            or wallet["daily"]["cap"] != 6
            or wallet["daily"]["spent"] != 0
            or wallet["daily"]["reserved"] != 0
            or wallet["daily"]["remaining"] != 6
            or wallet["daily"]["timezone"] != "Asia/Hebron"
            or wallet["global_daily"]["cap"] != 100
            or wallet["policy"]["ai_execution_available"] is not False
            or wallet["policy"]["reserve_minutes"] != 15
            or wallet["policy"]["reconciliation_target_hours"] != 24
            or wallet["policy"]["prices"]
            != {"MATCHING_AI": 1, "CV_EXTRACTION": 4, "DOCUMENT_NEW": 6}
        ):
            raise RuntimeError("Credit bootstrap balances, caps or price policy failed")
        if set(wallet["policy"]["free_services"]) != {
            "BROWSING",
            "RULES_ELIGIBILITY",
            "MANUAL_EDITS",
            "SAME_VERSION_REEXPORT",
            "EXTENSION",
        }:
            raise RuntimeError("Credit policy omitted a free baseline service")
        history = call("/api/v1/wallet/entries?page=1&page_size=1")
        if (
            history["total"] != 1
            or len(history["items"]) != 1
            or history["items"][0]["kind"] != "SIGNUP_GRANT"
            or history["items"][0]["amount"] != 30
            or history["items"][0]["operation_id"] is not None
        ):
            raise RuntimeError("Activation did not create exactly one signup grant")
        operations = call("/api/v1/operations?page=1&page_size=1")
        if operations["total"] != 0 or operations["items"]:
            raise RuntimeError("Read-only wallet created an operation")
        capabilities = call("/api/v1/ai/capabilities")
        if (
            capabilities["live_execution_available"] is not False
            or capabilities["mock_client_execution_available"] is not False
            or capabilities["classification_required"] is not True
            or capabilities["logical_daily_cap"] != 100
            or capabilities["cloudflare_neurons_ceiling"] != 8000
            or set(capabilities["allowed_classifications"])
            != {"PUBLIC/SYNTHETIC", "STUDENT_PRIVATE", "PROHIBITED"}
        ):
            raise RuntimeError("AI capability gates were not closed")
        call("/api/v1/ai/capabilities", {}, 405)
        call("/api/v1/ai/capabilities?owner_id=forged", expected=400)
        call("/api/v1/operations", {}, 405)
        call(f"/api/v1/operations/{uuid.uuid4()}", expected=403)
        call(f"/api/v1/wallet?owner_id={session['actor_id']}", expected=400)
        call(f"/api/v1/wallet/entries?owner_id={session['actor_id']}", expected=400)
        call("/api/v1/operations?page_size=51", expected=400)
        call("/api/v1/profile")
        call("/api/v1/scholarships?page_size=1")
        call(
            "/api/v1/eligibility/evaluations",
            {
                "profile_version_id": str(uuid.uuid4()),
                "scholarship_id": str(uuid.uuid4()),
                "scholarship_version_id": str(uuid.uuid4()),
            },
            403,
        )
        unchanged = call("/api/v1/wallet")
        if unchanged != wallet:
            raise RuntimeError("Free reads or denied requests changed the wallet")
        if any(value in json.dumps(wallet) for value in (email, password, match.group(1))):
            raise RuntimeError("Wallet response exposed an identity credential")
        call("/api/v1/session/logout", {}, 204)
        call("/api/v1/wallet", expected=401)
        call("/api/v1/session/login", {"email": email, "password": password})
        if call("/api/v1/wallet/entries")["total"] != 1:
            raise RuntimeError("A repeated sign-in duplicated the activation grant")

        # Only this smoke's freshly created synthetic fixture becomes an Admin.
        # No public role-management, synthetic AI or settlement endpoint is added.
        fixture = """
import json, sys
from django.conf import settings
from identity.models import Account
value = json.load(sys.stdin)
assert settings.LOCAL and value['email'].startswith('phase09-')
assert value['email'].endswith('@example.invalid')
assert Account.objects.filter(pk=value['id'], email=value['email']).update(role='ADMIN') == 1
"""
        subprocess.run(
            [sys.executable, "apps/api/manage.py", "shell", "-c", fixture],
            input=json.dumps({"id": session["actor_id"], "email": email}).encode(),
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=15,
        )
        call("/api/v1/session/logout", {}, 204)
        admin = call("/api/v1/session/login", {"email": email, "password": password})
        if admin["roles"] != ["ADMIN"]:
            raise RuntimeError("Synthetic Admin fixture was not activated")
        for path in (
            "/api/v1/wallet",
            "/api/v1/wallet/entries",
            "/api/v1/operations",
            "/api/v1/ai/capabilities",
        ):
            call(path, expected=403)
        call(f"/api/v1/operations/{uuid.uuid4()}", expected=403)
        call("/api/v1/session/logout", {}, 204)
        call("/api/v1/wallet", expected=401)
        print(
            "Credit HTTP smoke passed: bilingual wallet, verified adult once-only 30 grant, "
            "daily spend cap/prices, free reads, private ledger, denied execution/selection, "
            "Admin denial, closed AI capabilities and logout; no credentials or provider calls."
        )
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
