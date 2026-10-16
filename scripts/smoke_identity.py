"""Real same-origin HTTP identity flow, using only isolated synthetic local accounts."""

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
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dev import ROOT, stop


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Identity smoke needs loopback ports 3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    browser = build_opener(HTTPCookieProcessor(CookieJar()))
    origin = "http://127.0.0.1:3000"

    def call(path: str, body: dict | None = None, expected: int = 200) -> dict:
        headers = {"Origin": origin}
        if body is not None:
            with browser.open(origin + "/api/v1/session/csrf", timeout=5) as response:  # noqa: S310 -- fixed loopback.
                headers["X-CSRFToken"] = json.load(response)["csrf_token"]
            headers.update(
                {"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())}
            )
        request = Request(
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
                raise RuntimeError(f"Unexpected HTTP status {response.status}; expected {expected}")
            if expected == 204:
                return {}
            return dict(json.load(response))

    try:
        for command in (
            [sys.executable, "apps/api/manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
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
                raise RuntimeError("Identity smoke server exited")
            try:
                call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Identity smoke startup timed out") from None
                time.sleep(0.25)
        for locale, direction in (("ar", "rtl"), ("en", "ltr")):
            with browser.open(origin + f"/{locale}/account", timeout=10) as response:  # noqa: S310
                html = response.read().decode()
                if f'lang="{locale}"' not in html or f'dir="{direction}"' not in html:
                    raise RuntimeError("Account locale markup failed")
        mail_directory = ROOT / ".local/mail"
        previous = set(mail_directory.glob("*.eml"))
        email = f"phase06-{uuid.uuid4()}@example.invalid"
        password = "Synthetic-only-" + str(uuid.uuid4())
        ack = call(
            "/api/v1/auth/registrations",
            {"email": email, "password": password, "birth_date": "2000-02-29", "locale": "ar"},
            202,
        )
        if set(ack) != {"accepted", "correlation_id"}:
            raise RuntimeError("Registration exposed unexpected fields")
        messages = set(mail_directory.glob("*.eml")) - previous
        if len(messages) != 1:
            raise RuntimeError("Expected one private local verification message")
        message_path = messages.pop()
        if stat.S_IMODE(message_path.stat().st_mode) != 0o600:
            raise RuntimeError("Local verification mail permissions are not private")
        message = BytesParser(policy=policy.default).parsebytes(message_path.read_bytes())
        match = re.search(r"Verification code: (\S+)", str(message.get_content()))
        if not match:
            raise RuntimeError("Local verification code missing")
        token = match.group(1)
        call("/api/v1/auth/email-verifications", {"challenge_token": token})
        session = call("/api/v1/session/login", {"email": email, "password": password})
        if not session.get("verified_email") or not session.get("adult_eligible"):
            raise RuntimeError("Server session not verified/adult")
        if any(value in json.dumps(session) for value in (email, password, token)):
            raise RuntimeError("Session exposed a private credential")
        call("/api/v1/files")
        call(f"/api/v1/files/{uuid.uuid4()}", expected=403)
        call("/api/v1/account/deletions/impact")
        call("/api/v1/session/logout", {}, 204)
        call("/api/v1/session", expected=401)
        print(
            "Identity HTTP smoke passed: bilingual UI, private local mail, signup/verify/login, "
            "owned access, audited denial, logout; no credentials printed."
        )
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
