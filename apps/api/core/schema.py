from typing import Any


def strict_objects(
    result: dict[str, Any],
    generator: Any,
    request: Any,
    public: bool,
) -> dict[str, Any]:
    """Public schema hook: close serializer objects without patching library internals."""
    for schema in result.get("components", {}).get("schemas", {}).values():
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
    return result
