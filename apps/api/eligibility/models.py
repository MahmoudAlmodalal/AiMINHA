"""Private manual profile snapshots and exact-version, human-reviewed rule evidence."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProfileHead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=0)
    current = models.ForeignKey(
        "ProfileVersion", null=True, on_delete=models.PROTECT, related_name="+"
    )


class ProfileVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    # The strict ProfileFacts serializer is the typed schema. Nulls are preserved;
    # confirmation is separate and cannot turn null into a known fact.
    facts = models.JSONField()
    confirmed_fields = models.JSONField(default=list)
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "version"], name="eligibility_profile_version"
            ),
            models.UniqueConstraint(fields=["id", "owner"], name="eligibility_profile_owner_key"),
        ]


class RuleHead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scholarship = models.OneToOneField("catalog.Scholarship", on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=0)
    current = models.ForeignKey("RuleSet", null=True, on_delete=models.PROTECT, related_name="+")


class RuleSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    head = models.ForeignKey(RuleHead, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    scholarship_hash = models.CharField(max_length=64)
    complete = models.BooleanField(default=False)
    rules = models.JSONField()
    content_hash = models.CharField(max_length=64)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    session_proof = models.ForeignKey("identity.IdentitySession", on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["head", "version"], name="eligibility_rule_version"),
        ]


class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    profile_version = models.ForeignKey(ProfileVersion, on_delete=models.PROTECT)
    scholarship_version = models.ForeignKey("catalog.ScholarshipVersion", on_delete=models.PROTECT)
    rule_set = models.ForeignKey(RuleSet, null=True, on_delete=models.PROTECT)
    policy_version = models.CharField(max_length=32, default="phase08-v1")
    policy_snapshot = models.JSONField()
    source_freshness = models.CharField(max_length=8)
    result = models.JSONField()
    evaluated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["owner", "evaluated_at"], name="eligibility_owner_history")]
