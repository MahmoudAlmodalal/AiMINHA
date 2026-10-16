"""Owned deterministic evaluations on authored, approved synthetic catalog facts."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
from datetime import date, timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import DatabaseError, connections, transaction
from django.utils import timezone
from eligibility import services as eligibility_services
from eligibility.models import Evaluation, ProfileHead, ProfileVersion, RuleSet
from identity.models import Account, CommandReceipt, IdentitySession
from identity.security import digest
from privacy.models import PrivacyAudit
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Synthetic-eligibility-passphrase-529!"  # noqa: S105 -- public synthetic fixture.


@pytest.fixture(autouse=True)
def eligibility_settings(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.IDENTITY_RATE_LIMIT = 1000
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ALLOWED_HOSTS = ["testserver", "127.0.0.1", "localhost"]


def csrf(client):
    result = client.get("/api/v1/session/csrf")
    assert result.status_code == 200, result.content
    return result.json()["csrf_token"]


def mutate(client, path, data, *, revision=None, key=None, method="post"):
    headers = {
        "HTTP_X_CSRFTOKEN": csrf(client),
        "HTTP_IDEMPOTENCY_KEY": key or str(uuid.uuid4()),
    }
    if revision is not None:
        headers["HTTP_IF_MATCH"] = f'"{revision}"'
    return getattr(client, method)("/api/v1/" + path, data, format="json", **headers)


def signed_client(role="STUDENT", scopes=None, mfa=False):
    user = Account.objects.create_user(
        f"eligibility-{uuid.uuid4()}@example.invalid",
        PASSWORD,
        birth_date=date(2000, 1, 1),
        locale="en",
        state="ACTIVE",
        email_verified_at=timezone.now(),
        role=role,
        admin_scopes=scopes or [],
    )
    client = APIClient(enforce_csrf_checks=True)
    result = mutate(client, "session/login", {"email": user.email, "password": PASSWORD})
    assert result.status_code == 200, result.content
    if mfa:
        # Synthetic server proof: there is no public API accepting an MFA assertion.
        IdentitySession.objects.filter(digest=digest(client.session.session_key)).update(
            mfa_verified_at=timezone.now()
        )
    return client, user


@pytest.fixture
def student():
    return signed_client()


@pytest.fixture
def moderator():
    return signed_client("ADMIN", ["MODERATION", "SOURCE_APPROVAL"], True)[0]


def source_input(**changes):
    now = timezone.now()
    return {
        "name": "Authored synthetic eligibility source",
        "url": "https://fixtures.example.invalid/eligibility",
        "permission_status": "APPROVED",
        "license_basis": "Original synthetic data authored for deterministic tests.",
        "permission_evidence": "Synthetic evidence only; no real source authorization claimed.",
        "date_checked": now.isoformat(),
        "valid_until": (now + timedelta(days=90)).isoformat(),
        "allow_manual": True,
        "allow_import": False,
        "freshness_days": 30,
        "reason": "Synthetic fixture source registration.",
        **changes,
    }


@pytest.fixture
def catalog(moderator):
    source_response = mutate(moderator, "admin/sources", source_input())
    assert source_response.status_code == 201, source_response.content
    source = source_response.json()
    candidate_response = mutate(
        moderator,
        "admin/scholarships",
        {
            "source_id": source["id"],
            "title": "Synthetic engineering eligibility example",
            "provider": "Synthetic university",
            "summary": "Test fixture; no actual award.",
            "education_levels": ["MASTER"],
            "disciplines": ["engineering"],
            "countries": ["DE"],
            "languages": ["en"],
            "funding": "UNKNOWN",
            "criteria": [
                "Synthetic Master's level criterion",
                "Synthetic engineering criterion",
                "Synthetic PS nationality criterion",
                "Synthetic CEFR B2 criterion",
                "Synthetic Germany interest criterion",
            ],
            "required_documents": [],
            "submission_url": "https://fixtures.example.invalid/apply",
            "rounds": [{"kind": "UNKNOWN"}],
            "source_checked_at": timezone.now().isoformat(),
            "internal_notes": "PRIVATE-ELIGIBILITY-SYNTHETIC-NOTE",
            "origin": "MANUAL",
            "reason": "Authored synthetic eligibility candidate.",
        },
    )
    assert candidate_response.status_code == 201, candidate_response.content
    candidate = candidate_response.json()
    result = mutate(
        moderator,
        f"admin/scholarships/{candidate['id']}/moderation",
        {
            "version_id": candidate["latest"]["id"],
            "action": "APPROVE",
            "reason": "Synthetic human review of exact candidate.",
        },
        revision=candidate["revision"],
    )
    assert result.status_code == 200, result.content
    return {"source": source, "scholarship": result.json()}


def profile_input(**changes):
    fields = {
        "nationalities": ["PS"],
        "residency_country": "PS",
        "degree_level": "MASTER",
        "major": "engineering",
        "qualification": "BACHELOR",
        "gpa": {"value": "3.20", "scale": "GPA_4_0"},
        "languages": [{"language": "en", "level": "B2"}],
        "preferred_countries": ["DE"],
    }
    return {**fields, "confirmed_fields": list(fields), **changes}


def save_profile(client, revision=0, **changes):
    result = mutate(client, "profile", profile_input(**changes), revision=revision, method="put")
    assert result.status_code == 200, result.content
    return result.json()


def rules_payload(catalog, **changes):
    rules = []
    for index, (field, domain, operator, values, language) in enumerate(
        [
            ("degree_level", "ACADEMIC", "ONE_OF", ["MASTER"], None),
            ("major", "FIELD", "ONE_OF", ["engineering"], None),
            ("nationalities", "NATIONALITY_RESIDENCY", "INTERSECTS", ["PS"], None),
            ("languages", "LANGUAGE", "LANGUAGE_MIN", [], {"language": "en", "level": "B2"}),
            ("preferred_countries", "INTEREST", "INTERSECTS", ["DE"], None),
        ]
    ):
        rules.append(
            {
                "key": f"synthetic-{index}",
                "criterion_index": index,
                "field": field,
                "domain": domain,
                "operator": operator,
                "values": values,
                "gpa": None,
                "language": language,
                "mandatory": index != 4,
                "verified": True,
                "evidence_text": catalog["scholarship"]["latest"]["criteria"][index],
            }
        )
    return {
        "scholarship_version_id": catalog["scholarship"]["published_version_id"],
        "complete": True,
        "rules": rules,
        "confirm_review": True,
        "reason": "Synthetic human review of deterministic eligibility mapping.",
        **changes,
    }


def approve_rules(moderator, catalog, revision=0, **changes):
    result = mutate(
        moderator,
        f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules",
        rules_payload(catalog, **changes),
        revision=revision,
    )
    assert result.status_code in {200, 201}, result.content
    return result.json()


def evaluation_input(profile, catalog, **changes):
    return {
        "profile_version_id": profile["version_id"],
        "scholarship_id": catalog["scholarship"]["id"],
        "scholarship_version_id": catalog["scholarship"]["published_version_id"],
        **changes,
    }


def evaluate(client, profile, catalog, **changes):
    result = mutate(
        client, "eligibility/evaluations", evaluation_input(profile, catalog, **changes)
    )
    assert result.status_code in {200, 201}, result.content
    return result.json()


def test_profile_is_owned_typed_unknown_until_student_confirmation(student):
    client, _ = student
    empty = client.get("/api/v1/profile")
    assert empty.status_code == 200, empty.content
    assert empty.json()["revision"] == 0 and empty.json()["version_id"] is None
    assert empty.json()["profile"]["nationalities"] is None
    result = save_profile(client, nationalities=None, gpa=None, confirmed_fields=["major"])
    assert result["revision"] == 1 and result["version_id"]
    assert result["profile"]["nationalities"] is None and result["profile"]["gpa"] is None
    assert result["provenance"] == "STUDENT_CONFIRMED_MANUAL"
    assert result["credential_verification"] == "NOT_INDEPENDENTLY_VERIFIED"
    assert client.get("/api/v1/profile").json() == result


@pytest.mark.parametrize(
    "body",
    [
        {"owner_id": str(uuid.uuid4())},
        {"verified": True},
        {"credential_verification": "VERIFIED"},
        {"nationalities": ["Palestine"]},
        {"degree_level": "POSTDOC"},
        {"qualification": "GUESS"},
        {"gpa": {"value": "4.1", "scale": "GPA_4_0"}},
        {"gpa": {"value": "-1", "scale": "PERCENT_100"}},
        {"gpa": {"value": "NaN", "scale": "GPA_4_0"}},
        {"gpa": {"value": "3.2", "scale": "GPA_GUESSED"}},
        {"languages": [{"language": "en", "level": "IELTS_7"}]},
        {"confirmed_fields": ["role"]},
    ],
)
def test_profile_rejects_invalid_facts_and_ownership_or_verification_injection(student, body):
    response = mutate(student[0], "profile", profile_input(**body), revision=0, method="put")
    assert response.status_code == 400, response.content
    assert student[0].get("/api/v1/profile").json()["revision"] == 0


def test_profile_requires_csrf_if_match_and_stable_idempotency(student):
    client, _ = student
    assert client.put("/api/v1/profile", profile_input(), format="json").status_code == 403
    assert mutate(client, "profile", profile_input(), method="put").status_code in {400, 412}
    key = str(uuid.uuid4())
    first = mutate(client, "profile", profile_input(), revision=0, key=key, method="put")
    assert first.status_code == 200, first.content
    replay = mutate(client, "profile", profile_input(), revision=0, key=key, method="put")
    assert replay.status_code == 200 and replay.json() == first.json()
    assert (
        mutate(
            client, "profile", profile_input(major="history"), revision=0, key=key, method="put"
        ).status_code
        == 409
    )
    assert mutate(client, "profile", profile_input(), revision=0, method="put").status_code == 412
    next_profile = save_profile(client, revision=1, major="history")
    assert (
        next_profile["revision"] == 2 and next_profile["version_id"] != first.json()["version_id"]
    )


def test_personal_routes_deny_anonymous_and_admin_even_with_mfa(moderator):
    anonymous = APIClient(enforce_csrf_checks=True)
    for client in [anonymous, moderator]:
        assert client.get("/api/v1/profile").status_code in {401, 403}
        assert client.get(f"/api/v1/eligibility/evaluations/{uuid.uuid4()}").status_code in {
            401,
            403,
        }
        assert mutate(client, "profile", profile_input(), revision=0, method="put").status_code in {
            401,
            403,
        }


@pytest.mark.parametrize(
    "change",
    [
        {"email_verified_at": None},
        {"birth_date": date(2015, 1, 1)},
        {"state": "DELETION_PENDING"},
        {"state": "SUSPENDED"},
    ],
)
def test_verified_adult_and_active_state_rechecked_on_every_profile_request(student, change):
    client, user = student
    Account.objects.filter(pk=user.pk).update(**change)
    assert client.get("/api/v1/profile").status_code in {401, 403}
    assert mutate(client, "profile", profile_input(), revision=0, method="put").status_code in {
        401,
        403,
    }


def test_profile_and_evaluations_never_offer_cross_user_read(student, moderator, catalog):
    client, owner = student
    profile = save_profile(client)
    approve_rules(moderator, catalog)
    own = evaluate(client, profile, catalog)
    other, _ = signed_client()
    assert other.get("/api/v1/profile").json()["version_id"] is None
    forbidden = mutate(other, "eligibility/evaluations", evaluation_input(profile, catalog))
    assert forbidden.status_code == 403, forbidden.content
    assert other.get(f"/api/v1/eligibility/evaluations/{own['id']}").status_code == 403
    assert other.get(f"/api/v1/eligibility/evaluations/{uuid.uuid4()}").status_code == 403
    assert moderator.get(f"/api/v1/eligibility/evaluations/{own['id']}").status_code == 403
    assert other.get(f"/api/v1/profile?owner_id={owner.pk}").status_code in {400, 403}


def test_text_criteria_are_not_automatically_interpreted_or_given_a_fit(student, catalog):
    profile = save_profile(student[0])
    with patch(
        "socket.create_connection", side_effect=AssertionError("No provider network allowed")
    ):
        result = evaluate(student[0], profile, catalog)
    assert result["rule_set_id"] is None
    assert result["result"]["status"] == "INSUFFICIENT_INFORMATION"
    assert result["result"]["coverage_bps"] == 0 and result["result"]["fit_score_bps"] is None


def test_approved_evidence_produces_owned_explained_versioned_result(student, moderator, catalog):
    profile = save_profile(student[0])
    rules = approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    assert result["policy_version"] == "phase08-v1" and result["evaluated_at"]
    assert result["profile_version_id"] == profile["version_id"]
    assert result["scholarship_version_id"] == catalog["scholarship"]["published_version_id"]
    assert result["rule_set_id"] == rules["rule_set"]["id"]
    assert result["result"]["status"] == "ELIGIBLE"
    assert result["result"]["coverage_bps"] == result["result"]["fit_score_bps"] == 10000
    assert len(result["result"]["rules"]) == 5
    assert student[0].get(f"/api/v1/eligibility/evaluations/{result['id']}").json() == result
    public = APIClient().get(f"/api/v1/scholarships/{catalog['scholarship']['id']}")
    assert "profile_version_id" not in public.json()
    serialized = json.dumps(result)
    assert PASSWORD not in serialized and "PRIVATE-ELIGIBILITY-SYNTHETIC-NOTE" not in serialized
    assert "acceptance_probability" not in serialized and "admission_probability" not in serialized


def test_mandatory_failure_remains_ineligible_with_a_high_fit(student, moderator, catalog):
    profile = save_profile(student[0], nationalities=["FR"])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)["result"]
    assert result["status"] == "INELIGIBLE" and result["fit_score_bps"] == 8000
    assert (
        next(item for item in result["rules"] if item["field"] == "nationalities")["result"]
        == "FAIL"
    )


def test_only_confirmed_facts_count_towards_coverage_and_unknown_is_not_false(
    student, moderator, catalog
):
    profile = save_profile(
        student[0], confirmed_fields=["major", "nationalities", "languages", "preferred_countries"]
    )
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)["result"]
    assert result["coverage_bps"] == 7000 and result["fit_score_bps"] == 10000
    assert result["status"] == "INSUFFICIENT_INFORMATION"
    assert result["missing_fields"] == ["degree_level"]


def test_old_profile_or_ruleset_evaluation_cannot_be_presented_as_current(
    student, moderator, catalog
):
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    save_profile(student[0], revision=1, major="history")
    assert student[0].get(f"/api/v1/eligibility/evaluations/{result['id']}").status_code == 409
    assert (
        mutate(
            student[0], "eligibility/evaluations", evaluation_input(profile, catalog)
        ).status_code
        == 409
    )
    current = student[0].get("/api/v1/profile").json()
    result = evaluate(student[0], current, catalog)
    approve_rules(moderator, catalog, revision=1)
    assert student[0].get(f"/api/v1/eligibility/evaluations/{result['id']}").status_code == 409


def test_current_source_revocation_blocks_new_and_saved_personal_evaluations(
    student, moderator, catalog
):
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    revoked = mutate(
        moderator,
        f"admin/sources/{catalog['source']['id']}/versions",
        source_input(permission_status="REVOKED"),
        revision=catalog["source"]["revision"],
    )
    assert revoked.status_code == 200, revoked.content
    assert (
        mutate(
            student[0], "eligibility/evaluations", evaluation_input(profile, catalog)
        ).status_code
        == 409
    )
    assert student[0].get(f"/api/v1/eligibility/evaluations/{result['id']}").status_code == 409


@pytest.mark.parametrize(
    "role,scopes,mfa",
    [
        ("STUDENT", [], False),
        ("ADMIN", [], True),
        ("ADMIN", ["MODERATION"], False),
    ],
)
def test_rule_review_requires_scoped_current_server_mfa(catalog, role, scopes, mfa):
    client, _ = signed_client(role, scopes, mfa)
    path = f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules"
    assert client.get("/api/v1/" + path).status_code == 403
    assert mutate(client, path, rules_payload(catalog), revision=0).status_code == 403


@pytest.mark.parametrize(
    "change",
    [
        {"confirm_review": False},
        {"complete": True, "rules": []},
        {"owner_id": str(uuid.uuid4())},
    ],
)
def test_rule_review_rejects_missing_human_review_and_unmapped_or_injected_basis(
    moderator, catalog, change
):
    path = f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules"
    response = mutate(moderator, path, rules_payload(catalog, **change), revision=0)
    assert response.status_code == 400, response.content
    assert moderator.get("/api/v1/" + path).json()["revision"] == 0


def test_rule_review_is_explicit_revisioned_csrf_protected_and_audited_without_private_facts(
    moderator, catalog, student
):
    path = f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules"
    assert (
        moderator.post("/api/v1/" + path, rules_payload(catalog), format="json").status_code == 403
    )
    approve_rules(moderator, catalog)
    assert mutate(moderator, path, rules_payload(catalog), revision=0).status_code == 412
    profile = save_profile(student[0])
    evaluate(student[0], profile, catalog)
    audit_payload = json.dumps(list(PrivacyAudit.objects.values()), default=str)
    assert PASSWORD not in audit_payload and "engineering" not in audit_payload
    assert student[1].email not in audit_payload and "3.20" not in audit_payload


def test_evaluation_retains_csrf_and_rejects_client_score_or_decision_injection(student, catalog):
    client, _ = student
    profile = save_profile(client)
    payload = evaluation_input(profile, catalog)
    assert client.post("/api/v1/eligibility/evaluations", payload, format="json").status_code == 403
    for change in [
        {"status": "ELIGIBLE"},
        {"fit_score_bps": 10000},
        {"ai_override": True},
        {"owner_id": str(uuid.uuid4())},
    ]:
        result = mutate(client, "eligibility/evaluations", {**payload, **change})
        assert result.status_code == 400, result.content


def test_unverified_requirement_is_not_satisfied_and_never_increases_coverage(
    student, moderator, catalog
):
    profile = save_profile(student[0])
    payload = rules_payload(catalog)
    payload["rules"][0]["verified"] = False
    approve_rules(moderator, catalog, rules=payload["rules"])
    result = evaluate(student[0], profile, catalog)["result"]
    assert result["status"] == "INSUFFICIENT_INFORMATION"
    assert result["coverage_bps"] == 7000 and result["fit_score_bps"] == 10000
    assert result["rules"][0]["result"] == "UNKNOWN"
    assert result["rules"][0]["reason_code"] == "REQUIREMENT_UNVERIFIED"


@pytest.mark.parametrize(
    "fault", ["duplicate_key", "bad_domain", "bad_operator", "missing_index", "out_of_range"]
)
def test_rule_review_cannot_claim_complete_with_invalid_or_missing_criterion_basis(
    moderator, catalog, fault
):
    payload = rules_payload(catalog)
    if fault == "duplicate_key":
        payload["rules"][1]["key"] = payload["rules"][0]["key"]
    elif fault == "bad_domain":
        payload["rules"][1]["domain"] = "ACADEMIC"
    elif fault == "bad_operator":
        payload["rules"][1]["operator"] = "INTERSECTS"
    elif fault == "missing_index":
        payload["rules"].pop()
    else:
        payload["rules"][0]["criterion_index"] = 49
    path = f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules"
    result = mutate(moderator, path, payload, revision=0)
    assert result.status_code == 400, result.content


def test_old_evaluation_receipt_cannot_bypass_profile_changes(student, moderator, catalog):
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    payload = evaluation_input(profile, catalog)
    key = str(uuid.uuid4())
    result = mutate(student[0], "eligibility/evaluations", payload, key=key)
    assert result.status_code in {200, 201}, result.content
    replay = mutate(student[0], "eligibility/evaluations", payload, key=key)
    assert replay.status_code == result.status_code and replay.json() == result.json()
    save_profile(student[0], revision=1, major="history")
    stale = mutate(student[0], "eligibility/evaluations", payload, key=key)
    assert stale.status_code == 409, stale.content


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_profile_edits_preserve_one_version_and_reject_stale_writer(student):
    client, _ = student
    barrier = Barrier(2)
    cookies = copy(client.cookies)

    def write(major):
        separate = APIClient(enforce_csrf_checks=True)
        separate.cookies = copy(cookies)
        try:
            token = csrf(separate)
            barrier.wait(timeout=10)
            result = separate.put(
                "/api/v1/profile",
                profile_input(major=major),
                format="json",
                HTTP_X_CSRFTOKEN=token,
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                HTTP_IF_MATCH='"0"',
            )
            return result.status_code, result.json()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["engineering", "history"]))
    assert sorted(status for status, _ in results) == [200, 412], results
    current = client.get("/api/v1/profile").json()
    assert current["revision"] == 1
    assert current["profile"]["major"] in {"engineering", "history"}


def test_profile_rule_and_evaluation_snapshots_are_immutable_in_postgresql(
    student, moderator, catalog
):
    profile = save_profile(student[0])
    rules = approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    for model, identifier, changes, delete_statement in [
        (
            ProfileVersion,
            profile["version_id"],
            {"facts": {}},
            "DELETE FROM eligibility_profileversion WHERE id=%s",
        ),
        (
            RuleSet,
            rules["rule_set"]["id"],
            {"complete": False},
            "DELETE FROM eligibility_ruleset WHERE id=%s",
        ),
        (
            Evaluation,
            result["id"],
            {"result": {}},
            "DELETE FROM eligibility_evaluation WHERE id=%s",
        ),
    ]:
        with pytest.raises(DatabaseError), transaction.atomic():
            model.objects.filter(pk=identifier).update(**changes)
        with pytest.raises(DatabaseError), transaction.atomic():
            # ORM cascades/PROTECT are insufficient evidence for the SQL guard.
            with connections["default"].cursor() as cursor:
                cursor.execute(delete_statement, [identifier])
    assert student[0].get(f"/api/v1/eligibility/evaluations/{result['id']}").json() == result


def test_database_rejects_cross_owner_profile_heads_and_evaluation_foreign_keys(
    student, moderator, catalog
):
    own = save_profile(student[0])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], own, catalog)
    other_client, other_user = signed_client()
    save_profile(other_client)
    with pytest.raises(DatabaseError), transaction.atomic():
        ProfileHead.objects.filter(owner=other_user).update(
            current_id=own["version_id"], revision=2
        )
    original = Evaluation.objects.get(pk=result["id"])
    with pytest.raises(DatabaseError), transaction.atomic():
        Evaluation.objects.create(
            owner=other_user,
            profile_version_id=original.profile_version_id,
            scholarship_version_id=original.scholarship_version_id,
            rule_set_id=original.rule_set_id,
            policy_version=original.policy_version,
            policy_snapshot=original.policy_snapshot,
            source_freshness=original.source_freshness,
            result=original.result,
        )


def test_database_never_accepts_a_forged_eligible_outcome_over_mandatory_failure(
    student, moderator, catalog
):
    profile = save_profile(student[0], nationalities=["FR"])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    original = Evaluation.objects.get(pk=result["id"])
    assert original.result["status"] == "INELIGIBLE"
    with pytest.raises(DatabaseError), transaction.atomic():
        Evaluation.objects.create(
            owner=original.owner,
            profile_version=original.profile_version,
            scholarship_version=original.scholarship_version,
            rule_set=original.rule_set,
            policy_version=original.policy_version,
            policy_snapshot=original.policy_snapshot,
            source_freshness=original.source_freshness,
            result={**original.result, "status": "ELIGIBLE", "fit_score_bps": 10000},
        )


@pytest.mark.parametrize("freshness", ["STALE", "UNKNOWN"])
def test_source_freshness_uncertainty_disables_fit_and_invalidates_old_results(
    student, moderator, catalog, freshness
):
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    current = evaluate(student[0], profile, catalog)
    public_data = eligibility_services.catalog.public_data

    def changed_freshness(version):
        # Change only the catalog boundary's classification; do not mock sessions,
        # publication permission, review, student facts or the deterministic engine.
        return {**public_data(version), "freshness": freshness}

    with patch("eligibility.services.catalog.public_data", side_effect=changed_freshness):
        result = evaluate(student[0], profile, catalog)["result"]
        assert result["status"] == "INSUFFICIENT_INFORMATION"
        assert result["coverage_bps"] == 0 and result["fit_score_bps"] is None
        assert all(item["result"] == "UNKNOWN" for item in result["rules"])
        assert "SOURCE_" + freshness in result["limitations"]
        assert student[0].get(f"/api/v1/eligibility/evaluations/{current['id']}").status_code == 409
        path = f"admin/scholarships/{catalog['scholarship']['id']}/eligibility-rules"
        assert mutate(moderator, path, rules_payload(catalog), revision=1).status_code == 409


def test_unknown_optional_rules_do_not_manufacture_a_verified_eligibility_basis(
    student, moderator, catalog
):
    profile = save_profile(student[0])
    payload = rules_payload(catalog)
    for criterion in payload["rules"]:
        criterion.update(mandatory=False, verified=False)
    approve_rules(moderator, catalog, rules=payload["rules"])
    result = evaluate(student[0], profile, catalog)["result"]
    assert result["status"] == "INSUFFICIENT_INFORMATION"
    assert result["coverage_bps"] == 0 and result["fit_score_bps"] is None


def test_idempotency_receipts_keep_only_opaque_references_without_private_profile_or_results(
    student, moderator, catalog
):
    previous = set(CommandReceipt.objects.values_list("id", flat=True))
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    evaluate(student[0], profile, catalog)
    receipts = list(
        CommandReceipt.objects.exclude(pk__in=previous).values_list("response", flat=True)
    )
    assert len(receipts) == 3
    assert {tuple(receipt.keys()) for receipt in receipts} == {
        ("version_id",),
        ("rule_set_id",),
        ("evaluation_id",),
    }
    for receipt in receipts:
        assert uuid.UUID(next(iter(receipt.values())))
    payload = json.dumps(receipts)
    assert all(
        value not in payload for value in ["engineering", "3.20", student[1].email, PASSWORD]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "omitted_rule",
        "duplicate_rule",
        "missing_top_key",
        "missing_rule_key",
        "null_rule_state",
        "null_mandatory_state_with_other_passes",
        "changed_source_text",
        "changed_mandatory_flag",
        "insufficient_coverage_score",
    ],
)
def test_raw_evaluation_insert_rejects_incomplete_or_invented_pinned_rule_checks(
    student, moderator, catalog, fault
):
    profile = save_profile(student[0])
    approve_rules(moderator, catalog)
    result = evaluate(student[0], profile, catalog)
    original = Evaluation.objects.get(pk=result["id"])
    forged = deepcopy(original.result)
    if fault == "omitted_rule":
        forged["rules"].pop()
    elif fault == "duplicate_rule":
        forged["rules"][-1] = deepcopy(forged["rules"][0])
    elif fault == "missing_top_key":
        forged.pop("coverage_bps")
    elif fault == "missing_rule_key":
        forged["rules"][0].pop("evidence")
    elif fault == "null_rule_state":
        for criterion in forged["rules"]:
            criterion["result"] = None
        forged["status"] = "INSUFFICIENT_INFORMATION"
    elif fault == "null_mandatory_state_with_other_passes":
        forged["rules"][0]["result"] = None
    elif fault == "changed_source_text":
        forged["rules"][0]["evidence"]["source_text"] = "Invented source criterion"
    elif fault == "changed_mandatory_flag":
        forged["rules"][0]["mandatory"] = False
    else:
        forged["coverage_bps"] = 6999
    with pytest.raises(DatabaseError), transaction.atomic():
        Evaluation.objects.create(
            owner=original.owner,
            profile_version=original.profile_version,
            scholarship_version=original.scholarship_version,
            rule_set=original.rule_set,
            policy_version=original.policy_version,
            policy_snapshot=original.policy_snapshot,
            source_freshness=original.source_freshness,
            result=forged,
        )
