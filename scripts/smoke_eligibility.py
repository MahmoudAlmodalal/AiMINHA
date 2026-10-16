"""Actual same-origin private profile HTTP flow, with synthetic local security mail only."""

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
                raise SystemExit("Eligibility smoke needs loopback ports 3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    origin = "http://127.0.0.1:3000"

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
            with browser.open(origin + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": key or str(uuid.uuid4())}
            )
        if revision is not None:
            headers["If-Match"] = f'"{revision}"'
        request = Request(  # noqa: S310 -- fixed loopback origin and application-owned paths.
            origin + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = browser.open(request, timeout=10)  # noqa: S310 -- fixed loopback only.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"Unexpected eligibility HTTP {response.status}; expected {expected}"
                )
            if response.headers.get("Cache-Control") != "no-store":
                raise RuntimeError("Private profile HTTP must be no-store")
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
                raise RuntimeError("Eligibility smoke server exited")
            try:
                call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Eligibility startup timed out") from None
                time.sleep(0.25)
        for locale, direction in (("ar", "rtl"), ("en", "ltr")):
            with browser.open(origin + f"/{locale}/eligibility", timeout=10) as response:  # noqa: S310
                html = response.read().decode()
                if f'lang="{locale}"' not in html or f'dir="{direction}"' not in html:
                    raise RuntimeError("Eligibility locale markup failed")
        call("/api/v1/profile", expected=401)
        directory = ROOT / ".local/mail"
        previous = set(directory.glob("*.eml"))
        email = f"phase08-{uuid.uuid4()}@example.invalid"
        password = "Synthetic-only-" + str(uuid.uuid4())
        call(
            "/api/v1/auth/registrations",
            {"email": email, "password": password, "birth_date": "2000-02-29", "locale": "ar"},
            202,
        )
        messages = set(directory.glob("*.eml")) - previous
        if len(messages) != 1:
            raise RuntimeError("Expected one synthetic private verification email")
        path = messages.pop()
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError("Synthetic verification email is not private")
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        match = re.search(r"Verification code: (\S+)", str(message.get_content()))
        if not match:
            raise RuntimeError("Local verification code is absent")
        call("/api/v1/auth/email-verifications", {"challenge_token": match.group(1)})
        call("/api/v1/session/login", {"email": email, "password": password})
        empty = call("/api/v1/profile")
        if empty["revision"] != 0 or empty["profile"]["gpa"] is not None:
            raise RuntimeError("An absent profile must preserve unknown GPA")
        body = {
            "nationalities": ["PS"],
            "residency_country": None,
            "degree_level": "MASTER",
            "major": None,
            "qualification": "BACHELOR",
            "gpa": {"value": "3.25", "scale": "GPA_4_0"},
            "languages": [{"language": "en", "level": None}],
            "preferred_countries": ["DE"],
            "confirmed_fields": [
                "nationalities",
                "degree_level",
                "qualification",
                "gpa",
                "preferred_countries",
            ],
        }
        key = str(uuid.uuid4())
        saved = call("/api/v1/profile", body, method="PUT", revision=0, key=key)
        replay = call("/api/v1/profile", body, method="PUT", revision=0, key=key)
        if saved != replay or saved["revision"] != 1 or saved["profile"]["major"] is not None:
            raise RuntimeError("Profile version, unknowns or idempotency were not preserved")
        if any(value in json.dumps(saved) for value in (email, password, match.group(1))):
            raise RuntimeError("Profile response exposed identity credentials")
        call(
            "/api/v1/eligibility/evaluations",
            {
                "profile_version_id": str(uuid.uuid4()),
                "scholarship_id": str(uuid.uuid4()),
                "scholarship_version_id": str(uuid.uuid4()),
            },
            403,
        )
        call(
            "/api/v1/eligibility/evaluations",
            {
                "profile_version_id": saved["version_id"],
                "scholarship_id": str(uuid.uuid4()),
                "scholarship_version_id": str(uuid.uuid4()),
            },
            409,
        )
        call(f"/api/v1/eligibility/evaluations/{uuid.uuid4()}", expected=403)
        call("/api/v1/session/logout", {}, 204)
        call("/api/v1/profile", expected=401)
        print(
            "Eligibility HTTP smoke passed: bilingual UI, signup/verify/login, private nullable "
            "profile PUT/replay, ownership/current-catalog denials and logout; "
            "no private facts printed."
        )
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
