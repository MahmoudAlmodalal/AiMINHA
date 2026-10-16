import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any
from uuid import uuid4

from django.core.exceptions import DisallowedHost
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import CsrfViewMiddleware

logger = logging.getLogger("minhaai.http")


class MetadataFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "event": "http_request",
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "correlation_id": getattr(record, "correlation_id", None),
                "status": getattr(record, "status", None),
            }
        )


class RequestMetadataMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Never trust caller-provided correlation values or log body/URL/credentials.
        request.correlation_id = str(uuid4())
        try:
            request.get_host()  # Validate hosts even when the view doesn't use the host.
        except DisallowedHost:
            from core.errors import problem

            response = problem(request, 400, "INVALID_REQUEST", "Invalid request")
        else:
            response = self.get_response(request)
        response["X-Correlation-ID"] = request.correlation_id
        response["Cache-Control"] = "no-store"
        logger.info(
            "http_request",
            extra={"correlation_id": request.correlation_id, "status": response.status_code},
        )
        return response


class StrictCsrfMiddleware(CsrfViewMiddleware):
    """Enforce CSRF on anonymous unsafe DRF calls too, including future auth routes.

    DRF APIView normally exempts dispatch and relies on SessionAuthentication, which
    does not enforce anonymous CSRF. There are no token-exchange exceptions in Phase 05.
    """

    def process_view(
        self,
        request: HttpRequest,
        callback: Callable[..., Any],
        callback_args: tuple[Any, ...],
        callback_kwargs: dict[str, Any],
    ) -> HttpResponse | None:
        return super().process_view(request, partial(callback), callback_args, callback_kwargs)
