from typing import Any
from uuid import uuid4

from django.http import HttpRequest, HttpResponse, JsonResponse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class FieldErrorSerializer(serializers.Serializer):
    field = serializers.CharField()
    code = serializers.CharField()


@extend_schema_field({"type": "string", "format": "uri"})
class URIField(serializers.CharField):
    """Response URI reference, including the standard about:blank identifier."""


class ProblemSerializer(serializers.Serializer):
    type = URIField()
    title = serializers.CharField()
    status = serializers.IntegerField(min_value=400, max_value=599)
    code = serializers.CharField()
    detail = serializers.CharField()
    correlation_id = serializers.UUIDField()
    field_errors = FieldErrorSerializer(many=True, required=False)
    retry_after_seconds = serializers.IntegerField(min_value=0, required=False)


def problem_data(request: HttpRequest | Any, status: int, code: str, title: str) -> dict[str, Any]:
    return {
        "type": "about:blank",
        "title": title,
        "status": status,
        "code": code,
        "detail": title,
        "correlation_id": getattr(request, "correlation_id", str(uuid4())),
    }


def problem(request: HttpRequest, status: int, code: str, title: str) -> HttpResponse:
    response = JsonResponse(problem_data(request, status, code, title), status=status)
    response["Content-Type"] = "application/problem+json"
    response["Cache-Control"] = "no-store"
    return response


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    response = drf_exception_handler(exc, context)
    status = response.status_code if response is not None else 500
    codes = {
        400: ("INVALID_REQUEST", "Invalid request"),
        401: ("AUTHENTICATION_REQUIRED", "Authentication required"),
        403: ("FORBIDDEN", "Access denied"),
        404: ("NOT_FOUND", "Resource not found"),
        405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
        415: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
        429: ("RATE_LIMITED", "Too many requests"),
    }
    code, title = codes.get(status, ("INTERNAL_ERROR", "Request could not be completed"))
    headers = dict(response.items()) if response is not None else {}
    return Response(
        problem_data(context.get("request"), status, code, title),
        status=status,
        headers=headers,
        content_type="application/problem+json",
    )


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    return problem(request, 403, "CSRF_FAILED", "Request verification failed")


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    return problem(request, 400, "INVALID_REQUEST", "Invalid request")


def forbidden(request: HttpRequest, exception: Exception) -> HttpResponse:
    return problem(request, 403, "FORBIDDEN", "Access denied")


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return problem(request, 404, "NOT_FOUND", "Resource not found")


def server_error(request: HttpRequest) -> HttpResponse:
    return problem(request, 500, "INTERNAL_ERROR", "Request could not be completed")
