from typing import Any

from catalog.serializers import PublicRoundSerializer, ZonedTimestamp
from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from identity.serializers import StrictSerializer
from rest_framework import serializers

from applications.models import STATES


class CreateSerializer(StrictSerializer):
    scholarship_id = serializers.UUIDField()
    round_key = serializers.RegexField(r"^[0-9a-f]{64}$")


class PageInputSerializer(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=100000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class SavedInputSerializer(StrictSerializer):
    scholarship_id = serializers.UUIDField()


class NotesInputSerializer(StrictSerializer):
    notes = serializers.CharField(max_length=5000, allow_blank=True, trim_whitespace=False)


class RebaseInputSerializer(StrictSerializer):
    confirm = serializers.BooleanField()


class TransitionInputSerializer(StrictSerializer):
    to_state = serializers.ChoiceField(choices=STATES)
    observed_at = ZonedTimestamp()
    evidence = serializers.CharField(max_length=1000)
    confirm_external_submission = serializers.BooleanField(default=False)

    def validate_observed_at(self, value: Any) -> Any:
        if value > timezone.now():
            raise serializers.ValidationError("Observation cannot be in the future")
        return value


class CorrectionInputSerializer(StrictSerializer):
    correction_of_sequence = serializers.IntegerField(min_value=1)
    observed_at = ZonedTimestamp()
    evidence = serializers.CharField(max_length=1000)
    reason = serializers.CharField(max_length=1000)

    def validate_observed_at(self, value: Any) -> Any:
        if value > timezone.now():
            raise serializers.ValidationError("Observation cannot be in the future")
        return value


class ArtifactInputSerializer(StrictSerializer):
    version_id = serializers.UUIDField(allow_null=True, default=None)
    asset_id = serializers.UUIDField(allow_null=True, default=None)
    content_hash = serializers.RegexField(r"^[0-9a-f]{64}$", required=False)
    clear = serializers.BooleanField(default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["clear"]:
            if attrs["version_id"] or attrs["asset_id"] or "content_hash" in attrs:
                raise serializers.ValidationError("Clearing cannot select another artifact")
        elif bool(attrs["version_id"]) == bool(attrs["asset_id"]) or "content_hash" not in attrs:
            raise serializers.ValidationError(
                "Select one exact document version or upload and its hash"
            )
        return attrs


class RoundOptionSerializer(PublicRoundSerializer):
    round_key = serializers.CharField()


class RoundOptionsSerializer(serializers.Serializer):
    scholarship_id = serializers.UUIDField()
    scholarship_version_id = serializers.UUIDField()
    items = RoundOptionSerializer(many=True)


class RequirementSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    kind = serializers.ChoiceField(choices=["DOCUMENT"])
    status = serializers.ChoiceField(choices=["MISSING", "COMPLETE"])
    version_id = serializers.UUIDField(allow_null=True)
    asset_id = serializers.UUIDField(allow_null=True)
    content_hash = serializers.CharField(allow_null=True)


class RequirementsSerializer(serializers.Serializer):
    requirements_known = serializers.BooleanField()
    items = RequirementSerializer(many=True)


class OfficialReportSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=STATES)
    source_url = serializers.URLField()
    observed_at = serializers.DateTimeField()
    recorded_at = serializers.DateTimeField()
    evidence_ref = serializers.CharField()
    origin = serializers.ChoiceField(choices=["VERIFIED_OFFICIAL", "SYNTHETIC_LOCAL"])
    verified_official = serializers.BooleanField()


@extend_schema_serializer(component_name="ApplicationDeadline")
class DeadlineSerializer(serializers.Serializer):
    kind = serializers.CharField()
    closes_at = serializers.DateTimeField(allow_null=True)
    source_timezone = serializers.CharField(allow_null=True)
    display_at = serializers.CharField(allow_null=True)
    display_timezone = serializers.CharField()
    eligible = serializers.BooleanField()
    reason = serializers.CharField()
    source_version_id = serializers.UUIDField(allow_null=True)


class ApplicationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    scholarship_id = serializers.UUIDField()
    scholarship_version_id = serializers.UUIDField()
    title = serializers.CharField()
    round_key = serializers.CharField()
    round_snapshot = RoundOptionSerializer()
    profile_version_id = serializers.UUIDField(allow_null=True)
    state = serializers.ChoiceField(choices=STATES)
    revision = serializers.IntegerField()
    submitted_sequence = serializers.IntegerField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)
    requirements_known = serializers.BooleanField()
    requirements = RequirementSerializer(many=True)
    missing_count = serializers.IntegerField()
    allowed_transitions = serializers.ListField(child=serializers.ChoiceField(choices=STATES))
    official_integration_available = serializers.BooleanField()
    official_reports = OfficialReportSerializer(many=True)
    created_at = serializers.DateTimeField()
    deadline = DeadlineSerializer()
    source_changed = serializers.BooleanField()
    can_rebase = serializers.BooleanField()


