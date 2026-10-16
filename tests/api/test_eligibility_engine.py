"""Deterministic branches use authored evidence, never an admissions model."""

from copy import deepcopy
from decimal import Decimal

import pytest
from eligibility.engine import FIELD_DOMAINS, WEIGHTS, evaluate, normalize_gpa


def rule(field="major", **changes):
    return {
        "key": "synthetic-criterion",
        "criterion_index": 0,
        "field": field,
        "domain": FIELD_DOMAINS[field],
        "operator": "ONE_OF",
        "values": ["engineering"],
        "gpa": None,
        "language": None,
        "mandatory": True,
        "verified": True,
        "evidence_text": "Authored synthetic criterion; not a real scholarship.",
        **changes,
    }


def check(profile, *rules, complete=True):
    return evaluate(profile, {"complete": complete, "rules": list(rules)})


def confirmed(**facts):
    return {**facts, "confirmed_fields": list(facts)}


@pytest.mark.parametrize(
    ("field", "accepted", "rejected", "values", "operator"),
    [
        ("major", "Engineering", "history", ["engineering"], "ONE_OF"),
        ("degree_level", "MASTER", "BACHELOR", ["MASTER", "PHD"], "ONE_OF"),
        ("qualification", "BACHELOR", "SECONDARY", ["BACHELOR"], "ONE_OF"),
        ("residency_country", "PS", "FR", ["PS"], "ONE_OF"),
        ("nationalities", ["JO", "PS"], ["FR"], ["PS"], "INTERSECTS"),
        ("preferred_countries", ["DE", "FR"], ["US"], ["DE"], "INTERSECTS"),
    ],
)
def test_every_membership_rule_has_match_fail_missing_and_unconfirmed_branches(
    field, accepted, rejected, values, operator
):
    requirement = rule(field, values=values, operator=operator)
    for actual, expected in [(accepted, "PASS"), (rejected, "FAIL")]:
        output = check(confirmed(**{field: actual}), requirement)
        assert output["rules"][0]["result"] == expected
        assert output["status"] == ("ELIGIBLE" if expected == "PASS" else "INELIGIBLE")
    for actual in [{}, {field: None, "confirmed_fields": [field]}, {field: accepted}]:
        output = check(actual, requirement)
        assert output["status"] == "INSUFFICIENT_INFORMATION"
        assert output["rules"][0]["result"] == "UNKNOWN"
        assert output["missing_fields"] == [field]


@pytest.mark.parametrize("field", ["nationalities", "preferred_countries"])
def test_confirmed_empty_inventory_is_explicit_none_but_unconfirmed_empty_is_unknown(field):
    requirement = rule(field, operator="INTERSECTS", values=["PS"])
    assert check(confirmed(**{field: []}), requirement)["rules"][0]["result"] == "FAIL"
    assert check({field: []}, requirement)["rules"][0]["result"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("value", "scale", "expected"),
    [
        ("80", "PERCENT_100", Decimal("0.8")),
        ("3.2", "GPA_4_0", Decimal("0.8")),
        ("4", "GPA_5_0", Decimal("0.8")),
        ("0", "GPA_4_0", Decimal(0)),
        ("100", "PERCENT_100", Decimal(1)),
        ("4", "GPA_4_0", Decimal(1)),
        ("5", "GPA_5_0", Decimal(1)),
        ("3.5", "UNKNOWN", None),
        ("3.5", "GPA_10", None),
        ("-0.01", "GPA_4_0", None),
        ("4.01", "GPA_4_0", None),
        ("100.01", "PERCENT_100", None),
        ("5.01", "GPA_5_0", None),
        ("NaN", "GPA_4_0", None),
        ("Infinity", "GPA_4_0", None),
        (True, "GPA_4_0", None),
        (None, "GPA_4_0", None),
        ("", "GPA_4_0", None),
    ],
)
def test_only_explicit_bounded_known_gpa_scales_normalize(value, scale, expected):
    assert normalize_gpa(value, scale) == expected


