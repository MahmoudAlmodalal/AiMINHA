from identity.serializers import StrictSerializer
from rest_framework import serializers

from credits.models import SERVICES, STATES

ENTRY_KINDS = ["SIGNUP_GRANT", "DEBIT"]


class CreditPricesSerializer(serializers.Serializer):
    MATCHING_AI = serializers.IntegerField(min_value=1)
    CV_EXTRACTION = serializers.IntegerField(min_value=1)
    DOCUMENT_NEW = serializers.IntegerField(min_value=1)


class CreditPolicySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField()
    signup_grant = serializers.IntegerField(min_value=0)
    daily_spend_cap = serializers.IntegerField(min_value=0)
    global_ai_cap = serializers.IntegerField(min_value=0)
    timezone = serializers.ChoiceField(choices=["Asia/Hebron"])
    reserve_minutes = serializers.ChoiceField(choices=[15])
    reconciliation_target_hours = serializers.ChoiceField(choices=[24])
    prices = CreditPricesSerializer()
    free_services = serializers.ListField(child=serializers.CharField())
    ai_execution_available = serializers.BooleanField()


class CreditPolicyInputSerializer(StrictSerializer):
    signup_grant = serializers.IntegerField(min_value=0, max_value=1000000)
    daily_spend_cap = serializers.IntegerField(min_value=0, max_value=1000000)
    global_ai_cap = serializers.IntegerField(min_value=0, max_value=1000000)
    matching_price = serializers.IntegerField(min_value=1, max_value=1000000)
    cv_price = serializers.IntegerField(min_value=1, max_value=1000000)
    document_price = serializers.IntegerField(min_value=1, max_value=1000000)
    reason = serializers.CharField(max_length=1000)


class SignupGrantSerializer(serializers.Serializer):
    awarded = serializers.BooleanField()
    amount = serializers.IntegerField(allow_null=True)
    policy_version = serializers.IntegerField(allow_null=True)
    awarded_at = serializers.DateTimeField(allow_null=True)


class CreditDailySerializer(serializers.Serializer):
    day = serializers.DateField()
    timezone = serializers.ChoiceField(choices=["Asia/Hebron"])
    spent = serializers.IntegerField(min_value=0)
    reserved = serializers.IntegerField(min_value=0)
    cap = serializers.IntegerField(min_value=0)
    remaining = serializers.IntegerField(min_value=0)


class CreditGlobalDailySerializer(serializers.Serializer):
    day = serializers.DateField()
    timezone = serializers.ChoiceField(choices=["Asia/Hebron"])
    admitted_operations = serializers.IntegerField(min_value=0)
    cap = serializers.IntegerField(min_value=0)
    remaining = serializers.IntegerField(min_value=0)


class WalletSerializer(serializers.Serializer):
    posted_balance = serializers.IntegerField(min_value=0)
    reserved_balance = serializers.IntegerField(min_value=0)
    available_balance = serializers.IntegerField(min_value=0)
    signup_grant = SignupGrantSerializer()
    daily = CreditDailySerializer()
    global_daily = CreditGlobalDailySerializer()
    policy = CreditPolicySerializer()


class CreditEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=ENTRY_KINDS)
    amount = serializers.IntegerField()
    operation_id = serializers.UUIDField(allow_null=True)
    policy_version = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    reason_code = serializers.CharField()


class CreditOperationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    service = serializers.ChoiceField(choices=SERVICES)
    state = serializers.ChoiceField(choices=STATES)
    price = serializers.IntegerField(min_value=1)
    policy_version = serializers.IntegerField()
    captured_day = serializers.DateField()
    created_at = serializers.DateTimeField()
    reserve_until = serializers.DateTimeField()
    reconciliation_started_at = serializers.DateTimeField(allow_null=True)
    resolution_due_at = serializers.DateTimeField(allow_null=True)
    resolution_overdue = serializers.BooleanField()
    output_id = serializers.UUIDField(allow_null=True)


class CreditEntriesSerializer(serializers.Serializer):
    items = CreditEntrySerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50)


class CreditOperationsSerializer(serializers.Serializer):
    items = CreditOperationSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50)


class CreditPaginationSerializer(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=1000000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=20)
