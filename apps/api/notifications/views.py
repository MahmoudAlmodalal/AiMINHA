from typing import Any
from uuid import UUID

from catalog.services import expected_revision
from core.errors import ProblemSerializer
from drf_spectacular.utils import extend_schema
from identity.security import IdentityError, VerifiedAdult
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications import serializers as dto
from notifications import services

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 404, 409, 412, 503)}


class StudentNotificationView(IdentityView):
    permission_classes = [VerifiedAdult]

    def handle_exception(self, exc: Exception) -> Response:
        try:
            services.record(
                getattr(self.request, "user", None),
                "notification_request",
                next((value for value in self.kwargs.values() if isinstance(value, UUID)), None),
                outcome="DENY",
                reason=exc.code
                if isinstance(exc, IdentityError)
                else f"HTTP_{getattr(exc, 'status_code', 500)}",
                correlation=self.request.correlation_id,
            )
        except Exception:
            exc = IdentityError("AUDIT_UNAVAILABLE", 503, "Request could not be safely audited")
        return APIView.handle_exception(self, exc)


class InboxView(StudentNotificationView):
    @extend_schema(
        operation_id="listNotifications",
        parameters=[dto.InboxQuerySerializer],
        responses={200: dto.InboxSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        params = dto.InboxQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        value = services.inbox(
            request.user, request.auth, params.validated_data, request.correlation_id
        )
        return Response(dto.InboxSerializer(value).data)


class MarkReadView(StudentNotificationView):
    @extend_schema(
        operation_id="markNotificationRead",
        request=dto.EmptyInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.NotificationSerializer, **ERRORS},
    )
    def post(self, request: Any, notification_id: UUID) -> Response:
        data = self.data(dto.EmptyInputSerializer)
        # Do not cache a possibly superseded destination/deadline projection in a receipt.
        self.execute(
            f"notification_read:{notification_id}",
            data,
            lambda: {
                "id": services.mark_read(
                    request.user, request.auth, notification_id, request.correlation_id
                )["id"]
            },
        )
        value = services.mark_read(
            request.user, request.auth, notification_id, request.correlation_id
        )
        return Response(dto.NotificationSerializer(value).data)


class PreferenceView(StudentNotificationView):
    @extend_schema(
        operation_id="getNotificationPreferences",
        responses={200: dto.PreferenceSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        value = services.read_preferences(request.user, request.auth, request.correlation_id)
        return Response(
            dto.PreferenceSerializer(value).data, headers={"ETag": f'"{value["revision"]}"'}
        )

    @extend_schema(
        operation_id="updateNotificationPreferences",
        request=dto.PreferenceInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.PreferenceSerializer, **ERRORS},
    )
    def put(self, request: Any) -> Response:
        data = self.data(dto.PreferenceInputSerializer)
        expected = expected_revision(request)
        response = self.execute(
            "notification_preferences_update",
            {"body": data, "revision": expected},
            lambda: dict(
                dto.PreferenceSerializer(
                    services.write_preferences(
                        request.user, request.auth, data, expected, request.correlation_id
                    )
                ).data
            ),
        )
        # Receipt replay must not expose stale preferences as the live current revision.
        value = services.read_preferences(request.user, request.auth, request.correlation_id)
        if response.data["revision"] != value["revision"]:
            raise IdentityError("STALE_REVISION", 412, "Preferences changed; reload before editing")
        return Response(
            dto.PreferenceSerializer(value).data, headers={"ETag": f'"{value["revision"]}"'}
        )
