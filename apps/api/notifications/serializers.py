from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from identity.serializers import StrictSerializer
from rest_framework import serializers


class EmptyInputSerializer(StrictSerializer):
    pass


class InboxQuerySerializer(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=100000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
    unread_only = serializers.BooleanField(default=False)


class PreferenceInputSerializer(StrictSerializer):
    timezone = serializers.CharField(max_length=100)
    deadline_enabled = serializers.BooleanField()
    source_enabled = serializers.BooleanField()
    document_enabled = serializers.BooleanField()

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise serializers.ValidationError("Use a valid IANA timezone") from exc
        return value


class PreferenceSerializer(serializers.Serializer):
    revision = serializers.IntegerField()
    timezone = serializers.CharField()
    deadline_enabled = serializers.BooleanField()
    source_enabled = serializers.BooleanField()
    document_enabled = serializers.BooleanField()


class TargetSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["APPLICATION", "SCHOLARSHIP"])
    id = serializers.UUIDField()
    available = serializers.BooleanField()


class NotificationDeadlineSerializer(serializers.Serializer):
    closes_at = serializers.DateTimeField()
    source_timezone = serializers.CharField()
    # Preserve the user's explicitly selected display offset instead of rendering UTC.
    display_at = serializers.CharField()
    display_timezone = serializers.CharField()
    current = serializers.BooleanField()


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    category = serializers.ChoiceField(choices=["DEADLINE", "SOURCE_CHANGE", "DOCUMENT_MISSING"])
    event_id = serializers.UUIDField()
    event_version = serializers.IntegerField()
    offset_minutes = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)
    target = TargetSerializer()
    deadline = NotificationDeadlineSerializer(allow_null=True)


class InboxSerializer(serializers.Serializer):
    items = NotificationSerializer(many=True)
    total = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
