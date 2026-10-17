"""Bounded memory ingress: no unaudited temporary disk upload before quota admission."""

from collections.abc import Callable
from typing import Any

from core.errors import problem
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.http import HttpRequest, HttpResponse
from identity.security import audit

from private_files.validation import MAX_FILE_BYTES


class BoundedMemoryHandler(FileUploadHandler):
    def __init__(self, request: HttpRequest) -> None:
        import io

        super().__init__(request)
        self.buffer = io.BytesIO()
        self.received = 0
        self.files_seen = 0

    def new_file(self, *args: Any, **kwargs: Any) -> None:
        super().new_file(*args, **kwargs)
        self.files_seen += 1
        if self.files_seen > 1:
            self.request._bounded_upload_rejected = True
            raise StopUpload(connection_reset=True)

    def receive_data_chunk(self, raw_data: bytes, start: int) -> None:
        self.received += len(raw_data)
        if self.received > MAX_FILE_BYTES:
            self.request._bounded_upload_rejected = True
            raise StopUpload(connection_reset=True)
        self.buffer.write(raw_data)

    def file_complete(self, file_size: int) -> InMemoryUploadedFile:
        self.buffer.seek(0)
        return InMemoryUploadedFile(
            self.buffer,
            self.field_name,
            self.file_name,
            self.content_type,
            file_size,
            self.charset,
            self.content_type_extra,
        )


class BoundedUploadMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == "/api/v1/files/uploads" and request.method == "POST":
            request.upload_handlers = [BoundedMemoryHandler(request)]
            try:
                content_length = int(request.META.get("CONTENT_LENGTH", "0"))
            except (ValueError, TypeError):
                return problem(request, 400, "INVALID_REQUEST", "Invalid upload")
            # Multipart framing and one bounded field. Measured file bytes also enforced.
            if content_length > MAX_FILE_BYTES + 65536:
                try:
                    audit(
                        getattr(request, "user", None),
                        "private_file_upload",
                        "DENY",
                        reason="FILE_TOO_LARGE",
                        correlation=getattr(request, "correlation_id", None),
                    )
                except Exception:
                    return problem(
                        request, 503, "AUDIT_UNAVAILABLE", "Upload could not be safely audited"
                    )
                return problem(request, 413, "FILE_TOO_LARGE", "File exceeds 5,000,000 bytes")
        return self.get_response(request)
