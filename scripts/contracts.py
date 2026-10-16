"""Generate deployed surface and reject drift; future product APIs remain design-only."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def resolve(node: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in node:
        return resolve(document["components"]["schemas"][node["$ref"].rsplit("/", 1)[1]], document)
    return node


def compare_shape(
    expected: dict[str, Any], actual: dict[str, Any], document: dict[str, Any]
) -> None:
    actual = resolve(actual, document)
    for key in ("type", "format", "minimum", "maximum", "additionalProperties"):
        if key in expected and actual.get(key) != expected[key]:
            raise ValueError(f"Problem contract drift: {key}")
    if set(expected.get("required", [])) != set(actual.get("required", [])):
        raise ValueError("Problem contract drift: required fields")
    if "properties" in expected:
        if set(expected["properties"]) != set(actual.get("properties", {})):
            raise ValueError("Problem contract drift: properties")
        for key, value in expected["properties"].items():
            compare_shape(value, actual["properties"][key], document)
    if "items" in expected:
        compare_shape(expected["items"], actual["items"], document)


def validate(document: dict[str, Any]) -> None:
    if document["openapi"] != "3.1.0":
        raise ValueError("Runtime OpenAPI must use the documented 3.1 baseline.")
    authorized = {
        "/api/v1/health",
        "/api/v1/session/csrf",
        "/api/v1/session/login",
        "/api/v1/session",
        "/api/v1/session/logout",
        "/api/v1/session/reauthentications",
        "/api/v1/auth/registrations",
        "/api/v1/auth/email-verifications",
        "/api/v1/auth/email-verification-requests",
        "/api/v1/auth/password-reset-requests",
        "/api/v1/auth/password-resets",
        "/api/v1/auth/google/authorizations",
        "/api/v1/auth/google/callbacks",
        "/api/v1/consents/disclosures",
        "/api/v1/consents",
        "/api/v1/account/deletions",
        "/api/v1/account/deletions/impact",
        "/api/v1/account/recovery-requests",
        "/api/v1/account/restorations",
        "/api/v1/files",
        "/api/v1/files/{file_id}",
        "/api/v1/tickets/{ticket_id}/attachments",
        "/api/v1/tickets/{ticket_id}/attachments/{attachment_id}",
        "/api/v1/scholarships",
        "/api/v1/scholarships/{scholarship_id}",
        "/api/v1/admin/sources",
        "/api/v1/admin/sources/{source_id}/versions",
        "/api/v1/admin/scholarships",
        "/api/v1/admin/scholarships/{scholarship_id}",
        "/api/v1/admin/scholarships/{scholarship_id}/versions",
        "/api/v1/admin/scholarships/{scholarship_id}/moderation",
        "/api/v1/profile",
        "/api/v1/eligibility/evaluations",
        "/api/v1/eligibility/evaluations/{evaluation_id}",
        "/api/v1/admin/scholarships/{scholarship_id}/eligibility-rules",
        "/api/v1/wallet",
        "/api/v1/wallet/entries",
        "/api/v1/operations",
        "/api/v1/operations/{operation_id}",
        "/api/v1/admin/policies/credits",
    }
    if set(document["paths"]) != authorized:
        raise ValueError(
            "Only Phase 05–09 health, identity/privacy, catalog, "
            "eligibility and credit routes are authorized."
        )
    if set(document["paths"]["/api/v1/health"]) != {"get"}:
        raise ValueError("Health must expose only the safe GET contract.")
    baseline = json.loads((ROOT / "docs/architecture/openapi.json").read_text())
    compare_shape(
        baseline["components"]["schemas"]["Problem"],
        document["components"]["schemas"]["Problem"],
        document,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="minhaai-contracts-") as directory:
        schema = Path(directory) / "openapi.json"
        types = Path(directory) / "generated.ts"
        subprocess.run(
            [
                sys.executable,
                "apps/api/manage.py",
                "spectacular",
                "--format",
                "openapi-json",
                "--validate",
                "--fail-on-warn",
                "--file",
                str(schema),
            ],
            cwd=ROOT,
            check=True,
        )
        document = json.loads(schema.read_text())
        validate(document)
        schema.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        subprocess.run(
            [
                str(ROOT / "node_modules/.bin/openapi-typescript"),
                str(schema),
                "--output",
                str(types),
            ],
            cwd=ROOT,
            check=True,
        )
        for source, destination in (
            (schema, ROOT / "packages/contracts/openapi.json"),
            (types, ROOT / "packages/contracts/src/generated.ts"),
        ):
            if options.check:
                if not destination.exists() or source.read_bytes() != destination.read_bytes():
                    raise SystemExit(
                        f"Stale contract: {destination.relative_to(ROOT)}; run make contracts."
                    )
            else:
                destination.write_bytes(source.read_bytes())
    print("Runtime contract, architecture Problem compatibility and generated client checked.")


if __name__ == "__main__":
    main()
