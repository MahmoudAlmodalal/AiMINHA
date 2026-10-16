from typing import Any
from uuid import UUID

from core.errors import ProblemSerializer
from django.contrib.auth import logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from privacy import services as privacy
from privacy.models import ConsentRecord, Disclosure, PrivateAsset, RetentionHead
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from identity import google, services
from identity import serializers as dto
from identity.models import Account, IdentitySession
from identity.security import (
    IdentityAuthentication,
    IdentityError,
    VerifiedAdult,
    audit,
    digest,
    require_student,
    session_data,
    throttle,
)

CSRF = OpenApiParameter("X-CSRFToken", str, OpenApiParameter.HEADER, required=True)
IDEMPOTENCY = OpenApiParameter("Idempotency-Key", str, OpenApiParameter.HEADER, required=True)
ETAG = OpenApiParameter("If-Match", str, OpenApiParameter.HEADER, required=True)
ERRORS = {
    400: ProblemSerializer,
    401: ProblemSerializer,
    403: ProblemSerializer,
    409: ProblemSerializer,
    412: ProblemSerializer,
    429: ProblemSerializer,
    503: ProblemSerializer,
}


class IdentityView(APIView):
    authentication_classes = [IdentityAuthentication]
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc: Exception) -> Response:
        # Service atomic blocks have unwound: denied events survive their rollback.
        status = getattr(exc, "status_code", 500)
        if status >= 400:
            actor = getattr(self.request, "user", None)
            resource = next(
                (value for value in self.kwargs.values() if isinstance(value, UUID)), None
            )
            try:
                audit(
                    actor,
                    "identity_privacy_request",
                    "DENY",
                    resource=resource,
                    reason=exc.code if isinstance(exc, IdentityError) else f"HTTP_{status}",
                    correlation=self.request.correlation_id,
                )
            except Exception:
                exc = IdentityError("AUDIT_UNAVAILABLE", 503, "Request could not be safely audited")
        return super().handle_exception(exc)

    def data(self, serializer: Any) -> dict[str, Any]:
        value = serializer(data=self.request.data)
        value.is_valid(raise_exception=True)
        return dict(value.validated_data)

    def ack(self) -> dict[str, Any]:
        return {"accepted": True, "correlation_id": self.request.correlation_id}

    def limit(self, name: str, email: str | None = None) -> None:
        throttle(name + ":ip", self.request.META.get("REMOTE_ADDR", "unknown"))
        if email:
            throttle(name + ":identity", email.strip().lower())

    def execute(self, name: str, data: dict[str, Any], handler: Any, status: int = 200) -> Response:
        result, code = services.command(self.request, name, data, handler, status)
        return Response(result, status=code)


class PublicIdentityView(IdentityView):
    permission_classes = [AllowAny]


class CsrfView(PublicIdentityView):
    @extend_schema(operation_id="getCsrf", responses={200: dto.CsrfSerializer}, auth=[])
    def get(self, request: Any) -> Response:
        if not request.session.session_key:
            request.session.create()
        return Response({"csrf_token": get_token(request)})


