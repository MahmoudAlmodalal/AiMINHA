from typing import Any
from uuid import UUID

from catalog import services as catalog
from catalog.views import CatalogAdminView
from core.errors import ProblemSerializer
from django.db import transaction
from drf_spectacular.utils import extend_schema
from identity.security import IdentityError, VerifiedAdult
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response

from eligibility import serializers as dto
from eligibility import services

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 409, 412, 429, 503)}


def expected_revision(request: Any) -> int:
    if len(request.headers.get("If-Match", "")) > 12:
        raise IdentityError("PRECONDITION_REQUIRED", 412, "A current revision is required")
    return catalog.expected_revision(request)


class StudentView(IdentityView):
    permission_classes = [VerifiedAdult]


class ProfileView(StudentView):
    @extend_schema(
        operation_id="getEligibilityProfile", responses={200: dto.ProfileSerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        if request.query_params:
            raise IdentityError("INVALID_REQUEST", 400, "Profile selection comes from your session")
        value = services.read_profile(request.user, request.auth, request.correlation_id)
        return Response(
            dto.ProfileSerializer(value).data, headers={"ETag": f'"{value["revision"]}"'}
        )

    @extend_schema(
        operation_id="saveEligibilityProfile",
        request=dto.ProfileFactsSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.ProfileSerializer, **ERRORS},
    )
    def put(self, request: Any) -> Response:
        data = self.data(dto.ProfileFactsSerializer)
        expected = expected_revision(request)
        with transaction.atomic():
            services.student(request.user, request.auth)
            response = self.execute(
                "eligibility_profile_save",
                {"body": data, "revision": expected},
                lambda: {
                    "version_id": services.write_profile(
                        request.user, request.auth, data, expected, request.correlation_id
                    )["version_id"]
                },
            )
            current = services.read_profile(request.user, request.auth, request.correlation_id)
            if current["version_id"] != response.data["version_id"]:
                raise IdentityError("PROFILE_CHANGED", 409, "Reload the current profile")
            return Response(
                dto.ProfileSerializer(current).data,
                status=response.status_code,
                headers={"ETag": f'"{current["revision"]}"'},
            )


class EvaluationListView(StudentView):
    @extend_schema(
        operation_id="evaluateEligibility",
        request=dto.EvaluationInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.EvaluationSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.EvaluationInputSerializer)
        with transaction.atomic():
            user = services.student(request.user, request.auth)
            services.inputs(user, data)  # Current authorization also applies to receipt replays.
            response = self.execute(
                "eligibility_evaluate",
                data,
                lambda: {
                    "evaluation_id": services.evaluate_profile(
                        user, request.auth, data, request.correlation_id
                    )["id"]
                },
                status=201,
            )
            value = services.read_evaluation(
                user, request.auth, UUID(response.data["evaluation_id"]), request.correlation_id
            )
            return Response(dto.EvaluationSerializer(value).data, status=response.status_code)


class EvaluationDetailView(StudentView):
    @extend_schema(
        operation_id="getEligibilityEvaluation", responses={200: dto.EvaluationSerializer, **ERRORS}
    )
    def get(self, request: Any, evaluation_id: UUID) -> Response:
        value = services.read_evaluation(
            request.user, request.auth, evaluation_id, request.correlation_id
        )
        return Response(dto.EvaluationSerializer(value).data)


class RuleSetView(CatalogAdminView):
    @extend_schema(
        operation_id="getEligibilityRuleBasis", responses={200: dto.RuleHeadSerializer, **ERRORS}
    )
    def get(self, request: Any, scholarship_id: UUID) -> Response:
        return Response(
            dto.RuleHeadSerializer(
                services.read_rules(
                    request.user, request.auth, scholarship_id, request.correlation_id
                )
            ).data
        )

    @extend_schema(
        operation_id="reviewEligibilityRuleBasis",
        request=dto.RuleSetInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.RuleHeadSerializer, **ERRORS},
    )
    def post(self, request: Any, scholarship_id: UUID) -> Response:
        data = self.data(dto.RuleSetInputSerializer)
        expected = expected_revision(request)
        with transaction.atomic():
            # Receipt storage is opaque metadata; current authorization and evidence
            # are reconstructed even on a replay of an earlier reviewed command.
            services.authorize_rule_review(
                request.user, request.auth, scholarship_id, data["scholarship_version_id"]
            )
            response = self.execute(
                f"eligibility_rules_review:{scholarship_id}",
                {"body": data, "revision": expected},
                lambda: {
                    "rule_set_id": services.write_rules(
                        request.user,
                        request.auth,
                        scholarship_id,
                        data,
                        expected,
                        request.correlation_id,
                    )["rule_set"]["id"]
                },
            )
            value = services.read_rules(
                request.user, request.auth, scholarship_id, request.correlation_id
            )
            if value["rule_set"] is None or value["rule_set"]["id"] != response.data["rule_set_id"]:
                raise IdentityError("STALE_REVISION", 412, "Review the current rule basis")
            return Response(
                dto.RuleHeadSerializer(value).data,
                status=response.status_code,
                headers={"ETag": f'"{value["revision"]}"'},
            )
