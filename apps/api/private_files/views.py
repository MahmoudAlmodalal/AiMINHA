from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from identity.security import IdentityError, require_student
from identity.views import CSRF, IDEMPOTENCY, IdentityView
from identity.views import ERRORS as IDENTITY_ERRORS
from privacy.models import TicketShare
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from private_files import serializers as dto
from private_files import services

GRANT_HEADER = OpenApiParameter(
    "X-File-Access-Grant",
    str,
    OpenApiParameter.HEADER,
    required=True,
)
ERRORS = {**IDENTITY_ERRORS, 404: ProblemSerializer, 413: ProblemSerializer, 422: ProblemSerializer}


class CapabilitiesView(IdentityView):
    @extend_schema(responses={200: dto.CapabilitiesSerializer, **ERRORS})
    def get(self, request: Any) -> Response:
        require_student(request.user)
        return Response(services.capabilities())


class UploadView(IdentityView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=dto.UploadSerializer,
        responses={201: dto.FileSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
    )
    def post(self, request: Any) -> Response:
        require_student(request.user)
        data = request.data
        if getattr(request._request, "_bounded_upload_rejected", False):
            raise IdentityError("FILE_TOO_LARGE", 413, "File exceeds the upload limit")
        if set(data) != {"file"} or len(request.FILES.getlist("file")) != 1:
            raise IdentityError("INVALID_REQUEST", 400)
        file = request.FILES["file"]
        if file.size > services.validation.MAX_FILE_BYTES:
            raise IdentityError("FILE_TOO_LARGE", 413)
        asset = services.store_bytes(
            request.user.pk,
            file.name,
            file.content_type,
            file.read(5_000_001),
            request.headers.get("Idempotency-Key", ""),
        )
        return Response(services.upload_data(asset), status=201)


class GrantView(IdentityView):
    @extend_schema(
        request=dto.EmptySerializer,
        responses={201: dto.GrantSerializer, **ERRORS},
        parameters=[CSRF],
    )
    def post(self, request: Any, file_id: UUID) -> Response:
        if request.data:
            raise IdentityError("INVALID_REQUEST", 400)
        return Response(
            services.issue_grant(request.user, request.identity_session, file_id), status=201
        )


def bytes_response(file: Any, content: bytes) -> HttpResponse:
    response = HttpResponse(content, content_type=file.mime)
    # Fixed server-selected filename avoids reflecting untrusted upload labels.
    extension = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}.get(
        file.mime, "docx"
    )
    response["Content-Disposition"] = f'attachment; filename="private-file.{extension}"'
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


class ContentView(IdentityView):
    @extend_schema(
        responses={(200, "application/octet-stream"): bytes, **ERRORS}, parameters=[GRANT_HEADER]
    )
    def get(self, request: Any, file_id: UUID) -> HttpResponse:
        file, content = services.read_granted(
            request.user,
            request.identity_session,
            file_id,
            request.headers.get("X-File-Access-Grant", ""),
        )
        return bytes_response(file, content)


class DeleteView(IdentityView):
    @extend_schema(request=None, responses={202: dto.AckSerializer, **ERRORS}, parameters=[CSRF])
    def delete(self, request: Any, file_id: UUID) -> Response:
        services.delete_owned(request.user.pk, file_id)
        return Response({"accepted": True}, status=202)


def shared(ticket_id: UUID, attachment_id: UUID) -> TicketShare:
    share = TicketShare.objects.filter(pk=attachment_id, ticket_id=ticket_id).first()
    if not share:
        raise IdentityError("ASSIGNED_EXPLICIT_SHARE_REQUIRED", 403)
    return share


class TicketGrantView(IdentityView):
    @extend_schema(
        request=dto.EmptySerializer,
        responses={201: dto.GrantSerializer, **ERRORS},
        parameters=[CSRF],
    )
    def post(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> Response:
        if request.data:
            raise IdentityError("INVALID_REQUEST", 400)
        share = shared(ticket_id, attachment_id)
        return Response(
            services.issue_grant(request.user, request.identity_session, share.asset_id, share),
            status=201,
        )


class TicketContentView(IdentityView):
    @extend_schema(
        responses={(200, "application/octet-stream"): bytes, **ERRORS}, parameters=[GRANT_HEADER]
    )
    def get(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> HttpResponse:
        share = shared(ticket_id, attachment_id)
        file, content = services.read_granted(
            request.user,
            request.identity_session,
            share.asset_id,
            request.headers.get("X-File-Access-Grant", ""),
            share,
        )
        return bytes_response(file, content)
