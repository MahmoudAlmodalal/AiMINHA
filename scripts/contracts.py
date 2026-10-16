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
    if set(document["paths"]) != {"/api/v1/health"}:
        raise ValueError("Phase 05 authorizes only the bootstrap health route.")
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
