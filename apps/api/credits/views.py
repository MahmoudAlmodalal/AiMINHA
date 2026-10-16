from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.db import transaction
from drf_spectacular.utils import extend_schema
from identity.models import Account
from identity.security import IdentityError, VerifiedAdult, audit
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response

from credits import serializers as dto
from credits import services

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 409, 412, 429, 503)}


def no_selection(request: Any) -> None:
    if request.query_params:
        raise IdentityError("INVALID_REQUEST", 400, "Selection comes from your session")


def pagination(request: Any) -> dict[str, Any]:
    if any(len(values) != 1 for _, values in request.query_params.lists()):
        raise IdentityError("INVALID_REQUEST", 400, "Invalid pagination")
    value = dto.CreditPaginationSerializer(data=request.query_params.dict())
    value.is_valid(raise_exception=True)
    return dict(value.validated_data)


class WalletView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(operation_id="getWallet", responses={200: dto.WalletSerializer, **ERRORS})
    def get(self, request: Any) -> Response:
        no_selection(request)
        return Response(
            dto.WalletSerializer(
                services.read_wallet(request.user, request.auth, request.correlation_id)
            ).data
        )


class EntriesView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="listWalletEntries",
        parameters=[dto.CreditPaginationSerializer],
        responses={200: dto.CreditEntriesSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        value = services.read_history(
            request.user,
            request.auth,
            **pagination(request),
            entries=True,
            correlation=request.correlation_id,
        )
        return Response(dto.CreditEntriesSerializer(value).data)


class OperationsView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="listCreditOperations",
        parameters=[dto.CreditPaginationSerializer],
        responses={200: dto.CreditOperationsSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        value = services.read_history(
            request.user, request.auth, **pagination(request), correlation=request.correlation_id
        )
        return Response(dto.CreditOperationsSerializer(value).data)


class OperationView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="getCreditOperation", responses={200: dto.CreditOperationSerializer, **ERRORS}
    )
    def get(self, request: Any, operation_id: UUID) -> Response:
        no_selection(request)
        return Response(
            dto.CreditOperationSerializer(
                services.read_operation(
                    request.user, request.auth, operation_id, request.correlation_id
                )
            ).data
        )


class CreditPolicyView(IdentityView):
    @extend_schema(
        operation_id="getCreditPolicy", responses={200: dto.CreditPolicySerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        no_selection(request)
        with transaction.atomic():
            user = Account.objects.select_for_update().get(pk=request.user.pk)
            services.policy_admin(user, request.auth)
            policy = services.head_lock().policy
            audit(
                user, "credit_policy_read", resource=policy.pk, correlation=request.correlation_id
            )
            return Response(
                dto.CreditPolicySerializer(services.policy_data(policy)).data,
                headers={"ETag": f'"{policy.version}"'},
            )

    @extend_schema(
        operation_id="publishCreditPolicy",
        request=dto.CreditPolicyInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.CreditPolicySerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.CreditPolicyInputSerializer)
        expected = request.headers.get("If-Match", "")
        if (
            len(expected) > 12
            or not expected.startswith('"')
            or not expected.endswith('"')
            or not expected[1:-1].isdigit()
        ):
            raise IdentityError(
                "PRECONDITION_REQUIRED", 412, "A current policy version is required"
            )
        with transaction.atomic():
            user = Account.objects.select_for_update().get(pk=request.user.pk)
            services.policy_admin(user, request.auth)
            response = self.execute(
                "credit_policy_publish",
                {"body": data, "version": int(expected[1:-1])},
                lambda: {
                    "policy_id": str(
                        services.publish_policy(
                            user, request.auth, data, int(expected[1:-1]), request.correlation_id
                        ).pk
                    )
                },
            )
            policy = services.head_lock().policy
            if str(policy.pk) != response.data["policy_id"]:
                raise IdentityError("STALE_REVISION", 412, "Review the current credit policy")
            return Response(
                dto.CreditPolicySerializer(services.policy_data(policy)).data,
                headers={"ETag": f'"{policy.version}"'},
            )
