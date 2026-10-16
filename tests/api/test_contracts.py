import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("contracts", ROOT / "scripts/contracts.py")
contracts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contracts)


def runtime_schema():
    return json.loads((ROOT / "packages/contracts/openapi.json").read_text())


def test_runtime_problem_contract_matches_architecture():
    contracts.validate(runtime_schema())


def test_unplanned_route_fails_phase_gate():
    schema = runtime_schema()
    schema["paths"]["/api/v1/private"] = {"get": {}}
    with pytest.raises(ValueError, match="only the bootstrap health"):
        contracts.validate(schema)


def test_problem_type_drift_fails_gate():
    schema = copy.deepcopy(runtime_schema())
    schema["components"]["schemas"]["Problem"]["properties"]["status"]["type"] = "string"
    with pytest.raises(ValueError, match="contract drift"):
        contracts.validate(schema)
