"""Pure, versioned eligibility rules; no database, network, AI or grade equivalence.

Student-confirmed facts are declarations, not independently verified credentials.
The initial fit formula and CEFR ordering are explicit engineering policies, not
calibrated admissions models. Unknown evidence contributes neither success nor
failure and never increases coverage.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ENGINE_VERSION = "deterministic-v1"
WEIGHT_VERSION = "initial-30-25-20-15-10-v1"
MINIMUM_COVERAGE_BPS = 7000
WEIGHTS = {
    "ACADEMIC": 3000,
    "FIELD": 2500,
    "NATIONALITY_RESIDENCY": 2000,
    "LANGUAGE": 1500,
    "INTEREST": 1000,
}
FIELD_DOMAINS = {
    "nationalities": "NATIONALITY_RESIDENCY",
    "residency_country": "NATIONALITY_RESIDENCY",
    "degree_level": "ACADEMIC",
    "major": "FIELD",
    "qualification": "ACADEMIC",
    "gpa": "ACADEMIC",
    "languages": "LANGUAGE",
    "preferred_countries": "INTEREST",
}
GPA_MAXIMA = {"PERCENT_100": Decimal(100), "GPA_4_0": Decimal(4), "GPA_5_0": Decimal(5)}
CEFR_LEVELS = {level: index for index, level in enumerate(("A1", "A2", "B1", "B2", "C1", "C2"))}


def normalize_gpa(value: Any, scale: str) -> Decimal | None:
    """Return a bounded within-scale fraction; this is not cross-scale equivalence."""
    maximum = GPA_MAXIMA.get(scale)
    if maximum is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not number.is_finite() or number < 0 or number > maximum:
        return None
    return number / maximum


def _display(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(_display(item) or "Unknown" for item in value) or "None declared"
    if isinstance(value, dict):
        if "scale" in value:
            return f"{value.get('value', 'Unknown')} ({value.get('scale', 'UNKNOWN')})"
        if "language" in value:
            return f"{value.get('language', 'Unknown')}: {value.get('level') or 'Unknown'}"
        return "Unknown"
    return str(value)


def _expected(rule: dict[str, Any]) -> str:
    if rule.get("operator") == "GPA_MIN":
        return f"Minimum {_display(rule.get('gpa')) or 'Unknown'}"
    if rule.get("operator") == "LANGUAGE_MIN":
        return f"Minimum {_display(rule.get('language')) or 'Unknown'}"
    values = rule.get("values")
    return (_display(values) or "Unknown requirement") if values else "Unknown requirement"


def _gpa(actual: Any, expected: Any) -> tuple[str, str]:
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return "UNKNOWN", "REQUIREMENT_UNKNOWN"
    actual_scale, expected_scale = actual.get("scale"), expected.get("scale")
    if actual_scale not in GPA_MAXIMA or expected_scale not in GPA_MAXIMA:
        return "UNKNOWN", "GPA_SCALE_UNKNOWN"
    if actual_scale != expected_scale:
        return "UNKNOWN", "GPA_SCALE_MISMATCH"
    actual_value = normalize_gpa(actual.get("value"), actual_scale)
    expected_value = normalize_gpa(expected.get("value"), expected_scale)
    if actual_value is None or expected_value is None:
        return "UNKNOWN", "GPA_VALUE_INVALID"
    if actual_value >= expected_value:
        return "PASS", "GPA_MEETS_MINIMUM"
    return "FAIL", "GPA_BELOW_MINIMUM"


def _language(actual: Any, expected: Any) -> tuple[str, str]:
    if not isinstance(actual, list) or not isinstance(expected, dict):
        return "UNKNOWN", "REQUIREMENT_UNKNOWN"
    required_level = expected.get("level")
    required_language = expected.get("language")
    if (
        not isinstance(required_level, str)
        or required_level not in CEFR_LEVELS
        or not isinstance(required_language, str)
    ):
        return "UNKNOWN", "REQUIREMENT_UNKNOWN"
    matches = [
        item
        for item in actual
        if isinstance(item, dict)
        and str(item.get("language", "")).casefold() == required_language.casefold()
    ]
    if not matches:
        return "FAIL", "LANGUAGE_NOT_DECLARED"
    known: list[str] = []
    for item in matches:
        level = item.get("level")
        if isinstance(level, str) and level in CEFR_LEVELS:
            known.append(level)
    if any(CEFR_LEVELS[level] >= CEFR_LEVELS[required_level] for level in known):
        return "PASS", "LANGUAGE_MEETS_MINIMUM"
    if len(known) != len(matches):
        return "UNKNOWN", "LANGUAGE_LEVEL_UNKNOWN"
    return "FAIL", "LANGUAGE_BELOW_MINIMUM"


def _apply(profile: dict[str, Any], rule: dict[str, Any]) -> tuple[str, str]:
    field, domain = rule.get("field"), rule.get("domain")
    if not isinstance(field, str) or FIELD_DOMAINS.get(field) != domain:
        return "UNKNOWN", "UNSUPPORTED_RULE"
    if not rule.get("verified", False):
        return "UNKNOWN", "REQUIREMENT_UNVERIFIED"
    actual = profile.get(field)
    if actual is None:
        return "UNKNOWN", "PROFILE_UNKNOWN"
    if field not in profile.get("confirmed_fields", []):
        return "UNKNOWN", "PROFILE_UNCONFIRMED"
    operator = rule.get("operator")
    if operator == "GPA_MIN" and field == "gpa":
        return _gpa(actual, rule.get("gpa"))
    if operator == "LANGUAGE_MIN" and field == "languages":
        return _language(actual, rule.get("language"))
    expected = rule.get("values")
    if not isinstance(expected, list) or not expected:
        return "UNKNOWN", "REQUIREMENT_UNKNOWN"
    values = {item.casefold() for item in expected if isinstance(item, str)}
    if operator == "ONE_OF" and isinstance(actual, str):
        return ("PASS", "MATCH") if actual.casefold() in values else ("FAIL", "NO_MATCH")
    if operator == "INTERSECTS" and isinstance(actual, list) and field != "languages":
        matches = any(isinstance(item, str) and item.casefold() in values for item in actual)
        return ("PASS", "MATCH") if matches else ("FAIL", "NO_MATCH")
    return "UNKNOWN", "UNSUPPORTED_RULE"


def _rounded(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def evaluate(profile: dict[str, Any], ruleset: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate an exact approved rule snapshot against declared profile evidence.

    Each covered domain uses the arithmetic mean of its binary rule outcomes.
    The final fit averages those domain means using the available fixed weights;
    unknown domains stay null. Mandatory decisions are computed independently.
    """
    ruleset = ruleset or {}
    results: list[dict[str, Any]] = []
    missing: list[str] = []
    missing_reasons = {
        "PROFILE_UNKNOWN",
        "PROFILE_UNCONFIRMED",
        "GPA_SCALE_UNKNOWN",
        "GPA_SCALE_MISMATCH",
        "GPA_VALUE_INVALID",
        "LANGUAGE_LEVEL_UNKNOWN",
    }
    for rule in ruleset.get("rules", []):
        state, reason = _apply(profile, rule)
        field = rule.get("field", "")
        if reason in missing_reasons and field not in missing:
            missing.append(field)
        results.append(
            {
                "key": rule["key"],
                "criterion_index": rule["criterion_index"],
                "field": field,
                "domain": rule["domain"],
                "mandatory": rule["mandatory"],
                "result": state,
                "reason_code": reason,
                "expected_display": _expected(rule),
                "actual_display": _display(profile.get(field)),
                "evidence": {
                    "profile_field": field,
                    "profile_confirmed": field in profile.get("confirmed_fields", []),
                    "criterion_index": rule["criterion_index"],
                    "source_text": rule.get("evidence_text", ""),
                },
            }
        )
    if any(item["mandatory"] and item["result"] == "FAIL" for item in results):
        status = "INELIGIBLE"
    elif (
        not ruleset.get("complete", False)
        or not results
        or not any(item["result"] in {"PASS", "FAIL"} for item in results)
        or any(item["mandatory"] and item["result"] == "UNKNOWN" for item in results)
    ):
        status = "INSUFFICIENT_INFORMATION"
    else:
        status = "ELIGIBLE"
    domains: list[dict[str, Any]] = []
    weighted_fit = Decimal(0)
    coverage = 0
    for domain, weight in WEIGHTS.items():
        checks = [item for item in results if item["domain"] == domain]
        covered = bool(checks) and all(item["result"] != "UNKNOWN" for item in checks)
        score = None
        contribution = None
        if covered:
            coverage += weight
            exact_score = Decimal(sum(item["result"] == "PASS" for item in checks)) * 10000
            exact_score /= len(checks)
            score = _rounded(exact_score)
            exact_contribution = Decimal(weight) * exact_score / 10000
            contribution = _rounded(exact_contribution)
            weighted_fit += exact_contribution
        domains.append(
            {
                "domain": domain,
                "weight_bps": weight,
                "covered": covered,
                "score_bps": score,
                "contribution_bps": contribution,
                "reason_code": "VERIFIED_RULES_AND_CONFIRMED_DECLARATIONS"
                if covered
                else "NO_RULE_EVIDENCE"
                if not checks
                else "UNRESOLVED_RULE_EVIDENCE",
            }
        )
    sufficient = coverage >= MINIMUM_COVERAGE_BPS
    return {
        "status": status,
        "coverage_bps": coverage,
        "fit_score_bps": _rounded(weighted_fit * 10000 / coverage) if sufficient else None,
        "fit_status": "AVAILABLE" if sufficient else "INSUFFICIENT_COVERAGE",
        "confidence": "UNCALIBRATED",
        "domains": domains,
        "rules": results,
        "missing_fields": missing,
        "limitations": [
            "FIT_IS_NOT_ADMISSION_PROBABILITY",
            "STUDENT_CONFIRMED_IS_SELF_REPORTED",
            "WEIGHTS_UNCALIBRATED",
            "NO_CROSS_SCALE_GPA_EQUIVALENCE",
        ]
        + ([] if sufficient else ["INSUFFICIENT_VERIFIED_COVERAGE"]),
    }