@pytest.mark.parametrize(
    "scale,minimum", [("PERCENT_100", "80"), ("GPA_4_0", "3.2"), ("GPA_5_0", "4")]
)
def test_gpa_minimum_same_scale_exact_boundary_below_and_above(scale, minimum):
    requirement = rule("gpa", operator="GPA_MIN", gpa={"value": minimum, "scale": scale})
    for offset, expected in [
        (Decimal("-0.01"), "FAIL"),
        (Decimal(0), "PASS"),
        (Decimal("0.01"), "PASS"),
    ]:
        actual = {"value": str(Decimal(minimum) + offset), "scale": scale}
        output = check(confirmed(gpa=actual), requirement)
        assert output["rules"][0]["result"] == expected


@pytest.mark.parametrize(
    ("actual", "expected", "reason"),
    [
        (
            {"value": "80", "scale": "PERCENT_100"},
            {"value": "3.2", "scale": "GPA_4_0"},
            "GPA_SCALE_MISMATCH",
        ),
        (
            {"value": "3.2", "scale": "UNKNOWN"},
            {"value": "3.0", "scale": "GPA_4_0"},
            "GPA_SCALE_UNKNOWN",
        ),
        (
            {"value": "3.2", "scale": "GPA_4_0"},
            {"value": "3.0", "scale": "UNKNOWN"},
            "GPA_SCALE_UNKNOWN",
        ),
        (
            {"value": "NaN", "scale": "GPA_4_0"},
            {"value": "3.0", "scale": "GPA_4_0"},
            "GPA_VALUE_INVALID",
        ),
        (
            {"value": "4.1", "scale": "GPA_4_0"},
            {"value": "3.0", "scale": "GPA_4_0"},
            "GPA_VALUE_INVALID",
        ),
    ],
)
def test_unknown_invalid_and_different_gpa_scales_do_not_guess_equivalence(
    actual, expected, reason
):
    output = check(confirmed(gpa=actual), rule("gpa", operator="GPA_MIN", gpa=expected))
    assert output["status"] == "INSUFFICIENT_INFORMATION"
    assert output["rules"][0]["result"] == "UNKNOWN"
    assert output["rules"][0]["reason_code"] == reason


@pytest.mark.parametrize(
    ("actual", "expected"),
    [
        ([{"language": "en", "level": "B2"}], "PASS"),
        ([{"language": "EN", "level": "C1"}], "PASS"),
        ([{"language": "en", "level": "B1"}], "FAIL"),
        ([{"language": "fr", "level": "C2"}], "FAIL"),
        ([], "FAIL"),
        ([{"language": "en", "level": None}], "UNKNOWN"),
        ([{"language": "en", "level": "IELTS_7"}], "UNKNOWN"),
    ],
)
def test_explicit_cefr_language_minimum_and_unknown_proofs(actual, expected):
    requirement = rule(
        "languages", operator="LANGUAGE_MIN", language={"language": "en", "level": "B2"}
    )
    assert check(confirmed(languages=actual), requirement)["rules"][0]["result"] == expected


def test_unknown_cefr_requirement_and_missing_language_inventory_remain_unknown():
    requirement = rule(
        "languages", operator="LANGUAGE_MIN", language={"language": "en", "level": None}
    )
    assert (
        check(confirmed(languages=[{"language": "en", "level": "C2"}]), requirement)["rules"][0][
            "result"
        ]
        == "UNKNOWN"
    )
    requirement["language"]["level"] = "B2"
    assert check({}, requirement)["rules"][0]["result"] == "UNKNOWN"


@pytest.mark.parametrize(
    "ruleset", [None, {"complete": True, "rules": []}, {"complete": False, "rules": []}]
)
def test_absent_or_empty_rule_basis_does_not_invent_eligibility(ruleset):
    result = evaluate(confirmed(major="engineering"), ruleset)
    assert result["status"] == "INSUFFICIENT_INFORMATION"
    assert result["fit_score_bps"] is None and result["coverage_bps"] == 0


