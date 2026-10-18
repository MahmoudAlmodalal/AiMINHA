from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from identity.security import IdentityError, VerifiedAdult, audit
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response

from applications import serializers as dto
from applications import services
from applications.models import (
    STATES,
    Application,
    SavedScholarship,
    SubmittedArtifactDeletionRequest,
)
from applications.rounds import round_options

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 409, 412, 429, 503)}


def revision(request: Any) -> int:
    value = request.headers.get("If-Match", "")
    if len(value) < 3 or len(value) > 12 or not value.startswith('"') or not value.endswith('"'):
        raise IdentityError(
            "PRECONDITION_REQUIRED", 412, "A current application revision is required"
        )
    try:
        expected = int(value[1:-1])
    except ValueError as exc:
        raise IdentityError(
            "PRECONDITION_REQUIRED", 412, "A current application revision is required"
        ) from exc
    if expected < 1:
        raise IdentityError(
            "PRECONDITION_REQUIRED", 412, "A current application revision is required"
        )
    return expected


def respond(value: Application, *, status: int = 200) -> Response:
    return Response(
        dto.ApplicationSerializer(services.application_data(value)).data,
        status=status,
        headers={"ETag": f'"{value.revision}"'},
    )


class StudentView(IdentityView):
    permission_classes = [VerifiedAdult]

    def initial(self, request: Any, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        if request.query_params and not (
            request.method == "GET"
            and isinstance(self, (RoundOptionsView, ApplicationsView, SavedScholarshipsView))
        ):
            raise IdentityError("INVALID_REQUEST", 400, "Ownership comes from your session")

    def mutation(
        self,
        request: Any,
        application_id: UUID,
        data: dict[str, Any],
        expected: int,
        name: str,
        handler: Any,
    ) -> Response:
        with transaction.atomic():
            services.read_application(request.user, request.auth, application_id)

            def run() -> dict[str, Any]:
                value = handler()
                return {"application_id": str(value.pk), "revision": value.revision}

            receipt = self.execute(
                f"application_{name}:{application_id}", {"body": data, "revision": expected}, run
            )
            value = services.read_application(request.user, request.auth, application_id)
            if receipt.data["revision"] != value.revision:
                raise IdentityError("STALE_REVISION", 412, "Reload the current tracker")
            return respond(value)


class ApplicationsView(StudentView):
    @extend_schema(
        operation_id="listApplications",
        responses={200: dto.ApplicationPageSerializer, **ERRORS},
        parameters=[dto.PageInputSerializer],
    )
    def get(self, request: Any) -> Response:
        query = dto.PageInputSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page, size = query.validated_data["page"], query.validated_data["page_size"]
        with transaction.atomic():
            values = services.list_applications(
                request.user, request.auth, request.correlation_id, page=page, page_size=size
            )
            counts = {state: 0 for state in STATES}
            for item in (
                Application.objects.filter(owner=request.user)
                .values("state")
                .annotate(total=services.models.Count("pk"))
            ):
                counts[item["state"]] = item["total"]
            return Response(
                dto.ApplicationPageSerializer(
                    {
                        "items": [services.application_data(row) for row in values],
                        "next_cursor": None,
                        "counts": counts,
                        "page": page,
                        "page_size": size,
                        "total": sum(counts.values()),
                    }
                ).data
            )

    @extend_schema(
        operation_id="createApplication",
        request=dto.CreateSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.ApplicationSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.CreateSerializer)
        with transaction.atomic():
            services.student(request.user, request.auth)
            result = self.execute(
                "application_create",
                data,
                lambda: {
                    "application_id": str(
                        services.create_application(
                            request.user,
                            request.auth,
                            data["scholarship_id"],
                            data["round_key"],
                            request.correlation_id,
                        ).pk
                    )
                },
                201,
            )
            value = services.read_application(
                request.user, request.auth, UUID(result.data["application_id"])
            )
            return respond(value, status=201)


class RoundOptionsView(StudentView):
    @extend_schema(
        operation_id="getApplicationRoundOptions",
        responses={200: dto.RoundOptionsSerializer, **ERRORS},
        parameters=[OpenApiParameter("scholarship_id", UUID, required=True)],
    )
    def get(self, request: Any) -> Response:
        if set(request.query_params) != {"scholarship_id"}:
            raise IdentityError("INVALID_REQUEST", 400, "Select a scholarship")
        try:
            scholarship_id = UUID(request.query_params["scholarship_id"])
        except ValueError as exc:
            raise IdentityError("INVALID_REQUEST", 400, "Select a scholarship") from exc
        with transaction.atomic():
            services.student(request.user, request.auth)
            value = services.current_catalog(scholarship_id)
            audit(
                request.user,
                "application_round_options",
                resource=scholarship_id,
                correlation=request.correlation_id,
            )
            return Response(
                dto.RoundOptionsSerializer(
                    {
                        "scholarship_id": scholarship_id,
                        "scholarship_version_id": value.pk,
                        "items": round_options(value.rounds),
                    }
                ).data
            )


class ApplicationView(StudentView):
    @extend_schema(
        operation_id="getApplication", responses={200: dto.ApplicationSerializer, **ERRORS}
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        return respond(
            services.read_application(
                request.user, request.auth, application_id, request.correlation_id
            )
        )


class HistoryView(StudentView):
    @extend_schema(
        operation_id="getApplicationHistory", responses={200: dto.HistorySerializer, **ERRORS}
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        value = services.read_application(
            request.user, request.auth, application_id, request.correlation_id
        )
        return Response(
            dto.HistorySerializer(
                {
                    "items": [
                        services.event_data(row) for row in value.events.order_by("sequence")
                    ],
                    "next_cursor": None,
                }
            ).data
        )


class NotesView(StudentView):
    @extend_schema(
        operation_id="editApplicationNotes",
        request=dto.NotesInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ApplicationSerializer, **ERRORS},
    )
    def put(self, request: Any, application_id: UUID) -> Response:
        data, expected = self.data(dto.NotesInputSerializer), revision(request)
        return self.mutation(
            request,
            application_id,
            data,
            expected,
            "notes",
            lambda: services.edit_notes(
                request.user,
                request.auth,
                application_id,
                data["notes"],
                expected,
                request.correlation_id,
            ),
        )


class TransitionView(StudentView):
    @extend_schema(
        operation_id="transitionApplication",
        request=dto.TransitionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ApplicationSerializer, **ERRORS},
    )
    def post(self, request: Any, application_id: UUID) -> Response:
        data, expected = self.data(dto.TransitionInputSerializer), revision(request)
        return self.mutation(
            request,
            application_id,
            data,
            expected,
            "transition",
            lambda: services.transition(
                request.user, request.auth, application_id, data, expected, request.correlation_id
            ),
        )


class CorrectionView(StudentView):
    @extend_schema(
        operation_id="correctApplicationEvidence",
        request=dto.CorrectionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ApplicationSerializer, **ERRORS},
    )
    def post(self, request: Any, application_id: UUID) -> Response:
        data, expected = self.data(dto.CorrectionInputSerializer), revision(request)
        return self.mutation(
            request,
            application_id,
            data,
            expected,
            "correction",
            lambda: services.correct_evidence(
                request.user, request.auth, application_id, data, expected, request.correlation_id
            ),
        )


