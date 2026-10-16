from typing import Any
from urllib.parse import urlsplit

from django.utils import timezone
from identity.serializers import StrictSerializer
from rest_framework import serializers

from catalog.deadlines import parse_round

PERMISSIONS = ["UNVERIFIED", "APPROVED", "BLOCKED", "REVOKED"]
FUNDING = ["FULL", "PARTIAL", "WAIVER", "AID", "UNKNOWN"]
VISIBILITY = ["DRAFT", "PUBLISHED", "REVERIFY", "SUSPENDED", "ARCHIVED", "REJECTED"]


class PublicURLField(serializers.URLField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(max_length=1000, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname or ""
            port = parsed.port
        except ValueError as exc:
            raise serializers.ValidationError("Invalid public URL") from exc
        # No network is made. Conservative links also reject credentials, query tokens,
        # fragments, literal IPs, local hosts and nonstandard ports in reviewed facts.
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or port not in (None, 443)
            or "." not in hostname
            or ":" in hostname
            or hostname.replace(".", "").isdigit()
            or hostname.endswith((".local", ".localhost", ".internal"))
        ):
            raise serializers.ValidationError("A public HTTPS source URL is required")
        return value


class ZonedTimestamp(serializers.DateTimeField):
    def to_internal_value(self, value: Any) -> Any:
        if isinstance(value, str) and not (
            value.endswith("Z") or (len(value) >= 6 and value[-6] in "+-" and value[-3] == ":")
        ):
            raise serializers.ValidationError("An explicit UTC offset is required")
        return super().to_internal_value(value)


class SourceInputSerializer(StrictSerializer):
    name = serializers.CharField(max_length=200)
    url = PublicURLField()
    permission_status = serializers.ChoiceField(choices=PERMISSIONS, default="UNVERIFIED")
    license_basis = serializers.CharField(max_length=2000, allow_blank=True, default="")
    permission_evidence = serializers.CharField(max_length=2000, allow_blank=True, default="")
    date_checked = ZonedTimestamp(allow_null=True, default=None)
    valid_until = ZonedTimestamp(allow_null=True, default=None)
    allow_manual = serializers.BooleanField(default=True)
    allow_import = serializers.BooleanField(default=False)
    freshness_days = serializers.IntegerField(
        min_value=1, max_value=365, allow_null=True, default=None
    )
    reason = serializers.CharField(max_length=1000)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["date_checked"] and attrs["date_checked"] > timezone.now():
            raise serializers.ValidationError("A check cannot be in the future")
        if attrs["permission_status"] == "APPROVED" and (
            not attrs["license_basis"]
            or not attrs["permission_evidence"]
            or not attrs["date_checked"]
        ):
            raise serializers.ValidationError("Source approval needs checked license and evidence")
        if attrs["valid_until"] and (
            not attrs["date_checked"] or attrs["valid_until"] <= attrs["date_checked"]
        ):
            raise serializers.ValidationError("Permission expiry must follow its check")
        if (
            attrs["permission_status"] == "APPROVED"
            and attrs["valid_until"]
            and attrs["valid_until"] <= timezone.now()
        ):
            raise serializers.ValidationError("Approved permission must not already be expired")
        return attrs


class RequiredOutput:
    def get_fields(self) -> dict[str, Any]:
        fields = super().get_fields()  # type: ignore[misc]
        for field in fields.values():
            field.required = True
            field.default = serializers.empty
        return fields


class SourceSerializer(RequiredOutput, SourceInputSerializer):
    id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    revision = serializers.IntegerField()
    editor_id = serializers.UUIDField()
    automation_enabled = serializers.BooleanField()


class RoundSerializer(StrictSerializer):
    kind = serializers.ChoiceField(choices=["UNKNOWN", "ROLLING", "DATE_ONLY", "CONFIRMED"])
    label = serializers.CharField(max_length=200, allow_blank=True, default="")
    source_text = serializers.CharField(max_length=1000, allow_blank=True, default="")
    closes_at = serializers.CharField(max_length=64, allow_null=True, default=None)
    deadline_date = serializers.CharField(max_length=10, allow_null=True, default=None)
    timezone = serializers.CharField(max_length=100, allow_null=True, default=None)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        return parse_round(attrs)


class PublicRoundSerializer(RequiredOutput, RoundSerializer):
    pass


class CandidateInputSerializer(StrictSerializer):
    source_id = serializers.UUIDField()
    title = serializers.CharField(max_length=300)
    provider = serializers.CharField(max_length=300)
    summary = serializers.CharField(max_length=10000, allow_blank=True, default="")
    education_levels = serializers.ListField(
        child=serializers.ChoiceField(choices=["BACHELOR", "MASTER", "PHD"]),
        max_length=3,
        default=list,
    )
    disciplines = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=30, default=list
    )
    countries = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=30, default=list
    )
    languages = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=30, default=list
    )
    funding = serializers.ChoiceField(choices=FUNDING, default="UNKNOWN")
    criteria = serializers.ListField(
        child=serializers.CharField(max_length=1000), max_length=50, default=list
    )
    required_documents = serializers.ListField(
        child=serializers.CharField(max_length=500), max_length=50, default=list
    )
    submission_url = PublicURLField(allow_null=True, default=None)
    rounds = RoundSerializer(
        many=True,
        max_length=20,
        allow_empty=False,
        default=lambda: [
            {
                "kind": "UNKNOWN",
                "label": "",
                "source_text": "",
                "closes_at": None,
                "deadline_date": None,
                "timezone": None,
            }
        ],
    )
    source_checked_at = ZonedTimestamp(allow_null=True, default=None)
    internal_notes = serializers.CharField(max_length=10000, allow_blank=True, default="")
    origin = serializers.ChoiceField(choices=["MANUAL", "IMPORT"], default="MANUAL")
    reason = serializers.CharField(max_length=1000)

    def validate_source_checked_at(self, value: Any) -> Any:
        if value and value > timezone.now():
            raise serializers.ValidationError("A source check cannot be in the future")
        return value


class SourceCitationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    name = serializers.CharField()
    url = PublicURLField()


class PublicScholarshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    version = serializers.IntegerField()
    title = serializers.CharField()
    provider = serializers.CharField()
    summary = serializers.CharField()
    education_levels = serializers.ListField(child=serializers.CharField())
    disciplines = serializers.ListField(child=serializers.CharField())
    countries = serializers.ListField(child=serializers.CharField())
    languages = serializers.ListField(child=serializers.CharField())
    funding = serializers.ChoiceField(choices=FUNDING)
    criteria = serializers.ListField(child=serializers.CharField())
    required_documents = serializers.ListField(child=serializers.CharField())
    submission_url = PublicURLField(allow_null=True)
    source = SourceCitationSerializer()
    source_checked_at = serializers.DateTimeField(allow_null=True)
    verified_at = serializers.DateTimeField()
    freshness = serializers.ChoiceField(choices=["CURRENT", "STALE", "UNKNOWN"])
    rounds = PublicRoundSerializer(many=True)
    next_deadline = serializers.DateTimeField(allow_null=True)
    reminder_eligible = serializers.BooleanField()


class SearchInputSerializer(StrictSerializer):
    q = serializers.CharField(max_length=200, allow_blank=True, default="")
    education_level = serializers.ChoiceField(choices=["BACHELOR", "MASTER", "PHD"], required=False)
    discipline = serializers.CharField(max_length=80, required=False)
    country = serializers.CharField(max_length=80, required=False)
    language = serializers.CharField(max_length=80, required=False)
    funding = serializers.ChoiceField(choices=FUNDING, required=False)
    deadline_before = serializers.DateField(required=False)
    sort = serializers.ChoiceField(choices=["recent", "deadline", "relevance"], default="recent")
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=20)
    mode = serializers.ChoiceField(choices=["TEXT", "SEMANTIC"], default="TEXT")


class PublicPageSerializer(serializers.Serializer):
    items = PublicScholarshipSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    search_mode = serializers.ChoiceField(choices=["TEXT"])


class CandidateSerializer(RequiredOutput, CandidateInputSerializer):
    rounds = PublicRoundSerializer(many=True)
    id = serializers.UUIDField()
    version = serializers.IntegerField()
    source_revision_id = serializers.UUIDField()
    content_hash = serializers.CharField()
    created_at = serializers.DateTimeField()
    created_by = serializers.UUIDField()
    duplicate_ids = serializers.ListField(child=serializers.UUIDField())


class ModerationSerializer(StrictSerializer):
    version_id = serializers.UUIDField()
    action = serializers.ChoiceField(
        choices=["APPROVE", "REJECT", "REVERIFY", "SUSPEND", "ARCHIVE", "RESTORE"]
    )
    reason = serializers.CharField(max_length=1000)


class ModerationEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    action = serializers.CharField()
    reason = serializers.CharField()
    actor_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()


class AdminScholarshipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    revision = serializers.IntegerField()
    visibility = serializers.ChoiceField(choices=VISIBILITY)
    published_version_id = serializers.UUIDField(allow_null=True)
    latest = CandidateSerializer()
    versions = CandidateSerializer(many=True)
    history = ModerationEventSerializer(many=True)


class AdminSearchSerializer(StrictSerializer):
    visibility = serializers.ChoiceField(choices=VISIBILITY, required=False)
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=20)


class AdminPageSerializer(serializers.Serializer):
    items = AdminScholarshipSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()


class SourcePageSerializer(serializers.Serializer):
    items = SourceSerializer(many=True)
