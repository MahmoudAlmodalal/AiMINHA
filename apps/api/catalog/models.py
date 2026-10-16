"""Catalog facts are immutable proposals; publication is an attributable exact-version decision."""

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone


class Source(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.PositiveIntegerField(default=0)
    current = models.ForeignKey(
        "SourceRevision", null=True, on_delete=models.PROTECT, related_name="+"
    )


class SourceRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=1000)
    permission_status = models.CharField(
        max_length=16,
        choices=[(value, value) for value in ("UNVERIFIED", "APPROVED", "BLOCKED", "REVOKED")],
        default="UNVERIFIED",
    )
    license_basis = models.CharField(max_length=2000, blank=True)
    permission_evidence = models.CharField(max_length=2000, blank=True)
    date_checked = models.DateTimeField(null=True)
    valid_until = models.DateTimeField(null=True)
    allow_manual = models.BooleanField(default=True)
    allow_import = models.BooleanField(default=False)
    freshness_days = models.PositiveSmallIntegerField(null=True)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    session_proof = models.ForeignKey("identity.IdentitySession", on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "revision"], name="catalog_source_revision"),
            models.CheckConstraint(
                condition=models.Q(freshness_days__isnull=True)
                | models.Q(freshness_days__gte=1, freshness_days__lte=365),
                name="catalog_freshness_bounds",
            ),
            models.CheckConstraint(
                condition=~models.Q(permission_status="APPROVED")
                | (
                    ~models.Q(license_basis="")
                    & ~models.Q(permission_evidence="")
                    & models.Q(date_checked__isnull=False)
                ),
                name="catalog_approval_evidence",
            ),
        ]


class Scholarship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.PositiveIntegerField(default=0)
    visibility = models.CharField(
        max_length=16,
        default="DRAFT",
        choices=[
            (value, value)
            for value in ("DRAFT", "PUBLISHED", "REVERIFY", "SUSPENDED", "ARCHIVED", "REJECTED")
        ],
    )
    latest = models.ForeignKey(
        "ScholarshipVersion", null=True, on_delete=models.PROTECT, related_name="+"
    )
    published_version = models.ForeignKey(
        "ScholarshipVersion", null=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(visibility="PUBLISHED")
                | models.Q(published_version__isnull=False),
                name="catalog_published_pointer_required",
            )
        ]


class ScholarshipVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    source_revision = models.ForeignKey(SourceRevision, on_delete=models.PROTECT)
    title = models.CharField(max_length=300)
    provider = models.CharField(max_length=300)
    summary = models.TextField(blank=True)
    education_levels = models.JSONField(default=list)
    disciplines = models.JSONField(default=list)
    countries = models.JSONField(default=list)
    languages = models.JSONField(default=list)
    funding = models.CharField(max_length=16, default="UNKNOWN")
    criteria = models.JSONField(default=list)
    required_documents = models.JSONField(default=list)
    submission_url = models.URLField(max_length=1000, null=True)
    rounds = models.JSONField(default=list)
    source_checked_at = models.DateTimeField(null=True)
    origin = models.CharField(max_length=8, default="MANUAL")
    internal_notes = models.TextField(blank=True)
    reason = models.CharField(max_length=1000)
    content_hash = models.CharField(max_length=64)
    duplicate_ids = models.JSONField(default=list)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    search_document = SearchVectorField(null=True, editable=False)
    next_deadline = models.DateTimeField(null=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scholarship", "version"], name="catalog_scholarship_version"
            ),
            models.CheckConstraint(
                condition=models.Q(origin__in=["MANUAL", "IMPORT"]), name="catalog_origin_known"
            ),
        ]
        indexes = [GinIndex(fields=["search_document"], name="catalog_search_gin")]


class ModerationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.PROTECT)
    version = models.ForeignKey(ScholarshipVersion, on_delete=models.PROTECT)
    action = models.CharField(max_length=16)
    content_hash = models.CharField(max_length=64)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    session_proof = models.ForeignKey("identity.IdentitySession", on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)


class CatalogAudit(models.Model):
    """No query strings, source payloads, internal notes or student facts in audit metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(null=True)
    resource_id = models.UUIDField(null=True)
    version_id = models.UUIDField(null=True)
    action = models.CharField(max_length=64)
    outcome = models.CharField(max_length=8, default="ALLOW")
    reason = models.CharField(max_length=64, blank=True)
    correlation_id = models.UUIDField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
