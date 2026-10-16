import hashlib
import json
from datetime import timedelta
from typing import Any
from uuid import UUID

from catalog import services as catalog
from catalog.models import Scholarship, ScholarshipVersion, Source
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, require_admin, require_student

from eligibility import engine
from eligibility.models import Evaluation, ProfileHead, ProfileVersion, RuleHead, RuleSet
from eligibility.serializers import FIELDS

POLICY_VERSION = "phase08-v1"
POLICY = {
    "version": POLICY_VERSION,
    "engine_version": engine.ENGINE_VERSION,
    "weight_version": engine.WEIGHT_VERSION,
    "minimum_coverage_bps": 7000,
    "weights_bps": {
        "ACADEMIC": 3000,
        "FIELD": 2500,
        "NATIONALITY_RESIDENCY": 2000,
        "LANGUAGE": 1500,
        "INTEREST": 1000,
    },
    "domain_coverage": "ALL_COMPARISONS_KNOWN",
    "domain_fit": "MEAN_BINARY_COMPARISONS",
    "score": "WEIGHTED_MEAN_OF_COVERED_DOMAINS_HALF_UP",
    "gpa_conversion": "SAME_DECLARED_SCALE_ONLY",
    "confidence": "UNCALIBRATED",
}


def canonical(value: Any) -> Any:
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def hash_value(value: Any) -> str:
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True).encode()).hexdigest()


def student(user: Account, proof: IdentitySession) -> Account:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_student(user)
    proof.refresh_from_db()
    now = timezone.now()
    if (
        proof.account_id != user.pk
        or proof.epoch != user.session_epoch
        or proof.revoked_at is not None
        or now >= proof.expires_at
        or now >= proof.last_seen_at + timedelta(hours=24)
    ):
        raise IdentityError("SESSION_EXPIRED", 401, "Sign in again")
    return user


def profile_data(head: ProfileHead | None) -> dict[str, Any]:
    current = head.current if head else None
    return {
        "id": str(head.pk) if head else None,
        "revision": head.revision if head else 0,
        "version_id": str(current.pk) if current else None,
        "profile": {
            **(current.facts if current else dict.fromkeys(FIELDS)),
            "confirmed_fields": current.confirmed_fields if current else [],
        },
        "confirmed_at": current.created_at if current else None,
        "provenance": "STUDENT_CONFIRMED_MANUAL",
        "credential_verification": "NOT_INDEPENDENTLY_VERIFIED",
    }


@transaction.atomic
def read_profile(user: Account, proof: IdentitySession, correlation: Any) -> dict[str, Any]:
    user = student(user, proof)
    head = ProfileHead.objects.select_related("current").filter(owner=user).first()
    audit(
        user,
        "eligibility_profile_read",
        resource=head.pk if head else None,
        correlation=correlation,
    )
    return profile_data(head)


