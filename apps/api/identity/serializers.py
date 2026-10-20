from typing import Any

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError(
                {"non_field_errors": ["Unknown fields are not accepted"]}
            )
        return super().to_internal_value(data)


class SignupSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        min_length=1, max_length=256, write_only=True, trim_whitespace=False
    )
    birth_date = serializers.DateField()
    locale = serializers.ChoiceField(choices=["ar", "en"])


class LoginSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        min_length=1, max_length=1024, write_only=True, trim_whitespace=False
    )


class PasswordSerializer(StrictSerializer):
    password = serializers.CharField(
        min_length=1, max_length=1024, write_only=True, trim_whitespace=False
    )


class EmailSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)


class ChallengeSerializer(StrictSerializer):
    challenge_token = serializers.CharField(min_length=20, max_length=2048, write_only=True)


class PasswordResetSerializer(ChallengeSerializer):
    password = serializers.CharField(
        min_length=1, max_length=256, write_only=True, trim_whitespace=False
    )


class AckSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    correlation_id = serializers.UUIDField()


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class SessionSerializer(serializers.Serializer):
    actor_id = serializers.UUIDField()
    verified_email = serializers.BooleanField()
    adult_eligible = serializers.BooleanField()
    roles = serializers.ListField(child=serializers.ChoiceField(choices=["STUDENT", "ADMIN"]))
    expires_at = serializers.DateTimeField()


class ReauthenticationSerializer(serializers.Serializer):
    reauthentication_token = serializers.CharField()


class GoogleStartSerializer(StrictSerializer):
    intent = serializers.ChoiceField(choices=["SIGN_IN", "LINK"])


class GoogleCallbackSerializer(StrictSerializer):
    code = serializers.CharField(max_length=4096, write_only=True)
    state = serializers.CharField(max_length=256, write_only=True)


class AuthorizationSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()
    expires_at = serializers.DateTimeField()


class ConsentRequestSerializer(StrictSerializer):
    disclosure_id = serializers.UUIDField()
    decision = serializers.ChoiceField(choices=["GRANT", "REVOKE"])


class ConsentSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    state = serializers.ChoiceField(choices=["GRANTED", "REVOKED"])
    disclosure_id = serializers.UUIDField()
    recorded_at = serializers.DateTimeField()


class ConsentPageSerializer(serializers.Serializer):
    items = ConsentSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class DisclosureSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField()
    disclosure = serializers.CharField(max_length=20000)
    available = serializers.BooleanField()


class DisclosurePageSerializer(serializers.Serializer):
    items = DisclosureSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class DeletionInputSerializer(StrictSerializer):
    confirm_impact = serializers.BooleanField()
    reauthentication_token = serializers.CharField(min_length=20, max_length=2048, write_only=True)

    def validate_confirm_impact(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Explicit confirmation is required")
        return value


class DeletionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=["PENDING", "RESTORED", "PURGING", "PURGED"])
    confirmed_at = serializers.DateTimeField()
    restore_until = serializers.DateTimeField()
    policy_id = serializers.UUIDField()
    recovery_days = serializers.IntegerField(min_value=1)
    recovery_timezone = serializers.CharField()


class DeletionImpactSerializer(serializers.Serializer):
    policy_id = serializers.UUIDField()
    recovery_days = serializers.IntegerField(min_value=1)
    recovery_timezone = serializers.CharField()
    cutoff_algorithm = serializers.CharField()
    available = serializers.BooleanField()


class FileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.ChoiceField(
        choices=[
            "INITIATED",
            "QUARANTINED",
            "SCANNING",
            "ACCEPTED",
            "REJECTED",
            "PURGE_PENDING",
            "PURGED",
        ]
    )
    declared_size = serializers.IntegerField(min_value=1)
    created_at = serializers.DateTimeField()


class FilePageSerializer(serializers.Serializer):
    items = FileSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
