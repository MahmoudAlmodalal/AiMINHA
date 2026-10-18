"""Owned tracker aggregates and append-only student/official evidence streams."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

STATES = ["PREPARING", "READY", "SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"]


class SavedScholarship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scholarship = models.ForeignKey("catalog.Scholarship", on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "scholarship"], name="applications_saved_once")
        ]


class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scholarship = models.ForeignKey("catalog.Scholarship", on_delete=models.PROTECT)
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    profile_version = models.ForeignKey(
        "eligibility.ProfileVersion", null=True, on_delete=models.PROTECT
    )
    round_key = models.CharField(max_length=64)
    round_snapshot = models.JSONField()
    requirements_known = models.BooleanField(default=False)
    state = models.CharField(max_length=16, default="PREPARING", choices=[(s, s) for s in STATES])
    revision = models.PositiveIntegerField(default=0)
    head = models.ForeignKey(
        "ApplicationEvent", null=True, on_delete=models.PROTECT, related_name="+"
    )
    submitted_sequence = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "scholarship", "round_key"], name="applications_lifetime_round"
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=STATES), name="applications_known_state"
            ),
        ]


class ApplicationRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="requirements"
    )
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    key = models.CharField(max_length=64)
    label = models.CharField(max_length=500)
    position = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "scholarship_version", "key"],
                name="applications_requirement_key",
            ),
            models.UniqueConstraint(
                fields=["application", "scholarship_version", "position"],
                name="applications_requirement_position",
            ),
        ]


class SelectedArtifact(models.Model):
    requirement = models.OneToOneField(
        ApplicationRequirement, primary_key=True, on_delete=models.PROTECT
    )
    version = models.ForeignKey("documents.DocumentVersion", null=True, on_delete=models.PROTECT)
    asset = models.ForeignKey("privacy.PrivateAsset", null=True, on_delete=models.PROTECT)
    content_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(version__isnull=False, asset__isnull=True)
                    | models.Q(version__isnull=True, asset__isnull=False)
                ),
                name="applications_artifact_xor",
            )
        ]


class ApplicationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="events")
    sequence = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    session_proof = models.ForeignKey("identity.IdentitySession", on_delete=models.PROTECT)
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    profile_version = models.ForeignKey(
        "eligibility.ProfileVersion", null=True, on_delete=models.PROTECT
    )
    from_state = models.CharField(max_length=16, blank=True)
    to_state = models.CharField(max_length=16)
    kind = models.CharField(max_length=16)
    source = models.CharField(max_length=24, default="STUDENT_REPORTED")
    observed_at = models.DateTimeField()
    recorded_at = models.DateTimeField(default=timezone.now)
    evidence = models.CharField(max_length=1000, blank=True)
    reason = models.CharField(max_length=1000, blank=True)
    notes_snapshot = models.TextField(blank=True)
    manifest_snapshot = models.JSONField(default=list)
    correction_of_sequence = models.PositiveIntegerField(null=True)
    student_submission_confirmation = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "sequence"], name="applications_event_sequence"
            )
        ]


class SubmissionArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    event = models.ForeignKey(ApplicationEvent, on_delete=models.PROTECT)
    requirement = models.OneToOneField(ApplicationRequirement, on_delete=models.PROTECT)
    version = models.ForeignKey("documents.DocumentVersion", null=True, on_delete=models.PROTECT)
    asset = models.ForeignKey("privacy.PrivateAsset", null=True, on_delete=models.PROTECT)
    content_hash = models.CharField(max_length=64)
    label_snapshot = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(version__isnull=False, asset__isnull=True)
                    | models.Q(version__isnull=True, asset__isnull=False)
                ),
                name="applications_submission_xor",
            )
        ]


class OfficialStatusReport(models.Model):
    """An independent evidence stream; synthetic proof is never verified official."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="official_reports"
    )
    status = models.CharField(max_length=16)
    source_url = models.URLField(max_length=1000)
    observed_at = models.DateTimeField()
    recorded_at = models.DateTimeField(default=timezone.now)
    evidence_ref = models.CharField(max_length=200)
    origin = models.CharField(max_length=24)


class SubmittedArtifactDeletionRequest(models.Model):
    """An authorized request, never an approval or claim that evidence was erased."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    artifact = models.ForeignKey(SubmissionArtifact, on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    state = models.CharField(max_length=24, default="PENDING_LEGAL_REVIEW")
    created_at = models.DateTimeField(default=timezone.now)
