from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from identity.security import IdentityError, VerifiedAdult
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response

from documents import serializers as dto
from documents import services

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 409, 412, 429, 503)}


def revision(request: Any) -> int:
    value = request.headers.get("If-Match", "")
    if len(value) < 3 or len(value) > 12 or not value.startswith('"') or not value.endswith('"'):
        raise IdentityError("PRECONDITION_REQUIRED", 412, "A current document revision is required")
    try:
        result = int(value[1:-1])
    except ValueError as exc:
        raise IdentityError(
            "PRECONDITION_REQUIRED", 412, "A current document revision is required"
        ) from exc
    if result < 0:
        raise IdentityError("PRECONDITION_REQUIRED", 412, "A current document revision is required")
    return result


class StudentView(IdentityView):
    permission_classes = [VerifiedAdult]


class CapabilitiesView(StudentView):
    @extend_schema(
        operation_id="getDocumentCapabilities",
        responses={200: dto.CapabilitiesSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        with transaction.atomic():
            services.student(request.user, request.auth)
        return Response(
            {
                "manual_editing": True,
                "private_ai": False,
                "manual_fallback": True,
                "reason": "PRIVATE_AI_PIPELINE_UNAVAILABLE",
            }
        )


class DocumentsView(StudentView):
    @extend_schema(
        operation_id="listOwnedDocuments", responses={200: dto.DocumentPageSerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        if request.query_params:
            raise IdentityError(
                "INVALID_REQUEST", 400, "Document ownership comes from your session"
            )
        items = services.list_documents(request.user, request.auth, request.correlation_id)
        return Response(
            dto.DocumentPageSerializer(
                {
                    "items": [services.document_data(row) for row in items],
                    "next_cursor": None,
                }
            ).data
        )

    @extend_schema(
        operation_id="createManualDocument",
        request=dto.DocumentInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.DocumentSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.DocumentInputSerializer)
        with transaction.atomic():
            services.student(request.user, request.auth)
            result = self.execute(
                "document_create",
                data,
                lambda: {
                    "document_id": str(
                        services.create_document(
                            request.user, request.auth, data, request.correlation_id
                        ).pk
                    )
                },
                201,
            )
            value = services.read_document(
                request.user, request.auth, UUID(result.data["document_id"])
            )
            return Response(
                dto.DocumentSerializer(services.document_data(value)).data,
                status=201,
                headers={"ETag": f'"{value.revision}"'},
            )


class DocumentView(StudentView):
    @extend_schema(
        operation_id="getOwnedDocument", responses={200: dto.DocumentSerializer, **ERRORS}
    )
    def get(self, request: Any, document_id: UUID) -> Response:
        value = services.read_document(
            request.user, request.auth, document_id, request.correlation_id
        )
        return Response(
            dto.DocumentSerializer(services.document_data(value)).data,
            headers={"ETag": f'"{value.revision}"'},
        )


class VersionsView(StudentView):
    @extend_schema(
        operation_id="listDocumentVersions", responses={200: dto.VersionPageSerializer, **ERRORS}
    )
    def get(self, request: Any, document_id: UUID) -> Response:
        values = services.list_versions(
            request.user, request.auth, document_id, request.correlation_id
        )
        return Response(
            dto.VersionPageSerializer(
                {
                    "items": [services.version_data(row) for row in values],
                    "next_cursor": None,
                }
            ).data
        )

    @extend_schema(
        operation_id="saveManualDocumentVersion",
        request=dto.VersionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.DocumentSerializer, **ERRORS},
    )
    def post(self, request: Any, document_id: UUID) -> Response:
        data, expected = self.data(dto.VersionInputSerializer), revision(request)
        with transaction.atomic():
            services.read_document(request.user, request.auth, document_id)
            result = self.execute(
                f"document_save:{document_id}",
                {"body": data, "revision": expected},
                lambda: {
                    "version_id": str(
                        services.save_version(
                            request.user,
                            request.auth,
                            document_id,
                            data,
                            expected,
                            request.correlation_id,
                        ).current_id
                    )
                },
            )
            value = services.read_document(request.user, request.auth, document_id)
            if str(value.current_id) != result.data["version_id"]:
                raise IdentityError("STALE_REVISION", 412, "Reload the current document")
            return Response(
                dto.DocumentSerializer(services.document_data(value)).data,
                headers={"ETag": f'"{value.revision}"'},
            )


class RestoreView(StudentView):
    @extend_schema(
        operation_id="restoreDocumentVersion",
        request=dto.VersionReferenceSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.DocumentSerializer, **ERRORS},
    )
    def post(self, request: Any, document_id: UUID) -> Response:
        data, expected = self.data(dto.VersionReferenceSerializer), revision(request)
        with transaction.atomic():
            services.read_document(request.user, request.auth, document_id)
            services.version_owned(request.user, document_id, data["version_id"])
            result = self.execute(
                f"document_restore:{document_id}",
                {"body": data, "revision": expected},
                lambda: {
                    "version_id": str(
                        services.restore_version(
                            request.user,
                            request.auth,
                            document_id,
                            data["version_id"],
                            expected,
                            request.correlation_id,
                        ).current_id
                    )
                },
            )
            value = services.read_document(request.user, request.auth, document_id)
            if str(value.current_id) != result.data["version_id"]:
                raise IdentityError("STALE_REVISION", 412, "Reload the current document")
            return Response(
                dto.DocumentSerializer(services.document_data(value)).data,
                headers={"ETag": f'"{value.revision}"'},
            )


class ApprovalView(StudentView):
    @extend_schema(
        operation_id="approveExactDocumentVersion",
        request=dto.ApprovalInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.VersionSerializer, **ERRORS},
    )
    def post(self, request: Any, document_id: UUID) -> Response:
        data = self.data(dto.ApprovalInputSerializer)
        with transaction.atomic():
            services.read_document(request.user, request.auth, document_id)
            services.version_owned(request.user, document_id, data["version_id"])
            result = self.execute(
                f"document_approve:{document_id}",
                data,
                lambda: {
                    "version_id": str(
                        services.approve_version(
                            request.user,
                            request.auth,
                            document_id,
                            data["version_id"],
                            data["content_hash"],
                            data["confirm"],
                            request.correlation_id,
                        ).pk
                    )
                },
            )
            value = services.version_owned(
                request.user, document_id, UUID(result.data["version_id"])
            )
            return Response(dto.VersionSerializer(services.version_data(value)).data)


class ExportView(StudentView):
    @extend_schema(
        operation_id="exportApprovedDocumentVersion",
        request=dto.ExportInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.ExportSerializer, **ERRORS},
    )
    def post(self, request: Any, document_id: UUID) -> Response:
        data = self.data(dto.ExportInputSerializer)
        # Unlike other commands, no receipt transaction surrounds scanning I/O.
        # Exact immutable version/format uniqueness and storage key provide dedupe.
        services.bind_export_request(
            request.user,
            request.auth,
            document_id,
            data["version_id"],
            data["format"],
            request.headers.get("Idempotency-Key", ""),
        )
        value = services.export_version(
            request.user,
            request.auth,
            document_id,
            data["version_id"],
            data["format"],
            request.correlation_id,
        )
        return Response(dto.ExportSerializer(services.export_data(value)).data)


