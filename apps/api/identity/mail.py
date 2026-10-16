"""Local verification messages are private files, never API responses or console logs."""

import os
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class PrivateLocalMailBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Any) -> int:
        if not settings.LOCAL:
            raise RuntimeError("Local mail backend is unavailable outside local mode")
        directory = Path(settings.ROOT) / ".local/mail"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        count = 0
        for message in email_messages:
            path = directory / f"{uuid.uuid4()}.eml"
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(message.message().as_bytes())
            count += 1
        return count