class RebaseView(StudentView):
    @extend_schema(
        operation_id="rebaseApplication",
        request=dto.RebaseInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ApplicationSerializer, **ERRORS},
    )
    def post(self, request: Any, application_id: UUID) -> Response:
        data, expected = self.data(dto.RebaseInputSerializer), revision(request)
        return self.mutation(
            request,
            application_id,
            data,
            expected,
            "rebase",
            lambda: services.rebase_application(
                request.user,
                request.auth,
                application_id,
                expected,
                data["confirm"],
                request.correlation_id,
            ),
        )


class RequirementsView(StudentView):
    @extend_schema(
        operation_id="getApplicationRequirements",
        responses={200: dto.RequirementsSerializer, **ERRORS},
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        value = services.read_application(
            request.user, request.auth, application_id, request.correlation_id
        )
        return Response(
            dto.RequirementsSerializer(
                {
                    "requirements_known": value.requirements_known,
                    "items": services.requirements_data(value),
                }
            ).data
        )


class ArtifactView(StudentView):
    @extend_schema(
        operation_id="selectApplicationArtifact",
        request=dto.ArtifactInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ApplicationSerializer, **ERRORS},
    )
    def put(self, request: Any, application_id: UUID, requirement_key: str) -> Response:
        data, expected = self.data(dto.ArtifactInputSerializer), revision(request)
        return self.mutation(
            request,
            application_id,
            data,
            expected,
            "artifact:" + requirement_key,
            lambda: services.select_artifact(
                request.user,
                request.auth,
                application_id,
                requirement_key,
                data,
                expected,
                request.correlation_id,
            ),
        )


