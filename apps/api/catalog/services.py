import hashlib
import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.db.models import F, Q, QuerySet
from django.db.models.expressions import RawSQL
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, require_admin

from catalog.models import (
    CatalogAudit,
    ModerationEvent,
    Scholarship,
    ScholarshipVersion,
    Source,
    SourceRevision,
)

FACTS = (
    "title",
    "provider",
    "summary",
    "education_levels",
    "disciplines",
    "countries",
    "languages",
    "funding",
    "criteria",
    "required_documents",
    "submission_url",
    "rounds",
)
SOURCE_FIELDS = (
    "name",
    "url",
    "permission_status",
    "license_basis",
    "permission_evidence",
    "date_checked",
    "valid_until",
    "allow_manual",
    "allow_import",
    "freshness_days",
    "reason",
)


def record(
    actor: Any,
    action: str,
    resource: Any = None,
    version: Any = None,
    outcome: str = "ALLOW",
    reason: str = "",
    correlation: Any = None,
) -> None:
    CatalogAudit.objects.create(
        actor_id=getattr(actor, "pk", None),
        resource_id=resource,
        version_id=version,
        action=action,
        outcome=outcome,
        reason=reason,
        correlation_id=correlation,
    )


def expected_revision(request: Any) -> int:
    raw = request.headers.get("If-Match", "")
    if len(raw) < 3 or not raw.startswith('"') or not raw.endswith('"') or not raw[1:-1].isdigit():
        raise IdentityError("PRECONDITION_REQUIRED", 412, "A quoted current revision is required")
    return int(raw[1:-1])


def check_revision(resource: Any, expected: int) -> None:
    if resource.revision != expected:
        raise IdentityError("STALE_REVISION", 412, "Resource changed; reload before reviewing")


def source_allowed(version: SourceRevision, origin: str, now: datetime | None = None) -> bool:
    now = now or timezone.now()
    return bool(
        version.permission_status == "APPROVED"
        and version.date_checked
        and version.date_checked <= now
        and version.license_basis
        and version.permission_evidence
        and (version.valid_until is None or now < version.valid_until)
        and (version.allow_manual if origin == "MANUAL" else version.allow_import)
    )


def source_data(source: Source) -> dict[str, Any]:
    value = source.current
    assert value is not None
    return {
        **{field: getattr(value, field) for field in SOURCE_FIELDS},
        "id": str(source.pk),
        "version_id": str(value.pk),
        "revision": source.revision,
        "editor_id": str(value.editor_id),
        "automation_enabled": False,
    }


@transaction.atomic
def write_source(
    user: Account,
    proof: IdentitySession,
    data: dict[str, Any],
    correlation: Any,
    source_id: UUID | None = None,
    expected: int | None = None,
) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    if data["permission_status"] == "APPROVED":
        require_admin(user, proof, "SOURCE_APPROVAL")
        if data["valid_until"] and data["valid_until"] <= timezone.now():
            raise IdentityError(
                "SOURCE_PERMISSION_EXPIRED", 409, "Recheck expired source permission"
            )
    if source_id:
        try:
            source = Source.objects.select_for_update().get(pk=source_id)
        except Source.DoesNotExist as exc:
            raise IdentityError("NOT_FOUND", 404, "Source not found") from exc
        check_revision(source, expected or 0)
    else:
        source = Source.objects.create()
    version = SourceRevision.objects.create(
        source=source, revision=source.revision + 1, editor=user, session_proof=proof, **data
    )
    source.current, source.revision = version, version.revision
    source.save(update_fields=["current", "revision"])
    record(user, "source_revision_recorded", source.pk, version.pk, correlation=correlation)
    return source_data(source)


def candidate_data(version: ScholarshipVersion) -> dict[str, Any]:
    return {
        **{field: getattr(version, field) for field in FACTS},
        "id": str(version.pk),
        "version": version.version,
        "source_id": str(version.source_revision.source_id),
        "source_revision_id": str(version.source_revision_id),
        "source_checked_at": version.source_checked_at,
        "internal_notes": version.internal_notes,
        "origin": version.origin,
        "content_hash": version.content_hash,
        "created_at": version.created_at,
        "created_by": str(version.created_by_id),
        "duplicate_ids": version.duplicate_ids,
        "reason": version.reason,
    }


