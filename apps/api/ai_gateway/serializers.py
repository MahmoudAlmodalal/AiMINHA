from rest_framework import serializers


class AICapabilitiesSerializer(serializers.Serializer):
    live_execution_available = serializers.BooleanField()
    mock_client_execution_available = serializers.BooleanField()
    classification_required = serializers.BooleanField()
    allowed_classifications = serializers.ListField(child=serializers.CharField())
    logical_daily_cap = serializers.IntegerField(min_value=0)
    cloudflare_neurons_ceiling = serializers.IntegerField(min_value=0)
    reason_codes = serializers.ListField(child=serializers.CharField())
