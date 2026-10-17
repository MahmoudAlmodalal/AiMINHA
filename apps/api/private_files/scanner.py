"""ClamAV clamd protocol. No client claim or synthetic runtime clean adapter exists."""

import ipaddress
import re
import socket
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.utils import timezone
from identity.security import IdentityError


def unavailable() -> IdentityError:
    return IdentityError(
        "FILE_SCANNER_UNAVAILABLE",
        503,
        "File scanning is unavailable; continue with manual data entry",
    )


@dataclass(frozen=True)
class CleanScan:
    engine: str
    signature_version: str
    signature_at: datetime


def _connect() -> socket.socket:
    host = getattr(settings, "PRIVATE_FILES_SCANNER_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    try:
        address = ipaddress.ip_address(host)
        if not (address.is_private or address.is_loopback):
            raise ValueError
        return socket.create_connection(
            (host, int(getattr(settings, "PRIVATE_FILES_SCANNER_PORT", 3310))),
            timeout=float(getattr(settings, "PRIVATE_FILES_SCANNER_TIMEOUT_SECONDS", 30)),
        )
    except (OSError, ValueError, TypeError) as exc:
        raise unavailable() from exc


def _reply(connection: socket.socket) -> bytes:
    result = b""
    while b"\x00" not in result:
        piece = connection.recv(1024)
        if not piece or len(result) + len(piece) > 4096:
            raise unavailable()
        result += piece
    response, trailing = result.split(b"\x00", 1)
    if trailing:
        raise unavailable()
    return response


def health() -> CleanScan:
    try:
        with _connect() as connection:
            connection.sendall(b"zVERSION\x00")
            version = _reply(connection).decode("ascii")
        match = re.fullmatch(r"ClamAV ([^/\r\n]{1,100})/(\d{1,20})/(.{1,80})", version)
        if not match:
            raise unavailable()
        signature_at = datetime.strptime(match[3], "%a %b %d %H:%M:%S %Y").replace(tzinfo=UTC)
        now = timezone.now()
        max_age = timedelta(
            hours=getattr(settings, "PRIVATE_FILES_SCANNER_MAX_SIGNATURE_AGE_HOURS", 168)
        )
        if signature_at > now + timedelta(minutes=5) or now - signature_at > max_age:
            raise unavailable()
        return CleanScan("ClamAV " + match[1], match[2], signature_at)
    except (OSError, UnicodeError, ValueError) as exc:
        raise unavailable() from exc


def scan(data: bytes) -> CleanScan:
    evidence = health()
    try:
        with _connect() as connection:
            connection.sendall(b"zINSTREAM\x00")
            for offset in range(0, len(data), 65536):
                piece = data[offset : offset + 65536]
                connection.sendall(struct.pack("!I", len(piece)) + piece)
            connection.sendall(struct.pack("!I", 0))
            response = _reply(connection)
        if response.endswith(b" FOUND"):
            raise IdentityError("FILE_MALWARE_DETECTED", 422, "File was rejected as unsafe")
        if response != b"stream: OK":
            raise unavailable()
        return evidence
    except OSError as exc:
        raise unavailable() from exc