@transaction.atomic
def write_profile(
    user: Account, proof: IdentitySession, data: dict[str, Any], expected: int, correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    head, _ = ProfileHead.objects.get_or_create(owner=user)
    head = ProfileHead.objects.select_for_update().get(pk=head.pk)
    catalog.check_revision(head, expected)
    version = ProfileVersion.objects.create(
        owner=user,
        version=head.revision + 1,
        facts=canonical({key: data[key] for key in FIELDS}),
        confirmed_fields=data["confirmed_fields"],
        content_hash=hash_value(data),
    )
    head.current, head.revision = version, version.version
    head.save(update_fields=["current", "revision"])
    audit(user, "eligibility_profile_saved", resource=version.pk, correlation=correlation)
    return profile_data(head)


def rule_data(value: RuleSet) -> dict[str, Any]:
    return {
        "id": str(value.pk),
        "version": value.version,
        "scholarship_version_id": str(value.scholarship_version_id),
        "scholarship_hash": value.scholarship_hash,
        "complete": value.complete,
        "rules": value.rules,
        "content_hash": value.content_hash,
        "reviewed_by": str(value.actor_id),
        "reviewed_at": value.created_at,
        "reason": value.reason,
    }


@transaction.atomic
def read_rules(
    user: Account, proof: IdentitySession, scholarship_id: UUID, correlation: Any
) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    catalog.get_scholarship(scholarship_id)
    head = RuleHead.objects.select_related("current").filter(scholarship_id=scholarship_id).first()
    catalog.record(user, "eligibility_rules_read", scholarship_id, correlation=correlation)
    return {
        "revision": head.revision if head else 0,
        "rule_set": rule_data(head.current) if head and head.current else None,
    }


def locked_catalog(scholarship_id: UUID, version_id: UUID) -> ScholarshipVersion:
    # Fixed order: actor -> source -> scholarship -> rules -> profile. Version rows
    # are immutable; the first lookup only discovers which source row to lock.
    snapshot = (
        ScholarshipVersion.objects.select_related("source_revision")
        .filter(pk=version_id, scholarship_id=scholarship_id)
        .first()
    )
    if snapshot is None:
        raise IdentityError(
            "CATALOG_VERSION_UNAVAILABLE", 409, "Choose a current published scholarship"
        )
    Source.objects.select_for_update().get(pk=snapshot.source_revision.source_id)
    Scholarship.objects.select_for_update().get(pk=scholarship_id)
    current = catalog.published_query().filter(pk=version_id, scholarship_id=scholarship_id).first()
    if current is None:
        raise IdentityError(
            "CATALOG_VERSION_UNAVAILABLE", 409, "Choose a current published scholarship"
        )
    return current


@transaction.atomic
def authorize_rule_review(
    user: Account, proof: IdentitySession, scholarship_id: UUID, version_id: UUID
) -> ScholarshipVersion:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    version = locked_catalog(scholarship_id, version_id)
    if catalog.public_data(version)["freshness"] != "CURRENT":
        raise IdentityError(
            "SOURCE_REVERIFICATION_REQUIRED", 409, "Reverify source facts before reviewing rules"
        )
    return version


@transaction.atomic
def write_rules(
    user: Account,
    proof: IdentitySession,
    scholarship_id: UUID,
    data: dict[str, Any],
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    version = locked_catalog(scholarship_id, data["scholarship_version_id"])
    if catalog.public_data(version)["freshness"] != "CURRENT":
        raise IdentityError(
            "SOURCE_REVERIFICATION_REQUIRED", 409, "Reverify source facts before reviewing rules"
        )
    indices = {row["criterion_index"] for row in data["rules"]}
    valid = set(range(len(version.criteria)))
    if not indices <= valid or (data["complete"] and (not valid or indices != valid)):
        raise IdentityError(
            "CRITERIA_BASIS_INCOMPLETE",
            400,
            "Map the exact reviewed criteria before marking the basis complete",
        )
    head, _ = RuleHead.objects.get_or_create(scholarship_id=scholarship_id)
    head = RuleHead.objects.select_for_update().get(pk=head.pk)
    catalog.check_revision(head, expected)
    value = RuleSet.objects.create(
        head=head,
        version=head.revision + 1,
        scholarship_version=version,
        scholarship_hash=version.content_hash,
        complete=data["complete"],
        rules=canonical(data["rules"]),
        content_hash=hash_value(
            {
                "rules": data["rules"],
                "complete": data["complete"],
                "scholarship_version_id": str(version.pk),
            }
        ),
        actor=user,
        session_proof=proof,
        reason=data["reason"],
    )
    head.current, head.revision = value, value.version
    head.save(update_fields=["current", "revision"])
    catalog.record(
        user, "eligibility_rules_reviewed", scholarship_id, value.pk, correlation=correlation
    )
    return {"revision": head.revision, "rule_set": rule_data(value)}


def inputs(
    user: Account, data: dict[str, Any]
) -> tuple[ProfileVersion, ScholarshipVersion, RuleSet | None, str]:
    profile = ProfileVersion.objects.filter(pk=data["profile_version_id"], owner=user).first()
    if profile is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    version = locked_catalog(data["scholarship_id"], data["scholarship_version_id"])
    rule_head = (
        RuleHead.objects.select_for_update().filter(scholarship_id=version.scholarship_id).first()
    )
    rules = rule_head.current if rule_head else None
    if rules is not None and (
        rules.scholarship_version_id != version.pk or rules.scholarship_hash != version.content_hash
    ):
        rules = None
    head = ProfileHead.objects.select_for_update().filter(owner=user).first()
    if head is None or head.current_id != profile.pk:
        raise IdentityError("PROFILE_CHANGED", 409, "Review the current profile before evaluating")
    return profile, version, rules, catalog.public_data(version)["freshness"]


def evaluation_data(value: Evaluation) -> dict[str, Any]:
    return {
        "id": str(value.pk),
        "profile_version_id": str(value.profile_version_id),
        "scholarship_id": str(value.scholarship_version.scholarship_id),
        "scholarship_version_id": str(value.scholarship_version_id),
        "rule_set_id": str(value.rule_set_id) if value.rule_set_id else None,
        "policy_version": value.policy_version,
        "engine_version": value.policy_snapshot["engine_version"],
        "weight_version": value.policy_snapshot["weight_version"],
        "evaluated_at": value.evaluated_at,
        "result": value.result,
    }


@transaction.atomic
def evaluate_profile(
    user: Account, proof: IdentitySession, data: dict[str, Any], correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    profile, version, rules, freshness = inputs(user, data)
    basis = {"complete": rules.complete, "rules": rules.rules} if rules else None
    if basis is not None and rules is not None and freshness != "CURRENT":
        basis = {"complete": False, "rules": [{**row, "verified": False} for row in rules.rules]}
    result = engine.evaluate({**profile.facts, "confirmed_fields": profile.confirmed_fields}, basis)
    if freshness != "CURRENT":
        result["limitations"].append("SOURCE_" + freshness)
    value = Evaluation.objects.create(
        owner=user,
        profile_version=profile,
        scholarship_version=version,
        rule_set=rules,
        policy_version=POLICY_VERSION,
        policy_snapshot=POLICY,
        source_freshness=freshness,
        result=result,
    )
    audit(user, "eligibility_evaluated", resource=value.pk, correlation=correlation)
    return evaluation_data(value)


@transaction.atomic
def read_evaluation(
    user: Account, proof: IdentitySession, evaluation_id: UUID, correlation: Any
) -> dict[str, Any]:
    user = student(user, proof)
    value = (
        Evaluation.objects.select_related("scholarship_version")
        .filter(pk=evaluation_id, owner=user)
        .first()
    )
    if value is None:
        raise IdentityError("FORBIDDEN", 403, "Access denied")
    _, _, current_rules, freshness = inputs(
        user,
        {
            "profile_version_id": value.profile_version_id,
            "scholarship_id": value.scholarship_version.scholarship_id,
            "scholarship_version_id": value.scholarship_version_id,
        },
    )
    if (
        current_rules.pk if current_rules else None
    ) != value.rule_set_id or freshness != value.source_freshness:
        raise IdentityError(
            "EVALUATION_STALE", 409, "Inputs changed; evaluate current evidence again"
        )
    audit(user, "eligibility_evaluation_read", resource=value.pk, correlation=correlation)
    return evaluation_data(value)