def admin_data(scholarship: Scholarship) -> dict[str, Any]:
    assert scholarship.latest is not None
    events = ModerationEvent.objects.filter(scholarship=scholarship).order_by("created_at", "id")
    return {
        "id": str(scholarship.pk),
        "revision": scholarship.revision,
        "visibility": scholarship.visibility,
        "published_version_id": str(scholarship.published_version_id)
        if scholarship.published_version_id
        else None,
        "latest": candidate_data(scholarship.latest),
        "versions": [
            candidate_data(item)
            for item in scholarship.versions.select_related("source_revision").order_by("version")
        ],
        "history": [
            {
                "id": str(event.pk),
                "version_id": str(event.version_id),
                "action": event.action,
                "reason": event.reason,
                "actor_id": str(event.actor_id),
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def get_scholarship(scholarship_id: UUID, lock: bool = False) -> Scholarship:
    query = Scholarship.objects
    if lock:
        query = query.select_for_update()
    try:
        return query.get(pk=scholarship_id)
    except Scholarship.DoesNotExist as exc:
        raise IdentityError("NOT_FOUND", 404, "Scholarship not found") from exc


@transaction.atomic
def write_candidate(
    user: Account,
    proof: IdentitySession,
    data: dict[str, Any],
    correlation: Any,
    scholarship_id: UUID | None = None,
    expected: int | None = None,
) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    # Source before scholarship is the fixed catalog lock order for all mutating commands.
    try:
        source = (
            Source.objects.select_for_update(of=("self",))
            .select_related("current")
            .get(pk=data["source_id"])
        )
    except Source.DoesNotExist as exc:
        raise IdentityError("NOT_FOUND", 404, "Source not found") from exc
    permission = source.current
    if permission is None or not source_allowed(permission, data["origin"]):
        raise IdentityError("SOURCE_NOT_PERMITTED", 403, "This source does not permit this use")
    if scholarship_id:
        scholarship = get_scholarship(scholarship_id, lock=True)
        check_revision(scholarship, expected or 0)
    else:
        scholarship = Scholarship.objects.create()
    duplicates = list(
        ScholarshipVersion.objects.filter(
            Q(title__iexact=data["title"], provider__iexact=data["provider"])
            | Q(submission_url=data["submission_url"])
            if data["submission_url"]
            else Q(title__iexact=data["title"], provider__iexact=data["provider"])
        )
        .exclude(scholarship=scholarship)
        .values_list("scholarship_id", flat=True)
        .distinct()[:20]
    )
    values = {field: data[field] for field in FACTS}
    values.update(
        {
            field: data[field]
            for field in ("internal_notes", "origin", "source_checked_at", "reason")
        }
    )
    content_hash = hashlib.sha256(
        json.dumps(
            {**values, "source_revision_id": str(permission.pk)},
            sort_keys=True,
            cls=DjangoJSONEncoder,
        ).encode()
    ).hexdigest()
    confirmed = [
        datetime.fromisoformat(row["closes_at"])
        for row in data["rounds"]
        if row["kind"] == "CONFIRMED"
    ]
    version = ScholarshipVersion.objects.create(
        scholarship=scholarship,
        version=scholarship.versions.count() + 1,
        source_revision=permission,
        created_by=user,
        content_hash=content_hash,
        duplicate_ids=[str(value) for value in duplicates],
        next_deadline=min(confirmed, default=None),
        **values,
    )
    scholarship.latest = version
    scholarship.revision += 1
    scholarship.visibility = "REVERIFY" if scholarship.published_version_id else "DRAFT"
    scholarship.save(update_fields=["latest", "revision", "visibility"])
    record(user, "candidate_version_created", scholarship.pk, version.pk, correlation=correlation)
    return admin_data(scholarship)


@transaction.atomic
def moderate(
    user: Account,
    proof: IdentitySession,
    scholarship_id: UUID,
    data: dict[str, Any],
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    user = Account.objects.select_for_update().get(pk=user.pk)
    require_admin(user, proof, "MODERATION")
    # Resolve only to determine lock order; exact pointer is checked after the lock.
    snapshot = get_scholarship(scholarship_id)
    if snapshot.latest is None:
        raise IdentityError("INVALID_TRANSITION", 409, "No candidate version")
    source = (
        Source.objects.select_for_update(of=("self",))
        .select_related("current")
        .get(pk=snapshot.latest.source_revision.source_id)
    )
    scholarship = get_scholarship(scholarship_id, lock=True)
    check_revision(scholarship, expected)
    version = scholarship.latest
    if version is None or version.pk != data["version_id"]:
        raise IdentityError("STALE_VERSION", 409, "Review the exact current candidate version")
    action = data["action"]
    transitions = {
        "APPROVE": {"DRAFT", "REVERIFY"},
        "REJECT": {"DRAFT", "REVERIFY"},
        "REVERIFY": {"PUBLISHED", "REVERIFY"},
        "SUSPEND": {"PUBLISHED", "REVERIFY"},
        "ARCHIVE": {"PUBLISHED", "REVERIFY", "REJECTED", "SUSPENDED"},
        "RESTORE": {"SUSPENDED", "ARCHIVED"},
    }
    if scholarship.visibility not in transitions[action]:
        raise IdentityError("INVALID_TRANSITION", 409, "This moderation transition is unavailable")
    if action == "APPROVE":
        if (
            source.current is None
            or version.source_revision_id != source.current_id
            or not source_allowed(source.current, version.origin)
        ):
            raise IdentityError(
                "SOURCE_NOT_PERMITTED", 403, "Recheck current source permission before publication"
            )
        if (
            any(row["kind"] == "CONFIRMED" for row in version.rounds)
            and not version.source_checked_at
        ):
            raise IdentityError(
                "DEADLINE_UNVERIFIED", 409, "Confirmed deadlines need an attributable source check"
            )
    event = ModerationEvent.objects.create(
        scholarship=scholarship,
        version=version,
        action=action,
        content_hash=version.content_hash,
        actor=user,
        session_proof=proof,
        reason=data["reason"],
    )
    scholarship.visibility = {
        "APPROVE": "PUBLISHED",
        "RESTORE": "REVERIFY",
        "REJECT": "REJECTED",
        "REVERIFY": "REVERIFY",
        "SUSPEND": "SUSPENDED",
        "ARCHIVE": "ARCHIVED",
    }[action]
    if action == "APPROVE":
        scholarship.published_version = version
    scholarship.revision += 1
    scholarship.save(update_fields=["visibility", "published_version", "revision"])
    record(
        user,
        "moderation_" + action.lower(),
        scholarship.pk,
        event.version_id,
        correlation=correlation,
    )
    return admin_data(scholarship)


def published_query() -> QuerySet[ScholarshipVersion]:
    now = timezone.now()
    # The approval exists for exactly the public pointer/hash and the current permission
    # still allows the sealed version's use. Old approvals never override revocation.
    approved = ModerationEvent.objects.filter(
        version_id=models.OuterRef("pk"),
        scholarship_id=models.OuterRef("scholarship_id"),
        action="APPROVE",
        content_hash=models.OuterRef("content_hash"),
    )
    return (
        ScholarshipVersion.objects.filter(
            scholarship__visibility="PUBLISHED",
            scholarship__published_version_id=F("pk"),
            scholarship__latest_id=F("pk"),
            source_revision_id=F("source_revision__source__current_id"),
            source_revision__source__current__permission_status="APPROVED",
            source_revision__source__current__date_checked__lte=now,
        )
        .filter(
            Q(source_revision__source__current__valid_until__isnull=True)
            | Q(source_revision__source__current__valid_until__gt=now)
        )
        .filter(
            Q(origin="MANUAL", source_revision__source__current__allow_manual=True)
            | Q(origin="IMPORT", source_revision__source__current__allow_import=True)
        )
        .annotate(has_approval=models.Exists(approved))
        .filter(has_approval=True)
        .select_related("source_revision__source__current")
    )


def public_data(version: ScholarshipVersion) -> dict[str, Any]:
    now = timezone.now()
    source = version.source_revision
    policy = source.source.current
    assert policy is not None
    event = ModerationEvent.objects.filter(version=version, action="APPROVE").latest("created_at")
    freshness = "UNKNOWN"
    if version.source_checked_at and policy.freshness_days:
        freshness = (
            "CURRENT"
            if now < version.source_checked_at + timedelta(days=policy.freshness_days)
            else "STALE"
        )
    deadlines = [
        datetime.fromisoformat(row["closes_at"])
        for row in version.rounds
        if row["kind"] == "CONFIRMED"
    ]
    next_deadline = min((value for value in deadlines if value > now), default=None)
    return {
        **{field: getattr(version, field) for field in FACTS},
        "id": str(version.scholarship_id),
        "version_id": str(version.pk),
        "version": version.version,
        "source": {
            "id": str(source.source_id),
            "version_id": str(source.pk),
            "name": source.name,
            "url": source.url,
        },
        "source_checked_at": version.source_checked_at,
        "verified_at": event.created_at,
        "freshness": freshness,
        "next_deadline": next_deadline,
        "reminder_eligible": bool(next_deadline and freshness == "CURRENT"),
    }


def search(data: dict[str, Any]) -> dict[str, Any]:
    if data["mode"] != "TEXT":
        raise IdentityError(
            "SEARCH_MODE_UNAVAILABLE", 503, "Semantic search is not configured; choose text search"
        )
    query = published_query()
    if data["q"]:
        terms = SearchQuery(data["q"], config="simple", search_type="plain")
        query = query.filter(search_document=terms).annotate(
            rank=SearchRank(F("search_document"), terms)
        )
    for parameter, field in (
        ("education_level", "education_levels"),
        ("discipline", "disciplines"),
        ("country", "countries"),
        ("language", "languages"),
    ):
        if parameter in data:
            # The column comes only from this fixed mapping; input stays SQL parameters.
            alias = "matches_" + parameter
            query = query.annotate(
                **{
                    alias: RawSQL(
                        "EXISTS (SELECT 1 FROM jsonb_array_elements_text(CASE %s "
                        "WHEN 'education_levels' THEN education_levels "
                        "WHEN 'disciplines' THEN disciplines WHEN 'countries' THEN countries "
                        "ELSE languages END) label WHERE lower(label) = lower(%s))",
                        (field, data[parameter]),
                        output_field=models.BooleanField(),
                    )
                }
            ).filter(**{alias: True})
    if "funding" in data:
        query = query.filter(funding=data["funding"])
    # PostgreSQL computes the next confirmed future round, preserving multiple rounds.
    query = query.annotate(
        upcoming=RawSQL(
            "(SELECT min((r->>'closes_at')::timestamptz) FROM "
            "jsonb_array_elements(catalog_scholarshipversion.rounds) r "
            "WHERE r->>'kind' = 'CONFIRMED' AND (r->>'closes_at')::timestamptz > %s)",
            (timezone.now(),),
            output_field=models.DateTimeField(),
        )
    )
    if "deadline_before" in data:
        if data["deadline_before"] == date.max:
            query = query.filter(upcoming__isnull=False)
        else:
            end = datetime.combine(
                data["deadline_before"] + timedelta(days=1), time.min, tzinfo=UTC
            )
            query = query.filter(upcoming__lt=end)
    if data["sort"] == "deadline":
        query = query.order_by(F("upcoming").asc(nulls_last=True), "scholarship_id")
    elif data["sort"] == "relevance" and data["q"]:
        query = query.order_by("-rank", "scholarship_id")
    else:
        query = query.order_by("-created_at", "scholarship_id")
    total = query.count()
    start = (data["page"] - 1) * data["page_size"]
    return {
        "items": [public_data(version) for version in query[start : start + data["page_size"]]],
        "total": total,
        "page": data["page"],
        "page_size": data["page_size"],
        "search_mode": "TEXT",
    }
