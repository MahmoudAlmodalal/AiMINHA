"""Conservative synthetic proof, never a semantic validator for real student data."""

from typing import Any

from identity.security import IdentityError

from documents.serializers import DocumentInputSerializer


def validate_grounded_output(payload: Any, evidence: list[str]) -> dict[str, Any]:
    """Only literal supplied facts may be emitted; transport/provider claims prove nothing.

    The closed private route never calls this. Evidence is server-authored synthetic
    input, never an untrusted provider's own declaration of its sources.
    """
    if (
        not isinstance(payload, dict)
        or set(payload) != {"kind", "language", "title", "content", "claims"}
        or not isinstance(payload["claims"], list)
        or not payload["claims"]
        or len(payload["claims"]) > 50
        or any(not isinstance(item, str) or item not in evidence for item in payload["claims"])
        or payload["content"] != "\n".join(payload["claims"])
        or payload["title"] not in {"Synthetic CV", "Synthetic document", "مستند اصطناعي"}
    ):
        raise IdentityError("DOCUMENT_OUTPUT_INVALID", 409, "Document output could not be verified")
    value = DocumentInputSerializer(
        data={key: val for key, val in payload.items() if key != "claims"}
    )
    if not value.is_valid():
        raise IdentityError("DOCUMENT_OUTPUT_INVALID", 409, "Document output could not be verified")
    return dict(value.validated_data)
