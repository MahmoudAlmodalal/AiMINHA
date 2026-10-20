from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from drf_spectacular.utils import extend_schema
from identity.security import IdentityError, VerifiedAdult
from identity.views import CSRF, ETAG, IDEMPOTENCY, IdentityView
from privacy import services as privacy
from rest_framework.response import Response

from support import serializers as dto
from support import services

ERRORS = {code: ProblemSerializer for code in (400, 401, 403, 404, 409, 412, 429, 503)}


class SupportView(IdentityView):
    permission_classes = [VerifiedAdult]

    def respond(self, value: dict[str, Any], *, status: int = 200) -> Response:
        response = Response(dto.TicketSerializer(value).data, status=status)
        response["ETag"] = f'"{value["row_version"]}"'
        response["Cache-Control"] = "no-store, private"
        return response


class TicketsView(SupportView):
    @extend_schema(
        operation_id="listSupportTickets",
        parameters=[dto.PageInputSerializer],
        responses={200: dto.TicketPageSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        params = dto.PageInputSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        value = services.list_tickets(
            request.user,
            request.auth,
            params.validated_data["page"],
            params.validated_data["page_size"],
            request.correlation_id,
        )
        return Response(dto.TicketPageSerializer(value).data)

    @extend_schema(
        operation_id="createSupportTicket",
        request=dto.TicketCreateSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={201: dto.TicketSerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.TicketCreateSerializer)
        result = self.execute(
            "support_ticket_create",
            data,
            lambda: services.create_ticket(
                request.user, request.auth, data, request.correlation_id
            ),
            201,
        )
        return self.respond(result.data, status=201)


class TicketView(SupportView):
    @extend_schema(
        operation_id="readSupportTicket",
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.read_ticket(request.user, request.auth, ticket_id, request.correlation_id)
        return self.respond(value)


class MessagesView(SupportView):
    @extend_schema(
        operation_id="listSupportMessages",
        responses={200: dto.MessagePageSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.read_messages(
            request.user, request.auth, ticket_id, request.correlation_id
        )
        return Response(dto.MessagePageSerializer(value).data)

    @extend_schema(
        operation_id="postSupportMessage",
        request=dto.MessageInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.MessageInputSerializer)
        services.authorize_owner(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_message:{ticket_id}",
            data,
            lambda: services.post_message(
                request.user,
                request.auth,
                ticket_id,
                data["body"],
                data["request_human"],
                request.correlation_id,
            ),
        )
        return self.respond(result.data)


class AiReplyView(SupportView):
    @extend_schema(
        operation_id="requestSupportAiReply",
        request=None,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.AiReplySerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        if request.data:
            raise IdentityError("INVALID_REQUEST", 400, "This request takes no body")
        services.authorize_owner(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_ai_reply:{ticket_id}",
            {},
            lambda: services.ai_reply(
                request.user, request.auth, ticket_id, request.correlation_id
            ),
        )
        return Response(dto.AiReplySerializer(result.data).data)


class TransitionView(SupportView):
    @extend_schema(
        operation_id="transitionSupportTicket",
        request=dto.SupportTransitionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.SupportTransitionInputSerializer)
        expected = services.expected_revision(request)
        services.authorize_owner(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_transition:{ticket_id}",
            {"body": data, "revision": expected},
            lambda: services.student_transition(
                request.user,
                request.auth,
                ticket_id,
                data["to_state"],
                data["reason_code"],
                expected,
                request.correlation_id,
            ),
        )
        return self.respond(result.data)


class HistoryView(SupportView):
    @extend_schema(
        operation_id="readSupportTicketHistory",
        responses={200: dto.HistoryPageSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.read_history(request.user, request.auth, ticket_id, request.correlation_id)
        return Response(dto.HistoryPageSerializer(value).data)


class SlaView(SupportView):
    @extend_schema(
        operation_id="readSupportTicketSla",
        responses={200: dto.SlaSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.sla_view(
            request.user,
            request.auth,
            ticket_id,
            admin=False,
            correlation=request.correlation_id,
        )
        return Response(dto.SlaSerializer(value).data)


class RatingView(SupportView):
    @extend_schema(
        operation_id="readSupportTicketRating",
        responses={200: dto.RatingSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.read_rating(request.user, request.auth, ticket_id, request.correlation_id)
        return Response(dto.RatingSerializer(value).data)

    @extend_schema(
        operation_id="rateSupportTicket",
        request=dto.RatingInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.RatingSerializer, **ERRORS},
    )
    def put(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.RatingInputSerializer)
        expected = services.expected_revision(request)
        services.authorize_owner(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_rating:{ticket_id}",
            {"body": data, "revision": expected},
            lambda: services.rate_ticket(
                request.user,
                request.auth,
                ticket_id,
                data["rating"],
                expected,
                request.correlation_id,
            ),
        )
        return Response(dto.RatingSerializer(result.data).data)


class AttachmentsView(SupportView):
    @extend_schema(
        operation_id="listSupportTicketAttachments",
        responses={200: dto.AttachmentPageSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.attachments(request.user, request.auth, ticket_id, request.correlation_id)
        return Response(dto.AttachmentPageSerializer(value).data)

    @extend_schema(
        operation_id="shareExactTicketAsset",
        request=dto.ShareInputSerializer,
        responses={201: dto.ShareSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.ShareInputSerializer)
        services.authorize_owner(request.user, request.auth, ticket_id)
        result = self.execute(
            "share:" + str(ticket_id),
            data,
            lambda: privacy.share_asset(request, ticket_id, data["asset_id"]),
            201,
        )
        return Response(dto.ShareSerializer(result.data).data, status=201)


class ShareDetailView(IdentityView):
    """One explicit ticket share: assigned agents read it, the owner revokes it."""

    @extend_schema(
        operation_id="readAssignedTicketAttachmentMetadata",
        responses={200: dto.AttachmentSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> Response:
        value = services.attachment_metadata(
            request.user, request.identity_session, ticket_id, attachment_id
        )
        return Response(dto.AttachmentSerializer(value).data)

    @extend_schema(
        operation_id="revokeTicketShare",
        request=None,
        responses={202: dto.SupportAckSerializer, **ERRORS},
        parameters=[CSRF, ETAG],
    )
    def delete(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> Response:
        privacy.revoke_share(request, ticket_id, attachment_id)
        return Response({"accepted": True}, status=202)


class AdminSupportView(IdentityView):
    """Administrator surface. Every action re-checks scope, MFA and assignment."""

    def respond(self, value: dict[str, Any], *, status: int = 200) -> Response:
        response = Response(dto.TicketSerializer(value).data, status=status)
        response["ETag"] = f'"{value["row_version"]}"'
        response["Cache-Control"] = "no-store, private"
        return response


class AdminQueueView(AdminSupportView):
    @extend_schema(
        operation_id="listAdminSupportTickets",
        parameters=[dto.QueueInputSerializer],
        responses={200: dto.QueuePageSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        params = dto.QueueInputSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        value = services.queue(
            request.user,
            request.auth,
            params.validated_data["page"],
            params.validated_data["page_size"],
            params.validated_data.get("state"),
            params.validated_data.get("priority"),
            request.correlation_id,
        )
        return Response(dto.QueuePageSerializer(value).data)


class AdminAssignmentView(AdminSupportView):
    @extend_schema(
        operation_id="assignSupportTicket",
        request=dto.AssignmentInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.QueueItemSerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.AssignmentInputSerializer)
        expected = services.expected_revision(request)
        services.require_support_admin(request.user, request.auth, services.ASSIGNMENT_SCOPE)
        result = self.execute(
            f"support_assignment:{ticket_id}",
            {"body": data, "revision": expected},
            lambda: services.assign_ticket(
                request.user,
                request.auth,
                ticket_id,
                data["agent_id"],
                data["reason_code"],
                expected,
                request.correlation_id,
            ),
        )
        return Response(dto.QueueItemSerializer(result.data).data)


class AdminMessagesView(AdminSupportView):
    @extend_schema(
        operation_id="listAdminSupportMessages",
        responses={200: dto.MessagePageSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.admin_messages(
            request.user, request.auth, ticket_id, request.correlation_id
        )
        return Response(dto.MessagePageSerializer(value).data)

    @extend_schema(
        operation_id="postAdminSupportMessage",
        request=dto.MessageInputSerializer,
        parameters=[CSRF, IDEMPOTENCY],
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.MessageInputSerializer)
        services.authorize_assigned(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_admin_message:{ticket_id}",
            data,
            lambda: services.admin_post_message(
                request.user,
                request.auth,
                ticket_id,
                data["body"],
                data["request_human"],
                request.correlation_id,
            ),
        )
        return self.respond(result.data)


class AdminTransitionView(AdminSupportView):
    @extend_schema(
        operation_id="transitionAdminSupportTicket",
        request=dto.SupportTransitionInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.SupportTransitionInputSerializer)
        expected = services.expected_revision(request)
        services.authorize_assigned(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_admin_transition:{ticket_id}",
            {"body": data, "revision": expected},
            lambda: services.admin_transition(
                request.user,
                request.auth,
                ticket_id,
                data["to_state"],
                data["reason_code"],
                expected,
                request.correlation_id,
            ),
        )
        return self.respond(result.data)


class AdminClassificationView(AdminSupportView):
    @extend_schema(
        operation_id="classifySupportTicket",
        request=dto.ClassificationInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={200: dto.TicketSerializer, **ERRORS},
    )
    def put(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.ClassificationInputSerializer)
        expected = services.expected_revision(request)
        services.authorize_assigned(request.user, request.auth, ticket_id)
        result = self.execute(
            f"support_classification:{ticket_id}",
            {"body": data, "revision": expected},
            lambda: services.classify_ticket(
                request.user,
                request.auth,
                ticket_id,
                data["category"],
                data["priority"],
                data["reason_code"],
                expected,
                request.correlation_id,
            ),
        )
        return self.respond(result.data)


class AdminAttachmentsView(AdminSupportView):
    @extend_schema(
        operation_id="listAdminSupportTicketAttachments",
        responses={200: dto.AttachmentPageSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.admin_attachments(
            request.user, request.auth, ticket_id, request.correlation_id
        )
        return Response(dto.AttachmentPageSerializer(value).data)


class AdminSlaView(AdminSupportView):
    @extend_schema(
        operation_id="readAdminSupportTicketSla",
        responses={200: dto.SlaSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID) -> Response:
        value = services.sla_view(
            request.user,
            request.auth,
            ticket_id,
            admin=True,
            correlation=request.correlation_id,
        )
        return Response(dto.SlaSerializer(value).data)


class AdminMetricsView(AdminSupportView):
    @extend_schema(
        operation_id="readAdminSupportMetrics",
        responses={200: dto.MetricsSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        value = services.metrics(request.user, request.auth, request.correlation_id)
        return Response(dto.MetricsSerializer(value).data)


class AdminPolicyView(AdminSupportView):
    @extend_schema(
        operation_id="publishAdminSupportPolicy",
        request=dto.PolicyInputSerializer,
        parameters=[CSRF, IDEMPOTENCY, ETAG],
        responses={201: dto.PolicySerializer, **ERRORS},
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.PolicyInputSerializer)
        expected = services.expected_revision(request)
        services.require_support_admin(request.user, request.auth, services.POLICY_SCOPE)
        payload = {
            "timezone": data["timezone"],
            "working_weekdays": data["working_weekdays"],
            "opens_local": data["opens_local"],
            "closes_local": data["closes_local"],
            "holidays": data["holidays"],
            "targets": data["targets"],
            "ai_daily_messages": data["ai_daily_messages"],
            "closure_days": data["closure_days"],
            "reopen_days": data["reopen_days"],
            "rating_edit_days": data["rating_edit_days"],
            "warning_percent": data["warning_percent"],
            "effective_at": data["effective_at"],
            "reason": data["reason_code"],
        }
        self.execute(
            "support_policy_publish",
            {"body": payload, "revision": expected},
            lambda: services.publish_policy(
                request.user, request.auth, payload, expected, request.correlation_id
            ),
            201,
        )
        value = services.read_policy(request.user, request.auth, request.correlation_id)
        return Response(dto.PolicySerializer(value).data, status=201)


class AdminPolicyCurrentView(AdminSupportView):
    @extend_schema(
        operation_id="readAdminSupportPolicy",
        responses={200: dto.PolicySerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        value = services.read_policy(request.user, request.auth, request.correlation_id)
        return Response(dto.PolicySerializer(value).data)
