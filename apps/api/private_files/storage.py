"""Non-public, non-overwriting local development storage adapter.

Persistent encrypted object storage/region/backup approval remains an external gate.
"""

import fcntl
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from identity.security import IdentityError

from private_files.models import StoredFile
from private_files.validation import MAX_FILE_BYTES


def root() -> Path:
    configured = getattr(settings, "PRIVATE_FILES_ROOT", "")
    if not configured or not getattr(settings, "PRIVATE_FILES_STORAGE_APPROVED", False):
        raise IdentityError(
            "PRIVATE_STORAGE_UNAVAILABLE",
            503,
            "Private storage is unavailable; continue with manual data entry",
        )
    path = Path(configured)
    if not path.is_absolute() or any(parent.is_symlink() for parent in [path, *path.parents]):
        raise IdentityError("PRIVATE_STORAGE_UNAVAILABLE", 503)
    resolved = path.resolve()
    project_root = Path(settings.ROOT).resolve()
    public_roots = [
        project_root / "apps/web/public",
        project_root / "apps/web/.next",
    ]
    if any(resolved == public or public in resolved.parents for public in public_roots):
        raise IdentityError("PRIVATE_STORAGE_UNAVAILABLE", 503)
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise OSError
        return path
    except OSError as exc:
        raise IdentityError("PRIVATE_STORAGE_UNAVAILABLE", 503) from exc


def _path(file: StoredFile) -> Path:
    return root() / (str(file.storage_token) + ".blob")


@contextmanager
def lease(file: StoredFile) -> Iterator[None]:
    """Crash-released process lock fences write, scan, acceptance and physical deletion.

    A released database allocation is terminal. Every writer rechecks it while holding
    this lock, so a delayed writer can never recreate bytes after recovery releases quota.
    Lock metadata contains no student data and is not a downloadable object.
    """
    path = root() / (str(file.storage_token) + ".lock")
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise IdentityError(
                "FILE_STORAGE_BUSY", 409, "File processing is still active"
            ) from exc
        yield
    finally:
        os.close(descriptor)


def write(file: StoredFile, data: bytes) -> None:
    # O_EXCL forbids accidental key/version overwrite; O_NOFOLLOW forbids symlink traversal.
    descriptor = os.open(_path(file), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def read(file: StoredFile) -> bytes:
    descriptor = os.open(_path(file), os.O_RDONLY | os.O_NOFOLLOW)
    source: BinaryIO
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise OSError
        data = source.read(MAX_FILE_BYTES + 1)
    return data


def remove(file: StoredFile) -> None:
    path = _path(file)
    path.unlink(missing_ok=True)
    # A failed/unconfirmed cleanup never releases allocation.
    if path.exists() or path.is_symlink():
        raise OSError
