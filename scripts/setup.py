"""Create local credentials without displaying them or replacing an existing .env."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / ".env"
    if path.exists():
        print("Existing .env preserved; replace placeholder values locally if necessary.")
        return
    template = (ROOT / ".env.example").read_text()
    content = template.replace("replace-with-generated-local-secret", secrets.token_urlsafe(64))
    content = content.replace("replace-with-generated-local-password", secrets.token_urlsafe(32))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    print("Created private local .env. Credential values are not displayed.")


if __name__ == "__main__":
    main()