@pytest.mark.parametrize(
    "changes",
    [{"verified": False}, {"operator": "UNSUPPORTED"}, {"values": []}, {"domain": "ACADEMIC"}],
)
def test_unverified_unsupported_and_missing_requirements_never_pass(changes):
    result = check(confirmed(major="engineering"), rule(**changes))
    assert result["rules"][0]["result"] == "UNKNOWN"
    assert result["status"] == "INSUFFICIENT_INFORMATION"
    assert result["coverage_bps"] == 0


def test_incomplete_verified_rule_basis_does_not_make_eligible():
    result = check(confirmed(major="engineering"), rule(), complete=False)
    assert result["rules"][0]["result"] == "PASS"
    assert result["status"] == "INSUFFICIENT_INFORMATION"


def all_domain_case():
    profile = confirmed(
        degree_level="MASTER",
        major="engineering",
        nationalities=["PS"],
        languages=[{"language": "en", "level": "B2"}],
        preferred_countries=["DE"],
    )
    requirements = [
        rule("degree_level", key="academic", values=["MASTER"]),
        rule("major", key="field"),
        rule("nationalities", key="citizenship", operator="INTERSECTS", values=["PS"]),
        rule(
            "languages",
            key="language",
            operator="LANGUAGE_MIN",
            language={"language": "en", "level": "B2"},
        ),
        rule(
            "preferred_countries",
            key="interest",
            operator="INTERSECTS",
            values=["DE"],
            mandatory=False,
        ),
    ]
    return profile, requirements


def test_exact_seventy_percent_coverage_allows_fit_and_below_threshold_suppresses_it():
    profile, requirements = all_domain_case()
    # Field25 + nationality20 + language15 + interest10 = exactly70.
    result = check(profile, *requirements[1:])
    assert result["coverage_bps"] == 7000 and result["fit_score_bps"] == 10000
    assert result["fit_status"] == "AVAILABLE"
    below = check(profile, *requirements[1:4])
    assert below["coverage_bps"] == 6000 and below["fit_score_bps"] is None
    assert below["fit_status"] == "INSUFFICIENT_COVERAGE"
    assert "INSUFFICIENT_VERIFIED_COVERAGE" in below["limitations"]


def test_initial_weights_are_exact_and_unknown_or_unverified_domain_does_not_gain_coverage():
    profile, requirements = all_domain_case()
    result = check(profile, *requirements)
    assert {item["domain"]: item["weight_bps"] for item in result["domains"]} == WEIGHTS
    assert list(WEIGHTS.values()) == [3000, 2500, 2000, 1500, 1000]
    assert result["coverage_bps"] == result["fit_score_bps"] == 10000
    requirements[0]["verified"] = False
    result = check(profile, *requirements)
    assert result["coverage_bps"] == 7000
    academic = result["domains"][0]
    assert academic["covered"] is False and academic["score_bps"] is None
    assert academic["contribution_bps"] is None


def test_one_unknown_rule_excludes_entire_domain_but_known_fail_is_evidence_not_missing():
    profile, requirements = all_domain_case()
    additional = rule("qualification", key="qualification", values=["BACHELOR"])
    result = check(profile, *requirements, additional)
    assert result["coverage_bps"] == 7000 and result["domains"][0]["covered"] is False
    profile["qualification"] = "SECONDARY"
    profile["confirmed_fields"].append("qualification")
    result = check(profile, *requirements, additional)
    assert result["coverage_bps"] == 10000
    assert result["domains"][0]["score_bps"] == 5000
    assert result["domains"][0]["contribution_bps"] == 1500
    assert result["fit_score_bps"] == 8500 and result["status"] == "INELIGIBLE"


def test_mandatory_failure_dominates_unknown_incomplete_basis_and_high_fit():
    profile, requirements = all_domain_case()
    requirements.append(rule("qualification", key="hard-failure", values=["BACHELOR"]))
    profile["qualification"] = "SECONDARY"
    profile["confirmed_fields"].append("qualification")
    requirements.append(rule("residency_country", key="unknown-residence", values=["PS"]))
    result = check(profile, *requirements, complete=False)
    assert result["status"] == "INELIGIBLE"
    assert {item["result"] for item in result["rules"]} == {"PASS", "FAIL", "UNKNOWN"}
    assert result["coverage_bps"] == 8000 and result["fit_score_bps"] == 8125
    assert result["fit_status"] == "AVAILABLE"


