from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from identity.serializers import StrictSerializer
from rest_framework import serializers

from support.models import AUTHOR_KINDS, PRIORITIES, STATES

EVENT_KINDS = [
    "CREATED",
    "STATE_CHANGED",
    "HUMAN_REQUESTED",
    "HUMAN_ASSIGNED",
    "FIRST_HUMAN_RESPONSE",
    "AI_REPLIED",
    "AI_HANDOFF",
    "AI_LIMIT_REACHED",
    "CLASSIFIED",
    "RATED",
    "REOPENED",
    "SLA_WARNING",
    "SLA_BREACH",
    "AUTO_CLOSED",
    "MESSAGE_ADDED",
]


class TicketCreateSerializer(StrictSerializer):
    category = serializers.CharField(max_length=128)
    subject = serializers.CharField(max_length=256)
    message = serializers.CharField(max_length=12000)
    request_human = serializers.BooleanField()
    urgency = serializers.ChoiceField(choices=PRIORITIES, required=False, default="NORMAL")


class MessageInputSerializer(StrictSerializer):
    body = serializers.CharField(max_length=12000)
    request_human = serializers.BooleanField()


class SupportTransitionInputSerializer(StrictSerializer):
    to_state = serializers.ChoiceField(
        choices=["AWAITING_ADMIN", "AWAITING_STUDENT", "RESOLVED", "CLOSED"]
    )
    reason_code = serializers.CharField(max_length=512)


class RatingInputSerializer(StrictSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)


class ShareInputSerializer(StrictSerializer):
    asset_id = serializers.UUIDField()


class ShareSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField(min_value=1)


class SupportAckSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()


class ClassificationInputSerializer(StrictSerializer):
    category = serializers.CharField(max_length=128)
    priority = serializers.ChoiceField(choices=PRIORITIES)
    reason_code = serializers.CharField(max_length=128)


class AssignmentInputSerializer(StrictSerializer):
    agent_id = serializers.UUIDField()
    reason_code = serializers.CharField(max_length=512)


class PageInputSerializer(StrictSerializer):
    page = serializers.IntegerField(min_value=1, max_value=100000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class QueueInputSerializer(PageInputSerializer):
    state = serializers.ChoiceField(choices=STATES, required=False)
    priority = serializers.ChoiceField(choices=PRIORITIES, required=False)


class PolicyInputSerializer(StrictSerializer):
    timezone = serializers.CharField(max_length=100)
    working_weekdays = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), min_length=1, max_length=7
    )
    opens_local = serializers.CharField(max_length=5)
    closes_local = serializers.CharField(max_length=5)
    holidays = serializers.ListField(child=serializers.CharField(max_length=10), max_length=366)
    targets = serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=100000))
    ai_daily_messages = serializers.IntegerField(min_value=1, max_value=1000)
    closure_days = serializers.IntegerField(min_value=1, max_value=365)
    reopen_days = serializers.IntegerField(min_value=1, max_value=365)
    rating_edit_days = serializers.IntegerField(min_value=1, max_value=365)
    warning_percent = serializers.IntegerField(min_value=1, max_value=100)
    effective_at = serializers.DateTimeField()
    reason_code = serializers.CharField(max_length=512)

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise serializers.ValidationError("Use a valid IANA timezone") from exc
        return value


class SlaCycleSerializer(serializers.Serializer):
    cycle_no = serializers.IntegerField(min_value=1)
    started_at = serializers.DateTimeField()
    responded_at = serializers.DateTimeField(allow_null=True)
    target_business_minutes = serializers.IntegerField(min_value=1)
    computed_due_at = serializers.DateTimeField()
    warning = serializers.BooleanField()
    breached = serializers.BooleanField()
    state = serializers.ChoiceField(choices=["OPEN", "COMPLETED"])


class SlaSerializer(serializers.Serializer):
    cycle_no = serializers.IntegerField(min_value=0)
    human_requested_at = serializers.DateTimeField(allow_null=True)
    computed_due_at = serializers.DateTimeField(allow_null=True)
    calendar_policy_id = serializers.UUIDField(allow_null=True)
    target_business_minutes = serializers.IntegerField(allow_null=True, min_value=1)
    first_human_response_at = serializers.DateTimeField(allow_null=True)
    elapsed_business_minutes = serializers.IntegerField(allow_null=True, min_value=0)
    warning = serializers.BooleanField()
    breached = serializers.BooleanField()
    met = serializers.BooleanField()
    cycles = SlaCycleSerializer(many=True)


class TicketSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=STATES)
    category = serializers.CharField(max_length=128)
    subject = serializers.CharField(max_length=256)
    priority = serializers.ChoiceField(choices=PRIORITIES)
    head_sequence = serializers.IntegerField(min_value=0)
    row_version = serializers.IntegerField(min_value=1)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    assigned = serializers.BooleanField()
    suggested_category = serializers.CharField(max_length=128, allow_blank=True)
    suggested_priority = serializers.CharField(max_length=8, allow_blank=True)
    triage_confidence = serializers.IntegerField(allow_null=True, min_value=0)
    triage_reason = serializers.CharField(max_length=512, allow_blank=True)
    resolved_at = serializers.DateTimeField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)
    reopen_until = serializers.DateTimeField(allow_null=True)
    rating_window_until = serializers.DateTimeField(allow_null=True)
    rating = serializers.IntegerField(allow_null=True, min_value=1, max_value=5)
    rating_available = serializers.BooleanField()
    rating_editable = serializers.BooleanField()
    sla = SlaSerializer()


class TicketPageSerializer(serializers.Serializer):
    items = TicketSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)


class MessageSerializer(serializers.Serializer):
    sequence = serializers.IntegerField(min_value=1)
    author_kind = serializers.ChoiceField(choices=AUTHOR_KINDS)
    body = serializers.CharField()
    substantive = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class MessagePageSerializer(serializers.Serializer):
    items = MessageSerializer(many=True)


class SupportEventSerializer(serializers.Serializer):
    sequence = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=EVENT_KINDS)
    from_state = serializers.CharField(max_length=16, allow_blank=True)
    to_state = serializers.CharField(max_length=16)
    reason = serializers.CharField(max_length=512, allow_blank=True)
    observed_at = serializers.DateTimeField()


class HistoryPageSerializer(serializers.Serializer):
    items = SupportEventSerializer(many=True)


class RatingSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField()
    value = serializers.IntegerField(min_value=1, max_value=5)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    editable_until = serializers.DateTimeField()


class AttachmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    asset_id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=["SHARED", "REVOKED"])
    version = serializers.IntegerField(min_value=1)
    created_at = serializers.DateTimeField()


class AttachmentPageSerializer(serializers.Serializer):
    items = AttachmentSerializer(many=True)


class QueueItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.ChoiceField(choices=STATES)
    category = serializers.CharField(max_length=128)
    priority = serializers.ChoiceField(choices=PRIORITIES)
    assigned = serializers.BooleanField()
    assigned_to_me = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    due_at = serializers.DateTimeField(allow_null=True)
    human_requested_at = serializers.DateTimeField(allow_null=True)
    first_human_response_at = serializers.DateTimeField(allow_null=True)
    warning = serializers.BooleanField()
    breached = serializers.BooleanField()
    row_version = serializers.IntegerField(min_value=1)


class QueuePageSerializer(serializers.Serializer):
    items = QueueItemSerializer(many=True)
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    page_size = serializers.IntegerField(min_value=1)


class AiOutcomeSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    reason = serializers.CharField(max_length=512, allow_blank=True)
    category = serializers.CharField(max_length=128, allow_blank=True)
    priority = serializers.CharField(max_length=8, allow_blank=True)
    confidence = serializers.IntegerField(allow_null=True, min_value=0)


class AiReplySerializer(serializers.Serializer):
    ticket = TicketSerializer()
    ai = AiOutcomeSerializer()


class PolicySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField(min_value=1)
    timezone = serializers.CharField(max_length=100)
    working_weekdays = serializers.ListField(child=serializers.IntegerField())
    opens_local = serializers.CharField(max_length=5)
    closes_local = serializers.CharField(max_length=5)
    holidays = serializers.ListField(child=serializers.CharField())
    targets = serializers.DictField(child=serializers.IntegerField())
    ai_daily_messages = serializers.IntegerField(min_value=1)
    closure_days = serializers.IntegerField(min_value=1)
    reopen_days = serializers.IntegerField(min_value=1)
    rating_edit_days = serializers.IntegerField(min_value=1)
    warning_percent = serializers.IntegerField(min_value=1, max_value=100)
    effective_at = serializers.DateTimeField()


class MetricsSerializer(serializers.Serializer):
    tickets = serializers.DictField()
