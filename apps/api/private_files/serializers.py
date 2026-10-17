from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False, max_length=255)


@extend_schema_serializer(component_name="StoredPrivateFile")
class FileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=["ACCEPTED"])
    declared_size = serializers.IntegerField(min_value=1, max_value=5_000_000)
    created_at = serializers.DateTimeField()


class GrantSerializer(serializers.Serializer):
    token = serializers.CharField()
    expires_at = serializers.DateTimeField()


@extend_schema_serializer(component_name="PrivateFileCapabilities")
class CapabilitiesSerializer(serializers.Serializer):
    upload_available = serializers.BooleanField()
    manual_entry_available = serializers.BooleanField()
    allowed_mime_types = serializers.ListField(child=serializers.CharField())
    max_file_bytes = serializers.IntegerField()
    max_student_bytes = serializers.IntegerField()
    max_global_bytes = serializers.IntegerField()


class EmptySerializer(serializers.Serializer):
    pass


@extend_schema_serializer(component_name="PrivateFileAck")
class AckSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
