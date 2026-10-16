"""Production Next/Django HTTP catalog smoke; never fetches a scholarship source."""

import json
import socket
import subprocess
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dev import ROOT, stop


def main() -> None:
    for port in (3000, 8000):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Catalog smoke needs loopback ports 3000/8000 free.")
    processes: list[subprocess.Popen[bytes]] = []
    origin = "http://127.0.0.1:3000"

    def call(path: str, expected: int = 200) -> dict:
        try:
            response = urlopen(origin + path, timeout=10)  # noqa: S310 -- loopback only.
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"Unexpected catalog HTTP {response.status}; expected {expected}"
                )
            if response.headers.get("Cache-Control") != "no-store":
                raise RuntimeError("Catalog HTTP response must be no-store")
            return dict(json.load(response))

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
                raise RuntimeError("Catalog smoke server exited")
            try:
                call("/api/v1/health")
                break
            except (URLError, TimeoutError, RuntimeError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Catalog smoke startup timed out") from None
                time.sleep(0.25)
        for locale, direction in (("ar", "rtl"), ("en", "ltr")):
            for path in ("scholarships", f"scholarships/{uuid.uuid4()}", "admin/catalog"):
                with urlopen(origin + f"/{locale}/{path}", timeout=10) as response:  # noqa: S310
                    html = response.read().decode()
                    if f'lang="{locale}"' not in html or f'dir="{direction}"' not in html:
                        raise RuntimeError("Catalog locale markup failed")
        page = call("/api/v1/scholarships?q=synthetic&page=1&page_size=2&mode=TEXT")
        if set(page) != {"items", "total", "page", "page_size", "search_mode"}:
            raise RuntimeError("Unexpected public catalog fields")
        if len(page["items"]) > 2 or page["search_mode"] != "TEXT":
            raise RuntimeError("Catalog search pagination failed")
        for item in page["items"]:
            if any(
                field in item
                for field in ("internal_notes", "license_basis", "permission_evidence")
            ):
                raise RuntimeError("Catalog exposed internal fields")
        # Exercise consecutive proxy requests, where pooled upstream socket resets
        # previously produced an HTML 500 before Django received the request.
        for _ in range(50):
            call("/api/v1/scholarships?page_size=1")
        with urlopen("http://127.0.0.1:8000/api/v1/health", timeout=5) as response:  # noqa: S310
            if response.headers.get("Connection") != "close":
                raise RuntimeError("Local smoke server must explicitly close upstream connections")
        call(f"/api/v1/scholarships/{uuid.uuid4()}", 404)
        call("/api/v1/admin/sources", 401)
        call("/api/v1/admin/scholarships", 401)
        call("/api/v1/scholarships?mode=SEMANTIC", 503)
        call("/api/v1/scholarships?page_size=51", 400)
        print(
            "Catalog HTTP smoke passed: six bilingual routes, public search/rewrite, bounded "
            "pagination, unavailable semantic mode and denied anonymous moderation; "
            "no source fetched."
        )
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