def test_optional_failure_and_unknown_cannot_change_mandatory_decision():
    result = check(
        confirmed(major="engineering"),
        rule(),
        rule("qualification", key="optional", values=["MASTER"], mandatory=False),
    )
    assert result["status"] == "ELIGIBLE" and result["rules"][1]["result"] == "UNKNOWN"
    result = check(
        confirmed(major="engineering", qualification="BACHELOR"),
        rule(),
        rule("qualification", key="optional", values=["MASTER"], mandatory=False),
    )
    assert result["status"] == "ELIGIBLE" and result["rules"][1]["result"] == "FAIL"


def test_rule_explanations_bind_exact_source_text_and_self_report_without_side_effects():
    profile = confirmed(major="engineering")
    requirement = rule(criterion_index=7)
    before = deepcopy((profile, requirement))
    result = check(profile, requirement)
    assert result["rules"][0] == {
        "key": requirement["key"],
        "criterion_index": 7,
        "field": "major",
        "domain": "FIELD",
        "mandatory": True,
        "result": "PASS",
        "reason_code": "MATCH",
        "expected_display": "engineering",
        "actual_display": "engineering",
        "evidence": {
            "profile_field": "major",
            "profile_confirmed": True,
            "criterion_index": 7,
            "source_text": requirement["evidence_text"],
        },
    }
    assert (profile, requirement) == before
    assert result["confidence"] == "UNCALIBRATED"
    assert "FIT_IS_NOT_ADMISSION_PROBABILITY" in result["limitations"]
    assert "STUDENT_CONFIRMED_IS_SELF_REPORTED" in result["limitations"]
    assert not ({"acceptance_probability", "admission_probability", "ai_score"} & result.keys())


def test_domain_mean_uses_all_known_rules_and_final_rounding_is_explicit_half_up():
    profile, requirements = all_domain_case()
    profile["qualification"] = "BACHELOR"
    profile["gpa"] = {"value": "2", "scale": "GPA_4_0"}
    profile["confirmed_fields"] += ["qualification", "gpa"]
    requirements += [
        rule("qualification", key="academic-two", values=["BACHELOR"]),
        rule(
            "gpa", key="academic-three", operator="GPA_MIN", gpa={"value": "3", "scale": "GPA_4_0"}
        ),
    ]
    output = check(profile, *requirements)
    assert output["domains"][0]["score_bps"] == 6667
    assert output["domains"][0]["contribution_bps"] == 2000
    # Exact contribution (2/3)*3000 is retained before final rounding.
    assert output["fit_score_bps"] == 9000
    assert output["status"] == "INELIGIBLE"


def test_unknown_rule_does_not_count_as_failed_fit_evidence_or_zero_a_domain():
    profile, requirements = all_domain_case()
    profile["languages"] = [{"language": "en", "level": None}]
    output = check(profile, *requirements)
    assert output["coverage_bps"] == 8500 and output["fit_score_bps"] == 10000
    language = next(item for item in output["domains"] if item["domain"] == "LANGUAGE")
    assert language["score_bps"] is None and language["contribution_bps"] is None
    assert output["status"] == "INSUFFICIENT_INFORMATION"


def test_known_all_fail_rules_can_have_covered_zero_fit_with_no_false_eligibility():
    profile, requirements = all_domain_case()
    profile.update(
        degree_level="PHD",
        major="history",
        nationalities=["FR"],
        languages=[],
        preferred_countries=[],
    )
    output = check(profile, *requirements)
    assert output["coverage_bps"] == 10000 and output["fit_score_bps"] == 0
    assert output["status"] == "INELIGIBLE"
    assert all(item["result"] == "FAIL" for item in output["rules"])


def test_complete_basis_with_only_unknown_optional_rules_cannot_claim_eligibility():
    output = check({}, rule(mandatory=False))
    assert output["status"] == "INSUFFICIENT_INFORMATION"
    assert output["coverage_bps"] == 0 and output["fit_score_bps"] is None
