"""Bounded real-HTTP proof against a production Next build and local Django."""

import argparse
import json
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dev import ROOT, stop


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--liveness-only",
        action="store_true",
        help="Exercise WSGI/HTTP without database readiness; not the migration gate.",
    )
    options = parser.parse_args()
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"Port {port} is occupied; smoke needs both loopback ports free.")
    processes: list[subprocess.Popen[bytes]] = []
    try:
        api_command = [
            sys.executable,
            "apps/api/manage.py",
            "runserver",
            "127.0.0.1:8000",
            "--noreload",
        ]
        if options.liveness_only:
            # The identical Django WSGI application, without runserver's database preflight.
            api_command = [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'apps/api'); "
                "from config.wsgi import application; "
                "from django.core.servers.basehttp import run; "
                "run('127.0.0.1', 8000, application, threading=True)",
            ]
        for command in (
            api_command,
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
                raise SystemExit("A smoke server exited before startup.")
            try:
                with urlopen("http://127.0.0.1:3000/api/v1/health", timeout=2) as response:
                    assert json.load(response) == {"status": "ok"}
                    assert response.headers["Cache-Control"] == "no-store"
                break
            except (URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise SystemExit("Server startup timed out.") from None
                time.sleep(0.5)
        with urlopen("http://127.0.0.1:8000/api/v1/health", timeout=5) as response:
            assert json.load(response) == {"status": "ok"}
        try:
            urlopen(
                Request(
                    "http://127.0.0.1:3000/api/v1/health",
                    data=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "Origin": "https://foreign.invalid",
                    },
                ),
                timeout=5,
            )
        except HTTPError as error:
            assert error.code == 403
            assert json.load(error)["code"] == "CSRF_FAILED"
            assert "Access-Control-Allow-Origin" not in error.headers
        else:
            raise AssertionError("Unsafe request unexpectedly accepted.")
        for locale, direction in (("ar", "rtl"), ("en", "ltr")):
            with urlopen(f"http://127.0.0.1:3000/{locale}", timeout=5) as response:
                page = response.read().decode()
                assert f'lang="{locale}"' in page and f'dir="{direction}"' in page
                assert 'id="main"' in page
        try:
            urlopen("http://127.0.0.1:3000/api/v1/nonexistent", timeout=5)
        except HTTPError as error:
            assert error.code == 404
            assert error.headers["Content-Type"] == "application/problem+json"
            assert json.load(error)["code"] == "NOT_FOUND"
        else:
            raise AssertionError("Unknown API path did not return 404.")
        print(
            "HTTP smoke passed: Django, Next production build, API rewrite/CSRF, "
            "Arabic RTL/English LTR, safe 404."
        )
        if options.liveness_only:
            print("Liveness-only mode: database startup and migrations are NOT verified.")
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
