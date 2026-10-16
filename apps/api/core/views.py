from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import ProblemSerializer


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok"])


class HealthView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    @extend_schema(
        operation_id="health_retrieve",
        auth=[],
        description=(
            "Public process liveness only. Does not assert database or external service readiness."
        ),
        responses={
            200: HealthSerializer,
            (400, "application/problem+json"): ProblemSerializer,
            (403, "application/problem+json"): ProblemSerializer,
            (405, "application/problem+json"): ProblemSerializer,
            (500, "application/problem+json"): ProblemSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        return Response(HealthSerializer({"status": "ok"}).data)
