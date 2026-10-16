"""Small baseline guard for tracked/proposed files, not a full security audit."""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
]


def main() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    failures = []
    names = set(result.stdout.decode().split("\0")) - {""}
    local_values: dict[str, str] = {}
    local_environment = ROOT / ".env"
    if local_environment.exists():
        local_values = dict(
            line.split("=", 1)
            for line in local_environment.read_text().splitlines()
            if line and not line.startswith("#") and "=" in line
        )
    private_values = {
        value
        for key in ("DJANGO_SECRET_KEY", "POSTGRES_PASSWORD")
        for value in (local_values.get(key, ""), os.environ.get(key, ""))
        if len(value) >= 16 and not value.startswith("replace-with-")
    }
    for name in sorted(names):
        path = ROOT / name
        if not path.is_file():
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            failures.append(name)
            continue
        value = path.read_text(errors="replace")
        if any(pattern.search(value) for pattern in PATTERNS) or any(
            secret in value for secret in private_values
        ):
            failures.append(name)
    browser_files = list((ROOT / "apps/web/.next/static").rglob("*"))
    for path in browser_files:
        if path.is_file():
            data = path.read_bytes()
            if any(value.encode() in data for value in private_values):
                failures.append(str(path.relative_to(ROOT)))
    template = (ROOT / ".env.example").read_text()
    for line in template.splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            if any(word in key for word in ("SECRET", "PASSWORD", "TOKEN", "API_KEY")):
                if not value.startswith("replace-with-"):
                    failures.append(".env.example")
    if failures:
        raise SystemExit("Potential credentials in: " + ", ".join(sorted(set(failures))))
    print(
        f"Baseline secret scan passed for {len(names)} tracked/proposed files; "
        "template credentials are placeholders only."
    )
    if browser_files:
        print("Browser build also checked for generated/exported local backend credentials.")


if __name__ == "__main__":
    main()
