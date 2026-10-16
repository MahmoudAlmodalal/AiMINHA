from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from identity.models import RateBucket
from identity.security import IdentityError, PublicCatalogRead, digest, require_admin
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog import serializers as dto
from catalog import services
from catalog.models import Scholarship, Source

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 404, 409, 412, 429, 503)}


class CatalogAdminView(IdentityView):
    def initial(self, request: Any, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        require_admin(request.user, request.auth, "MODERATION")

    def handle_exception(self, exc: Exception) -> Response:
        try:
            services.record(
                getattr(self.request, "user", None),
                "catalog_request",
                outcome="DENY",
                resource=next((v for v in self.kwargs.values() if isinstance(v, UUID)), None),
                reason=exc.code
                if isinstance(exc, IdentityError)
                else f"HTTP_{getattr(exc, 'status_code', 500)}",
                correlation=self.request.correlation_id,
            )
        except Exception:
            exc = IdentityError("AUDIT_UNAVAILABLE", 503, "Request could not be safely audited")
        # Avoid recording catalog denials in the unrelated privacy event stream.
        return APIView.handle_exception(self, exc)

    def output(self, serializer: Any, value: Any, status: int = 200) -> Response:
        result = Response(serializer(value).data, status=status)
        if isinstance(value, dict) and "revision" in value:
            result["ETag"] = f'"{value["revision"]}"'
        return result

    def mutation(
        self,
        name: str,
        data: dict[str, Any],
        handler: Any,
        serializer: Any,
        status: int = 200,
        expected: int | None = None,
    ) -> Response:
        # Serialize before the idempotency receipt: only JSON-safe, scoped DTOs are cached.
        return self.execute(
            name,
            {"body": data, "revision": expected},
            lambda: dict(serializer(handler()).data),
            status=status,
        )


class SourceListView(CatalogAdminView):
    @extend_schema(
        operation_id="listCatalogSources", responses={200: dto.SourcePageSerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        with transaction.atomic():
            values = [
                services.source_data(source)
                for source in Source.objects.select_related("current").order_by("id")
            ]
            services.record(
                request.user, "source_registry_read", correlation=request.correlation_id
            )
        return self.output(dto.SourcePageSerializer, {"items": values})

    @extend_schema(
        operation_id="createCatalogSource",
        request=dto.SourceInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.SourceSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.SourceInputSerializer)
        # Reauthorize on a receipt replay too: it must not confer source-approval scope.
        if data["permission_status"] == "APPROVED":
            require_admin(request.user, request.auth, "SOURCE_APPROVAL")
        return self.mutation(
            "source_create",
            data,
            lambda: services.write_source(request.user, request.auth, data, request.correlation_id),
            dto.SourceSerializer,
            status=201,
        )


class SourceVersionView(CatalogAdminView):
    @extend_schema(
        operation_id="reviseCatalogSource",
        request=dto.SourceInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.SourceSerializer, **ERRORS},
    )
    def post(self, request: Any, source_id: UUID) -> Response:
        data = self.data(dto.SourceInputSerializer)
        expected = services.expected_revision(request)
        if data["permission_status"] == "APPROVED":
            require_admin(request.user, request.auth, "SOURCE_APPROVAL")
        return self.mutation(
            f"source_revise:{source_id}",
            data,
            lambda: services.write_source(
                request.user, request.auth, data, request.correlation_id, source_id, expected
            ),
            dto.SourceSerializer,
            expected=expected,
        )


class CandidateListView(CatalogAdminView):
    @extend_schema(
        operation_id="listCatalogCandidates",
        parameters=[dto.AdminSearchSerializer],
        responses={200: dto.AdminPageSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        params = dto.AdminSearchSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        query = Scholarship.objects.select_related("latest__source_revision").order_by("id")
        if "visibility" in data:
            query = query.filter(visibility=data["visibility"])
        start = (data["page"] - 1) * data["page_size"]
        with transaction.atomic():
            result = {
                "items": [
                    services.admin_data(item) for item in query[start : start + data["page_size"]]
                ],
                "total": query.count(),
                "page": data["page"],
                "page_size": data["page_size"],
            }
            services.record(request.user, "catalog_queue_read", correlation=request.correlation_id)
        return self.output(dto.AdminPageSerializer, result)

    @extend_schema(
        operation_id="createCatalogCandidate",
        request=dto.CandidateInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.AdminScholarshipSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.CandidateInputSerializer)
        return self.mutation(
            "catalog_candidate_create",
            data,
            lambda: services.write_candidate(
                request.user, request.auth, data, request.correlation_id
            ),
            dto.AdminScholarshipSerializer,
            status=201,
        )


class CandidateDetailView(CatalogAdminView):
    @extend_schema(
        operation_id="getCatalogCandidate",
        responses={200: dto.AdminScholarshipSerializer, **ERRORS},
    )
    def get(self, request: Any, scholarship_id: UUID) -> Response:
        with transaction.atomic():
            value = services.admin_data(services.get_scholarship(scholarship_id))
            services.record(
                request.user,
                "catalog_candidate_read",
                scholarship_id,
                correlation=request.correlation_id,
            )
        return self.output(dto.AdminScholarshipSerializer, value)


class CandidateVersionView(CatalogAdminView):
    @extend_schema(
        operation_id="reviseCatalogCandidate",
        request=dto.CandidateInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.AdminScholarshipSerializer, **ERRORS},
    )
    def post(self, request: Any, scholarship_id: UUID) -> Response:
        data = self.data(dto.CandidateInputSerializer)
        expected = services.expected_revision(request)
        return self.mutation(
            f"catalog_candidate_revise:{scholarship_id}",
            data,
            lambda: services.write_candidate(
                request.user, request.auth, data, request.correlation_id, scholarship_id, expected
            ),
            dto.AdminScholarshipSerializer,
            expected=expected,
        )


class ModerationView(CatalogAdminView):
    @extend_schema(
        operation_id="moderateCatalogCandidate",
        request=dto.ModerationSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.AdminScholarshipSerializer, **ERRORS},
    )
    def post(self, request: Any, scholarship_id: UUID) -> Response:
        data = self.data(dto.ModerationSerializer)
        expected = services.expected_revision(request)
        return self.mutation(
            f"catalog_moderate:{scholarship_id}",
            data,
            lambda: services.moderate(
                request.user, request.auth, scholarship_id, data, expected, request.correlation_id
            ),
            dto.AdminScholarshipSerializer,
            expected=expected,
        )


class PublicView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [PublicCatalogRead]

    def initial(self, request: Any, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        # Anonymous queries never leave this application or enter logs/audits as raw text.
        from datetime import timedelta

        from django.conf import settings

        now = timezone.now()
        with transaction.atomic():
            bucket, _ = RateBucket.objects.get_or_create(
                key=digest("public_catalog:" + request.META.get("REMOTE_ADDR", "unknown"))
            )
            bucket = RateBucket.objects.select_for_update().get(pk=bucket.pk)
            if now >= bucket.window_started + timedelta(minutes=15):
                bucket.window_started, bucket.attempts = now, 0
            bucket.attempts += 1
            bucket.save(update_fields=["window_started", "attempts"])
        if bucket.attempts > settings.CATALOG_PUBLIC_RATE_LIMIT:
            raise IdentityError("RATE_LIMITED", 429, "Too many requests; try later")


class PublicScholarshipListView(PublicView):
    @extend_schema(
        operation_id="searchScholarships",
        parameters=[dto.SearchInputSerializer],
        responses={200: dto.PublicPageSerializer, **ERRORS},
        auth=[],
    )
    def get(self, request: Any) -> Response:
        params = dto.SearchInputSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        return Response(dto.PublicPageSerializer(services.search(params.validated_data)).data)


class PublicScholarshipDetailView(PublicView):
    @extend_schema(
        operation_id="getScholarship",
        responses={200: dto.PublicScholarshipSerializer, **ERRORS},
        auth=[],
    )
    def get(self, request: Any, scholarship_id: UUID) -> Response:
        version = services.published_query().filter(scholarship_id=scholarship_id).first()
        if version is None:
            raise IdentityError("NOT_FOUND", 404, "Scholarship not found")
        return Response(dto.PublicScholarshipSerializer(services.public_data(version)).data)
