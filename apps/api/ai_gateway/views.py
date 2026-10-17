from typing import Any

from core.errors import ProblemSerializer
from credits import services as credits
from django.db import transaction
from drf_spectacular.utils import extend_schema
from identity.models import Account
from identity.security import IdentityError, VerifiedAdult, audit, require_student
from identity.views import IdentityView
from rest_framework.response import Response

from ai_gateway.serializers import AICapabilitiesSerializer
from ai_gateway.validation import Classification


class AICapabilitiesView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="getAICapabilities",
        responses={
            200: AICapabilitiesSerializer,
            **{x: ProblemSerializer for x in (400, 401, 403, 503)},
        },
    )
    def get(self, request: Any) -> Response:
        if request.query_params:
            raise IdentityError("INVALID_REQUEST", 400, "Selection comes from your session")
        with transaction.atomic():
            user = Account.objects.select_for_update().get(pk=request.user.pk)
            require_student(user)
            credits.session_check(user, request.auth)
            policy = credits.head_lock().policy
            audit(user, "ai_capabilities_read", correlation=request.correlation_id)
            return Response(
                AICapabilitiesSerializer(
                    {
                        "live_execution_available": False,
                        "mock_client_execution_available": False,
                        "classification_required": True,
                        "allowed_classifications": [str(x) for x in Classification],
                        "logical_daily_cap": policy.global_ai_cap,
                        "cloudflare_neurons_ceiling": 8000,
                        "reason_codes": [
                            "REAL_TRANSPORT_UNAVAILABLE",
                            "APPROVAL_AND_CAPACITY_REQUIRED",
                        ],
                    }
                ).data
            )
