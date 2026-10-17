"""Private document history; content never lives in command receipts or telemetry."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=24)
    revision = models.PositiveIntegerField(default=0)
    current = models.ForeignKey(
        "DocumentVersion", null=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["id", "owner"], name="documents_owner_key"),
            models.CheckConstraint(
                condition=models.Q(
                    kind__in=["CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"]
                ),
                name="documents_supported_kind",
            ),
        ]


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="versions")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=2)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    provenance = models.CharField(max_length=24, default="MANUAL")
    restored_from = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "number"], name="documents_version_number"),
            models.CheckConstraint(
                condition=models.Q(number__gte=1), name="documents_positive_version"
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=["ar", "en"]), name="documents_supported_language"
            ),
            models.CheckConstraint(
                condition=models.Q(provenance__in=["MANUAL", "SYNTHETIC_LOCAL"]),
                name="documents_known_provenance",
            ),
        ]


class DocumentApproval(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.OneToOneField(DocumentVersion, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)


class DocumentExport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    format = models.CharField(max_length=4)
    asset = models.OneToOneField(
        "privacy.PrivateAsset", on_delete=models.PROTECT, related_name="document_export"
    )
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["version", "format"], name="documents_export_once"),
            models.CheckConstraint(
                condition=models.Q(format__in=["PDF", "DOCX"]), name="documents_export_format"
            ),
        ]


class DocumentExportRequest(models.Model):
    """Opaque idempotency intent bound before conversion/scanner I/O."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    key_digest = models.CharField(max_length=64)
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT)
    format = models.CharField(max_length=4)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "key_digest"], name="documents_export_request_once"
            ),
            models.CheckConstraint(
                condition=models.Q(format__in=["PDF", "DOCX"]),
                name="documents_request_format",
            ),
        ]


class SubmissionSnapshot(models.Model):
    """Internal freeze primitive; Phase12 must supply a trusted owned application binding."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application_ref = models.UUIDField()
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT)
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application_ref", "version"], name="documents_snapshot_once"
            )
        ]


class SyntheticDocumentJob(models.Model):
    """Local-only accounting proof. No client endpoint or private-data route."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation = models.OneToOneField("credits.Operation", on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=24)
    language = models.CharField(max_length=2)
    request_hash = models.CharField(max_length=64)
    version = models.ForeignKey(DocumentVersion, null=True, on_delete=models.PROTECT)
    proposal = models.JSONField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