class CompareView(StudentView):
    @extend_schema(
        operation_id="compareDocumentVersions",
        responses={200: dto.CompareSerializer, **ERRORS},
        parameters=[
            OpenApiParameter("left", UUID, required=True),
            OpenApiParameter("right", UUID, required=True),
        ],
    )
    def get(self, request: Any, document_id: UUID) -> Response:
        try:
            left, right = UUID(request.query_params["left"]), UUID(request.query_params["right"])
        except (KeyError, ValueError) as exc:
            raise IdentityError("INVALID_REQUEST", 400, "Choose two saved versions") from exc
        services.read_document(request.user, request.auth, document_id, request.correlation_id)
        result = {
            name: services.version_data(services.version_owned(request.user, document_id, key))
            for name, key in (("left", left), ("right", right))
        }
        return Response(dto.CompareSerializer(result).data)


def consent_first(request: Any, consent: bool) -> None:
    with transaction.atomic():
        services.student(request.user, request.auth)
    if consent is not True:
        raise IdentityError(
            "DOCUMENT_AI_CONSENT_REQUIRED", 403, "Explicit consent is required; use manual entry"
        )


class GenerationView(StudentView):
    @extend_schema(
        operation_id="requestPrivateDocumentGeneration",
        request=dto.GenerateInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses=ERRORS,
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.GenerateInputSerializer)
        consent_first(request, data["consent"])
        raise IdentityError(
            "PRIVATE_AI_PIPELINE_UNAVAILABLE",
            503,
            "Private AI unavailable; use manual document entry",
        )


class ExtractionView(StudentView):
    @extend_schema(
        operation_id="requestPrivateCVExtraction",
        request=dto.ExtractInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses=ERRORS,
    )
    def post(self, request: Any) -> Response:
        from privacy import services as privacy

        data = self.data(dto.ExtractInputSerializer)
        consent_first(request, data["consent"])
        privacy.owned_asset(request.user, data["asset_id"])
        raise IdentityError(
            "PRIVATE_AI_PIPELINE_UNAVAILABLE",
            503,
            "Private CV extraction unavailable; enter facts manually",
        )