class RegistrationView(PublicIdentityView):
    @extend_schema(
        operation_id="registerStudent",
        request=dto.SignupSerializer,
        responses={202: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.SignupSerializer)
        self.limit("register", data["email"])

        def run() -> dict[str, Any]:
            services.register(data, request.correlation_id)
            return self.ack()

        return self.execute("register", data, run, 202)


class VerificationView(PublicIdentityView):
    @extend_schema(
        operation_id="verifyEmail",
        request=dto.ChallengeSerializer,
        responses={200: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.ChallengeSerializer)
        self.limit("verify")

        def run() -> dict[str, Any]:
            services.verify_email(data["challenge_token"], request.correlation_id)
            return self.ack()

        return self.execute("verify", data, run)


class LoginView(PublicIdentityView):
    @extend_schema(
        operation_id="login",
        request=dto.LoginSerializer,
        responses={200: dto.SessionSerializer, **ERRORS},
        parameters=[CSRF],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.LoginSerializer)
        self.limit("login", data["email"])
        return Response(services.sign_in(request, data))


class SessionView(IdentityView):
    @extend_schema(operation_id="getSession", responses={200: dto.SessionSerializer, **ERRORS})
    def get(self, request: Any) -> Response:
        return Response(session_data(request.user, request.identity_session))


class LogoutView(IdentityView):
    @extend_schema(
        operation_id="logout", request=None, responses={204: None, **ERRORS}, parameters=[CSRF]
    )
    def post(self, request: Any) -> Response:
        with transaction.atomic():
            user = Account.objects.select_for_update().get(pk=request.user.pk)
            IdentitySession.objects.filter(digest=digest(request.session.session_key)).update(
                revoked_at=timezone.now()
            )
            audit(user, "sign_out", correlation=request.correlation_id)
        logout(request)
        return Response(status=204)


class ReauthenticationView(IdentityView):
    @extend_schema(
        operation_id="reauthenticate",
        request=dto.PasswordSerializer,
        responses={200: dto.ReauthenticationSerializer, **ERRORS},
        parameters=[CSRF],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.PasswordSerializer)
        self.limit("reauthenticate", request.user.email)
        return Response(
            {"reauthentication_token": services.reauthenticate(request, data["password"])}
        )


class ResetRequestView(PublicIdentityView):
    @extend_schema(
        operation_id="requestPasswordReset",
        request=dto.EmailSerializer,
        responses={202: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.EmailSerializer)
        self.limit("reset_request", data["email"])

        def run() -> dict[str, Any]:
            services.reset_request(data["email"], request.correlation_id)
            return self.ack()

        return self.execute("reset_request", data, run, 202)


class ResetView(PublicIdentityView):
    @extend_schema(
        operation_id="completePasswordReset",
        request=dto.PasswordResetSerializer,
        responses={200: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.PasswordResetSerializer)
        self.limit("reset")

        def run() -> dict[str, Any]:
            services.reset_password(
                data["challenge_token"], data["password"], request.correlation_id
            )
            return self.ack()

        return self.execute("reset", data, run)


class VerificationRequestView(PublicIdentityView):
    @extend_schema(
        operation_id="requestEmailVerification",
        request=dto.EmailSerializer,
        responses={202: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.EmailSerializer)
        self.limit("verification_request", data["email"])

        def run() -> dict[str, Any]:
            services.reset_request(data["email"], request.correlation_id, "VERIFY_EMAIL")
            return self.ack()

        return self.execute("verification_request", data, run, 202)


class GoogleStartView(PublicIdentityView):
    @extend_schema(
        operation_id="startGoogleAuth",
        request=dto.GoogleStartSerializer,
        responses={200: dto.AuthorizationSerializer, **ERRORS},
        parameters=[CSRF],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.GoogleStartSerializer)
        self.limit("google_start")
        return Response(google.start(request, data["intent"]))


class GoogleCallbackView(PublicIdentityView):
    @extend_schema(
        operation_id="completeGoogleCallback",
        request=dto.GoogleCallbackSerializer,
        responses={200: dto.SessionSerializer, **ERRORS},
        parameters=[CSRF],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.GoogleCallbackSerializer)
        self.limit("google_callback")
        return Response(google.callback(request, data["code"], data["state"]))


class DisclosuresView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="listProcessingDisclosures",
        responses={200: dto.DisclosurePageSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        rows = list(Disclosure.objects.order_by("purpose", "-version"))
        latest = {row.purpose: row for row in reversed(rows)}
        return Response(
            {
                "items": [
                    {
                        "id": str(row.pk),
                        "version": row.version,
                        "purpose": row.purpose,
                        "disclosure": row.disclosure,
                        "available": row.available,
                    }
                    for row in latest.values()
                ],
                "next_cursor": None,
            }
        )


class ConsentsView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="listOwnConsents", responses={200: dto.ConsentPageSerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        rows = (
            ConsentRecord.objects.filter(account=request.user)
            .select_related("disclosure")
            .order_by("-version")
        )
        latest: dict[str, Any] = {}
        for row in rows:
            latest.setdefault(row.disclosure.purpose, row)
        request.user.refresh_from_db()
        return Response(
            {"items": [privacy.consent_data(row) for row in latest.values()], "next_cursor": None},
            headers={"ETag": f'"consent-{request.user.consent_version}"'},
        )

    @extend_schema(
        operation_id="recordConsent",
        request=dto.ConsentRequestSerializer,
        responses={201: dto.ConsentSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY, ETAG],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.ConsentRequestSerializer)
        return self.execute("consent", data, lambda: privacy.record_consent(request, **data), 201)


class DeletionsView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="confirmAccountDeletion",
        request=dto.DeletionInputSerializer,
        responses={201: dto.DeletionSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.DeletionInputSerializer)
        response = self.execute(
            "delete_account",
            data,
            lambda: privacy.delete_account(request, data["reauthentication_token"]),
            201,
        )
        logout(request)
        return response


class DeletionImpactView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="reviewAccountDeletionImpact",
        responses={200: dto.DeletionImpactSerializer, **ERRORS},
    )
    def get(self, request: Any) -> Response:
        with transaction.atomic():
            policy = RetentionHead.objects.select_related("policy").get(pk=1).policy
            try:
                privacy.legal_policy(policy)
                available = True
            except IdentityError:
                available = False
            request.session["deletion_impact"] = {
                "policy": str(policy.pk),
                "actor": str(request.user.pk),
                "seen_at": timezone.now().isoformat(),
            }
            audit(
                request.user,
                "deletion_impact_reviewed",
                resource=policy.pk,
                correlation=request.correlation_id,
            )
            return Response(
                {
                    "policy_id": str(policy.pk),
                    "recovery_days": policy.recovery_days,
                    "recovery_timezone": policy.recovery_timezone,
                    "cutoff_algorithm": policy.cutoff_algorithm,
                    "available": available,
                }
            )


class RecoveryRequestView(PublicIdentityView):
    @extend_schema(
        operation_id="requestDeletedAccountRecovery",
        request=dto.EmailSerializer,
        responses={202: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.EmailSerializer)
        self.limit("recovery", data["email"])

        def run() -> dict[str, Any]:
            privacy.request_recovery(data["email"], request.correlation_id)
            return self.ack()

        return self.execute("recovery", data, run, 202)


class RestorationsView(PublicIdentityView):
    @extend_schema(
        operation_id="restoreDeletionPendingAccount",
        request=dto.ChallengeSerializer,
        responses={200: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
        auth=[],
    )
    def post(self, request: Any) -> Response:
        data = self.data(dto.ChallengeSerializer)
        self.limit("restore")

        def run() -> dict[str, Any]:
            privacy.restore_account(data["challenge_token"], request.correlation_id)
            return self.ack()

        return self.execute("restore", data, run)


class FilesView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="listOwnFileMetadata", responses={200: dto.FilePageSerializer, **ERRORS}
    )
    def get(self, request: Any) -> Response:
        with transaction.atomic():
            actor = Account.objects.select_for_update().get(pk=request.user.pk)
            require_student(actor)
            audit(actor, "private_file_library_list", correlation=request.correlation_id)
            rows = list(PrivateAsset.objects.filter(owner=actor).order_by("pk")[:100])
            return Response(
                {"items": [privacy.asset_data(row) for row in rows], "next_cursor": None}
            )


class FileView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(operation_id="getFile", responses={200: dto.FileSerializer, **ERRORS})
    def get(self, request: Any, file_id: UUID) -> Response:
        return Response(privacy.owned_asset(request.user, file_id))


class SharesView(IdentityView):
    permission_classes = [VerifiedAdult]

    @extend_schema(
        operation_id="shareExactTicketAsset",
        request=dto.ShareInputSerializer,
        responses={201: dto.ShareSerializer, **ERRORS},
        parameters=[CSRF, IDEMPOTENCY],
    )
    def post(self, request: Any, ticket_id: UUID) -> Response:
        data = self.data(dto.ShareInputSerializer)
        return self.execute(
            "share:" + str(ticket_id),
            data,
            lambda: privacy.share_asset(request, ticket_id, data["asset_id"]),
            201,
        )


class ShareView(IdentityView):
    @extend_schema(
        operation_id="readAssignedTicketAttachmentMetadata",
        responses={200: dto.FileSerializer, **ERRORS},
    )
    def get(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> Response:
        return Response(
            privacy.ticket_asset(request.user, request.identity_session, ticket_id, attachment_id)
        )

    @extend_schema(
        operation_id="revokeTicketShare",
        request=None,
        responses={202: dto.AckSerializer, **ERRORS},
        parameters=[CSRF, ETAG],
    )
    def delete(self, request: Any, ticket_id: UUID, attachment_id: UUID) -> Response:
        privacy.revoke_share(request, ticket_id, attachment_id)
        return Response(self.ack(), status=202)