class ApplicationPageSerializer(serializers.Serializer):
    items = ApplicationSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    counts = serializers.DictField(child=serializers.IntegerField())
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()


class ManifestSerializer(serializers.Serializer):
    key = serializers.CharField()
    version_id = serializers.UUIDField(allow_null=True)
    asset_id = serializers.UUIDField(allow_null=True)
    content_hash = serializers.CharField()


class EventSerializer(serializers.Serializer):
    sequence = serializers.IntegerField()
    from_state = serializers.CharField(allow_blank=True)
    to_state = serializers.ChoiceField(choices=STATES)
    kind = serializers.ChoiceField(
        choices=["CREATED", "TRANSITION", "NOTES", "ARTIFACT", "CORRECTION", "REBASE"]
    )
    source = serializers.ChoiceField(choices=["STUDENT_REPORTED"])
    observed_at = serializers.DateTimeField()
    recorded_at = serializers.DateTimeField()
    evidence = serializers.CharField(allow_blank=True)
    reason = serializers.CharField(allow_blank=True)
    notes_snapshot = serializers.CharField(allow_blank=True)
    manifest_snapshot = ManifestSerializer(many=True)
    correction_of_sequence = serializers.IntegerField(allow_null=True)
    student_submission_confirmation = serializers.BooleanField()
    scholarship_version_id = serializers.UUIDField()
    profile_version_id = serializers.UUIDField(allow_null=True)


class HistorySerializer(serializers.Serializer):
    items = EventSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class SubmissionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    requirement_key = serializers.CharField()
    label_snapshot = serializers.CharField()
    version_id = serializers.UUIDField(allow_null=True)
    document_id = serializers.UUIDField(allow_null=True)
    asset_id = serializers.UUIDField(allow_null=True)
    content_hash = serializers.CharField()
    submitted_sequence = serializers.IntegerField()


class SubmissionPageSerializer(serializers.Serializer):
    items = SubmissionSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class SavedSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    scholarship_id = serializers.UUIDField()
    title = serializers.CharField(allow_blank=True)
    active = serializers.BooleanField()
    revision = serializers.IntegerField()


class SavedPageSerializer(serializers.Serializer):
    items = SavedSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()


class VersionOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    title = serializers.CharField()
    language = serializers.CharField()
    number = serializers.IntegerField()
    content_hash = serializers.CharField()


class FileOptionSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    declared_size = serializers.IntegerField()
    content_hash = serializers.CharField()
    mime = serializers.CharField()


class ArtifactOptionsSerializer(serializers.Serializer):
    versions = VersionOptionSerializer(many=True)
    files = FileOptionSerializer(many=True)


@extend_schema_serializer(component_name="SubmittedArtifactDeletionInput")
class DeletionInputSerializer(StrictSerializer):
    artifact_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=1000)


@extend_schema_serializer(component_name="SubmittedArtifactDeletion")
class DeletionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    artifact_id = serializers.UUIDField()
    reason = serializers.CharField()
    state = serializers.ChoiceField(choices=["PENDING_LEGAL_REVIEW"])
    created_at = serializers.DateTimeField()


class DeletionPageSerializer(serializers.Serializer):
    items = DeletionSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
