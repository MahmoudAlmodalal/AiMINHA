from typing import Any

from drf_spectacular.utils import extend_schema_serializer
from identity.serializers import StrictSerializer
from rest_framework import serializers

KINDS = ["CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"]


class VersionInputSerializer(StrictSerializer):
    title = serializers.CharField(max_length=200)
    language = serializers.ChoiceField(choices=["ar", "en"])
    content = serializers.CharField(max_length=40000)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs["content"] = attrs["content"].replace("\r\n", "\n").replace("\r", "\n")
        # XML/PDF text must contain no hidden control instructions or invalid codepoints.
        for text in (attrs["title"], attrs["content"]):
            if any(
                ord(char) < 32
                and char not in "\n\t\r"
                or 0xD800 <= ord(char) <= 0xDFFF
                or ord(char) in {0xFFFE, 0xFFFF}
                for char in text
            ):
                raise serializers.ValidationError("Unsupported text control character")
        return attrs


class DocumentInputSerializer(VersionInputSerializer):
    kind = serializers.ChoiceField(choices=KINDS)


class VersionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    language = serializers.CharField()
    content = serializers.CharField()
    content_hash = serializers.CharField()
    preview_html = serializers.CharField()
    provenance = serializers.CharField()
    restored_from_id = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    approved = serializers.BooleanField()


class DocumentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    revision = serializers.IntegerField()
    current = VersionSerializer()


class DocumentPageSerializer(serializers.Serializer):
    items = DocumentSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class VersionPageSerializer(serializers.Serializer):
    items = VersionSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class VersionReferenceSerializer(StrictSerializer):
    version_id = serializers.UUIDField()


class ApprovalInputSerializer(VersionReferenceSerializer):
    content_hash = serializers.RegexField(r"^[a-f0-9]{64}$")
    confirm = serializers.BooleanField()

    def validate_confirm(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Explicit owner approval is required")
        return value


class ExportInputSerializer(VersionReferenceSerializer):
    format = serializers.ChoiceField(choices=["PDF", "DOCX"])


class ExportSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    format = serializers.CharField()
    asset_id = serializers.UUIDField()
    content_hash = serializers.CharField()
    created_at = serializers.DateTimeField()


@extend_schema_serializer(component_name="DocumentCapabilities")
class CapabilitiesSerializer(serializers.Serializer):
    manual_editing = serializers.BooleanField()
    private_ai = serializers.BooleanField()
    manual_fallback = serializers.BooleanField()
    reason = serializers.CharField()


class GenerateInputSerializer(DocumentInputSerializer):
    consent = serializers.BooleanField()


class ExtractInputSerializer(StrictSerializer):
    asset_id = serializers.UUIDField()
    consent = serializers.BooleanField()


class CompareSerializer(serializers.Serializer):
    left = VersionSerializer()
    right = VersionSerializer()
