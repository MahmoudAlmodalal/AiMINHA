"""Exact-byte storage evidence; ownership remains exclusively in privacy.PrivateAsset."""

import uuid
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone


def storage_lease_deadline() -> datetime:
    return timezone.now() + timedelta(minutes=5)


class StorageLock(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)


class StoredFile(models.Model):
    asset = models.OneToOneField("privacy.PrivateAsset", primary_key=True, on_delete=models.PROTECT)
    operation_digest = models.CharField(max_length=64)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    mime = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    storage_token = models.UUIDField(default=uuid.uuid4, unique=True)
    capacity_bytes = models.PositiveIntegerField()
    capacity_state = models.CharField(max_length=12, default="RESERVED")
    created_at = models.DateTimeField(default=timezone.now)
    lease_expires_at = models.DateTimeField(default=storage_lease_deadline)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operation_digest"],
                condition=~models.Q(capacity_state="RELEASED"),
                name="files_one_live_operation",
            ),
            models.CheckConstraint(
                condition=models.Q(size__gte=1, size__lte=5_000_000), name="files_bounded_size"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        capacity_state__in=["RESERVED", "RETAINED"], capacity_bytes=models.F("size")
                    )
                    | models.Q(capacity_state="RELEASED", capacity_bytes=0)
                ),
                name="files_exact_capacity",
            ),
        ]


class ScanReceipt(models.Model):
    file = models.OneToOneField(StoredFile, primary_key=True, on_delete=models.PROTECT)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    engine = models.CharField(max_length=160)
    signature_version = models.CharField(max_length=32)
    signature_at = models.DateTimeField()
    scanned_at = models.DateTimeField(default=timezone.now)
    verdict = models.CharField(max_length=8, default="CLEAN")


class AccessGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(StoredFile, on_delete=models.PROTECT)
    actor = models.ForeignKey("identity.Account", on_delete=models.PROTECT)
    session = models.ForeignKey("identity.IdentitySession", on_delete=models.PROTECT)
    share = models.ForeignKey("privacy.TicketShare", null=True, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    sha256 = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