class ArtifactOptionsView(StudentView):
    @extend_schema(
        operation_id="getApplicationArtifactOptions",
        responses={200: dto.ArtifactOptionsSerializer, **ERRORS},
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        value = services.read_application(
            request.user, request.auth, application_id, request.correlation_id
        )
        return Response(dto.ArtifactOptionsSerializer(services.artifact_options(value)).data)


class SubmittedArtifactsView(StudentView):
    @extend_schema(
        operation_id="getApplicationSubmittedArtifacts",
        responses={200: dto.SubmissionPageSerializer, **ERRORS},
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        value = services.read_application(
            request.user, request.auth, application_id, request.correlation_id
        )
        rows = (
            services.SubmissionArtifact.objects.filter(application=value)
            .select_related("event", "requirement", "version")
            .order_by("requirement__position")
        )
        return Response(
            dto.SubmissionPageSerializer(
                {"items": [services.submission_data(row) for row in rows], "next_cursor": None}
            ).data
        )


class DeletionRequestsView(StudentView):
    @extend_schema(
        operation_id="getApplicationArtifactDeletionRequests",
        responses={200: dto.DeletionPageSerializer, **ERRORS},
    )
    def get(self, request: Any, application_id: UUID) -> Response:
        value = services.read_application(
            request.user, request.auth, application_id, request.correlation_id
        )
        rows = SubmittedArtifactDeletionRequest.objects.filter(
            application=value, owner=request.user
        ).order_by("created_at", "pk")
        return Response(
            dto.DeletionPageSerializer(
                {"items": [services.deletion_data(row) for row in rows], "next_cursor": None}
            ).data
        )

    @extend_schema(
        operation_id="requestApplicationArtifactDeletion",
        request=dto.DeletionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={202: dto.DeletionSerializer, **ERRORS},
    )
    def post(self, request: Any, application_id: UUID) -> Response:
        data = self.data(dto.DeletionInputSerializer)
        with transaction.atomic():
            services.read_application(request.user, request.auth, application_id)
            result = self.execute(
                f"application_deletion:{application_id}",
                data,
                lambda: {
                    "request_id": str(
                        services.request_artifact_deletion(
                            request.user,
                            request.auth,
                            application_id,
                            data["artifact_id"],
                            data["reason"],
                            request.correlation_id,
                        ).pk
                    )
                },
                202,
            )
            value = SubmittedArtifactDeletionRequest.objects.get(
                pk=result.data["request_id"], owner=request.user, application_id=application_id
            )
            return Response(dto.DeletionSerializer(services.deletion_data(value)).data, status=202)


class SavedScholarshipsView(StudentView):
    @extend_schema(
        operation_id="listSavedScholarships",
        responses={200: dto.SavedPageSerializer, **ERRORS},
        parameters=[dto.PageInputSerializer],
    )
    def get(self, request: Any) -> Response:
        query = dto.PageInputSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page, size = query.validated_data["page"], query.validated_data["page_size"]
        with transaction.atomic():
            services.student(request.user, request.auth)
            rows = (
                SavedScholarship.objects.filter(owner=request.user, active=True)
                .select_related("scholarship__published_version")
                .order_by("created_at", "pk")
            )
            total = rows.count()
            values = rows[(page - 1) * size : page * size]
            audit(request.user, "scholarship_saved_list", correlation=request.correlation_id)
            return Response(
                dto.SavedPageSerializer(
                    {
                        "items": [services.saved_data(row) for row in values],
                        "next_cursor": None,
                        "total": total,
                        "page": page,
                        "page_size": size,
                    }
                ).data
            )

    @extend_schema(
        operation_id="saveScholarship",
        request=dto.SavedInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.SavedSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.SavedInputSerializer)
        with transaction.atomic():
            services.student(request.user, request.auth)
            result = self.execute(
                "scholarship_save",
                data,
                lambda: {
                    "saved_id": str(
                        services.set_saved(
                            request.user,
                            request.auth,
                            data["scholarship_id"],
                            active=True,
                            correlation=request.correlation_id,
                        ).pk
                    )
                },
            )
            value = SavedScholarship.objects.get(pk=result.data["saved_id"], owner=request.user)
            return Response(
                dto.SavedSerializer(services.saved_data(value)).data,
                headers={"ETag": f'"{value.revision}"'},
            )


class SavedScholarshipView(StudentView):
    @extend_schema(
        operation_id="unsaveScholarship",
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        request=None,
        responses={200: dto.SavedSerializer, **ERRORS},
    )
    def delete(self, request: Any, scholarship_id: UUID) -> Response:
        if request.data:
            raise IdentityError("INVALID_REQUEST", 400, "No body is accepted")
        expected = revision(request)
        with transaction.atomic():
            services.student(request.user, request.auth)
            result = self.execute(
                f"scholarship_unsave:{scholarship_id}",
                {"revision": expected},
                lambda: {
                    "saved_id": str(
                        services.set_saved(
                            request.user,
                            request.auth,
                            scholarship_id,
                            active=False,
                            expected=expected,
                            correlation=request.correlation_id,
                        ).pk
                    )
                },
            )
            value = SavedScholarship.objects.get(pk=result.data["saved_id"], owner=request.user)
            return Response(
                dto.SavedSerializer(services.saved_data(value)).data,
                headers={"ETag": f'"{value.revision}"'},
            )
