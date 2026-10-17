"""Provider boundaries with zero network egress in this bounded phase.

Named real-provider adapters fail closed until an actual account's free-only
enforcement, approvals and trustworthy physical usage controls are available.
An API key or database setting cannot turn these placeholders into transport.
"""

from dataclasses import dataclass, field
from math import isfinite
from typing import Protocol

from django.conf import settings

from ai_gateway.validation import AdapterRequest, Classification, build_prompt


@dataclass(frozen=True)
class AdapterResponse:
    output: object = field(repr=False)
    usage_units: int
    usage_unit: str


class AdapterFailure(Exception):
    """Metadata-only failure; ambiguous outcomes prohibit automatic retry.

    ``safe_to_retry`` is meaningful only for a positively known non-execution.
    Gateway receipt/attempt fencing is still required before another attempt.
    """

    def __init__(
        self,
        code: str,
        safe_to_retry: bool = False,
        outcome_unknown: bool = False,
    ) -> None:
        if safe_to_retry and outcome_unknown:
            raise ValueError("Retry cannot be authorized for an unknown outcome")
        self.code = code
        self.safe_to_retry = safe_to_retry
        self.outcome_unknown = outcome_unknown
        super().__init__(code)


class ProviderAdapter(Protocol):
    def execute(self, request: AdapterRequest, timeout_seconds: float) -> AdapterResponse: ...


def check_timeout(timeout_seconds: float) -> None:
    if (
        type(timeout_seconds) not in (int, float)
        or not isfinite(timeout_seconds)
        or not 0 < timeout_seconds <= 30
    ):
        raise AdapterFailure("INVALID_TIMEOUT")


class MockAdapter:
    """Deterministic local synthetic fixture, not an alternate private processor.

    Scripts are server-owned test fixtures, never a public request parameter.
    Only a count is retained; raw requests, responses and prompts are not logged.
    """

    OUTCOMES = frozenset(
        {"SUCCESS", "UNAVAILABLE", "RATE_LIMIT", "TIMEOUT", "INVALID_OUTPUT", "UNSUPPORTED_CLAIM"}
    )

    def __init__(
        self,
        script: tuple[str, ...] = (),
        usage_units: int = 1,
        usage_unit: str = "REQUESTS",
    ) -> None:
        if (
            not isinstance(script, tuple)
            or any(not isinstance(item, str) or item not in self.OUTCOMES for item in script)
            or type(usage_units) is not int
            or not 0 <= usage_units <= 1_000_000
            or usage_unit not in {"REQUESTS", "TOKENS", "NEURONS"}
        ):
            raise ValueError("Invalid synthetic adapter configuration")
        self.script = script
        self.usage_units = usage_units
        self.usage_unit = usage_unit
        self.calls = 0

    def execute(self, request: AdapterRequest, timeout_seconds: float) -> AdapterResponse:
        check_timeout(timeout_seconds)
        if (
            not settings.LOCAL
            or not request.synthetic
            or request.data_class != Classification.PUBLIC_SYNTHETIC
        ):
            raise AdapterFailure("MOCK_SYNTHETIC_ONLY")
        # Validate and construct the same isolated messages a future transport
        # must use. Neither the mock nor its output can execute a tool action.
        build_prompt(request)
        outcome = self.script[self.calls] if self.calls < len(self.script) else "SUCCESS"
        self.calls += 1
        if outcome == "UNAVAILABLE":
            raise AdapterFailure("PROVIDER_UNAVAILABLE", safe_to_retry=True)
        if outcome == "RATE_LIMIT":
            raise AdapterFailure("RATE_LIMITED", safe_to_retry=True)
        if outcome == "TIMEOUT":
            raise AdapterFailure("PROVIDER_TIMEOUT", outcome_unknown=True)
        if outcome == "INVALID_OUTPUT":
            output: object = {"tool_calls": [{"name": "alter_credit_balance"}]}
        elif outcome == "UNSUPPORTED_CLAIM":
            output = {
                "language": request.language,
                "claims": [
                    {"text": "Unsupported synthetic claim.", "citations": [request.evidence[0].id]}
                ],
            }
        else:
            output = {
                "language": request.language,
                "claims": [
                    {"text": evidence.text, "citations": [evidence.id]}
                    for evidence in request.evidence
                ],
            }
        return AdapterResponse(output, self.usage_units, self.usage_unit)


class _UnavailableRealAdapter:
    def execute(self, request: AdapterRequest, timeout_seconds: float) -> AdapterResponse:
        check_timeout(timeout_seconds)
        raise AdapterFailure("REAL_TRANSPORT_UNAVAILABLE")


class CloudflareAdapter(_UnavailableRealAdapter):
    """Workers AI transport blocked pending account/free-only/meter evidence."""


class GroqAdapter(_UnavailableRealAdapter):
    """Groq transport blocked pending account/terms/free-only/quota evidence."""


class GeminiFreeAdapter(_UnavailableRealAdapter):
    """Unpaid Gemini transport blocked; private data is never eligible."""


class OpenRouterFreeAdapter(_UnavailableRealAdapter):
    """Free-model routing blocked pending exact underlying processor evidence."""
