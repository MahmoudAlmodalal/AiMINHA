from typing import Any

from catalog.serializers import RequiredOutput
from identity.serializers import StrictSerializer
from rest_framework import serializers

FIELDS = [
    "nationalities",
    "residency_country",
    "degree_level",
    "major",
    "qualification",
    "gpa",
    "languages",
    "preferred_countries",
]
DOMAINS = ["ACADEMIC", "FIELD", "NATIONALITY_RESIDENCY", "LANGUAGE", "INTEREST"]
DEGREES = ["BACHELOR", "MASTER", "PHD"]
QUALIFICATIONS = ["SECONDARY", "DIPLOMA", "BACHELOR", "MASTER", "PHD", "OTHER"]
SCALES = ["PERCENT_100", "GPA_4_0", "GPA_5_0", "UNKNOWN"]
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
FIELD_DOMAIN = {
    "nationalities": "NATIONALITY_RESIDENCY",
    "residency_country": "NATIONALITY_RESIDENCY",
    "degree_level": "ACADEMIC",
    "qualification": "ACADEMIC",
    "gpa": "ACADEMIC",
    "major": "FIELD",
    "languages": "LANGUAGE",
    "preferred_countries": "INTEREST",
}


class CountryField(serializers.RegexField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(regex=r"^[A-Z]{2}$", max_length=2, **kwargs)


class GpaSerializer(StrictSerializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=4, min_value=0, max_value=100000)
    scale = serializers.ChoiceField(choices=SCALES)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        maximum = {"PERCENT_100": 100, "GPA_4_0": 4, "GPA_5_0": 5}.get(attrs["scale"])
        if maximum is not None and attrs["value"] > maximum:
            raise serializers.ValidationError("GPA exceeds its explicitly declared scale")
        return attrs


class LanguageSerializer(StrictSerializer):
    language = serializers.RegexField(regex=r"^[a-z]{2}(?:-[A-Z]{2})?$", max_length=5)
    level = serializers.ChoiceField(choices=LEVELS, allow_null=True)


class ProfileFactsSerializer(StrictSerializer):
    nationalities = serializers.ListField(
        child=CountryField(), max_length=5, allow_null=True, default=None
    )
    residency_country = CountryField(allow_null=True, default=None)
    degree_level = serializers.ChoiceField(choices=DEGREES, allow_null=True, default=None)
    major = serializers.CharField(max_length=200, allow_null=True, default=None)
    qualification = serializers.ChoiceField(choices=QUALIFICATIONS, allow_null=True, default=None)
    gpa = GpaSerializer(allow_null=True, default=None)
    languages = LanguageSerializer(many=True, max_length=20, allow_null=True, default=None)
    preferred_countries = serializers.ListField(
        child=CountryField(), max_length=30, allow_null=True, default=None
    )
    confirmed_fields = serializers.ListField(
        child=serializers.ChoiceField(choices=FIELDS), max_length=8, default=list
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        confirmed = attrs["confirmed_fields"]
        if len(confirmed) != len(set(confirmed)) or any(attrs[key] is None for key in confirmed):
            raise serializers.ValidationError("Confirm only distinct, explicitly known fields")
        if attrs["languages"] is not None:
            codes = [item["language"] for item in attrs["languages"]]
            if len(codes) != len(set(codes)):
                raise serializers.ValidationError("A language must have one explicit level")
        for field in ("nationalities", "preferred_countries"):
            if attrs[field] is not None and len(attrs[field]) != len(set(attrs[field])):
                raise serializers.ValidationError("Duplicate country values are not accepted")
        return attrs


class ProfileFactsOutputSerializer(RequiredOutput, ProfileFactsSerializer):
    pass


class ProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    revision = serializers.IntegerField()
    version_id = serializers.UUIDField(allow_null=True)
    profile = ProfileFactsOutputSerializer()
    confirmed_at = serializers.DateTimeField(allow_null=True)
    provenance = serializers.ChoiceField(choices=["STUDENT_CONFIRMED_MANUAL"])
    credential_verification = serializers.ChoiceField(choices=["NOT_INDEPENDENTLY_VERIFIED"])


class RuleSerializer(StrictSerializer):
    key = serializers.RegexField(regex=r"^[A-Za-z0-9_-]{1,64}$", max_length=64)
    criterion_index = serializers.IntegerField(min_value=0, max_value=49)
    field = serializers.ChoiceField(choices=FIELDS)
    domain = serializers.ChoiceField(choices=DOMAINS)
    operator = serializers.ChoiceField(
        choices=["ONE_OF", "INTERSECTS", "GPA_MIN", "LANGUAGE_MIN", "UNSUPPORTED"]
    )
    values = serializers.ListField(
        child=serializers.CharField(max_length=200), max_length=50, default=list
    )
    gpa = GpaSerializer(allow_null=True, default=None)
    language = LanguageSerializer(allow_null=True, default=None)
    mandatory = serializers.BooleanField(default=True)
    verified = serializers.BooleanField(default=False)
    evidence_text = serializers.CharField(max_length=2000)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        field, operator = attrs["field"], attrs["operator"]
        if attrs["domain"] != FIELD_DOMAIN[field]:
            raise serializers.ValidationError("A criterion cannot redefine its scoring domain")
        allowed = {
            "nationalities": "INTERSECTS",
            "preferred_countries": "INTERSECTS",
            "gpa": "GPA_MIN",
            "languages": "LANGUAGE_MIN",
            "residency_country": "ONE_OF",
            "degree_level": "ONE_OF",
            "major": "ONE_OF",
            "qualification": "ONE_OF",
        }
        if operator not in (allowed[field], "UNSUPPORTED"):
            raise serializers.ValidationError("Unsupported field/operator pair")
        if operator in {"ONE_OF", "INTERSECTS"}:
            if not attrs["values"] or attrs["gpa"] is not None or attrs["language"] is not None:
                raise serializers.ValidationError("A set comparison requires only explicit values")
            if field == "degree_level" and set(attrs["values"]) - set(DEGREES):
                raise serializers.ValidationError("Unknown degree code")
            if field == "qualification" and set(attrs["values"]) - set(QUALIFICATIONS):
                raise serializers.ValidationError("Unknown qualification code")
            if field in {"nationalities", "preferred_countries", "residency_country"}:
                for value in attrs["values"]:
                    CountryField().run_validation(value)
        if operator == "GPA_MIN" and (
            attrs["gpa"] is None or attrs["values"] or attrs["language"] is not None
        ):
            raise serializers.ValidationError(
                "A GPA comparison requires only a declared GPA threshold"
            )
        if operator == "LANGUAGE_MIN" and (
            attrs["language"] is None or attrs["values"] or attrs["gpa"] is not None
        ):
            raise serializers.ValidationError(
                "A language comparison requires only an explicit level"
            )
        if operator == "UNSUPPORTED" and (
            attrs["values"] or attrs["gpa"] is not None or attrs["language"] is not None
        ):
            raise serializers.ValidationError(
                "Unsupported criteria cannot smuggle executable conditions"
            )
        return attrs


class RuleOutputSerializer(RequiredOutput, RuleSerializer):
    pass


class RuleSetInputSerializer(StrictSerializer):
    scholarship_version_id = serializers.UUIDField()
    complete = serializers.BooleanField()
    rules = RuleSerializer(many=True, max_length=50, allow_empty=False)
    confirm_review = serializers.BooleanField()
    reason = serializers.CharField(max_length=1000)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs["confirm_review"]:
            raise serializers.ValidationError("An attributable human review is required")
        keys = [item["key"] for item in attrs["rules"]]
        if len(keys) != len(set(keys)):
            raise serializers.ValidationError("Rule keys must be unique")
        return attrs


class RuleSetSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField()
    scholarship_version_id = serializers.UUIDField()
    scholarship_hash = serializers.CharField()
    complete = serializers.BooleanField()
    rules = RuleOutputSerializer(many=True)
    content_hash = serializers.CharField()
    reviewed_by = serializers.UUIDField()
    reviewed_at = serializers.DateTimeField()
    reason = serializers.CharField()


class RuleHeadSerializer(serializers.Serializer):
    revision = serializers.IntegerField()
    rule_set = RuleSetSerializer(allow_null=True)


class EvaluationInputSerializer(StrictSerializer):
    profile_version_id = serializers.UUIDField()
    scholarship_id = serializers.UUIDField()
    scholarship_version_id = serializers.UUIDField()


class RuleEvidenceSerializer(serializers.Serializer):
    profile_field = serializers.ChoiceField(choices=FIELDS)
    profile_confirmed = serializers.BooleanField()
    criterion_index = serializers.IntegerField()
    source_text = serializers.CharField()


class RuleResultSerializer(serializers.Serializer):
    key = serializers.CharField()
    criterion_index = serializers.IntegerField()
    field = serializers.ChoiceField(choices=FIELDS)
    domain = serializers.ChoiceField(choices=DOMAINS)
    mandatory = serializers.BooleanField()
    result = serializers.ChoiceField(choices=["PASS", "FAIL", "UNKNOWN"])
    reason_code = serializers.CharField()
    expected_display = serializers.CharField()
    actual_display = serializers.CharField(allow_null=True)
    evidence = RuleEvidenceSerializer()


class DomainResultSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=DOMAINS)
    weight_bps = serializers.IntegerField(min_value=0, max_value=10000)
    covered = serializers.BooleanField()
    score_bps = serializers.IntegerField(min_value=0, max_value=10000, allow_null=True)
    contribution_bps = serializers.IntegerField(min_value=0, max_value=10000, allow_null=True)
    reason_code = serializers.CharField()


class ResultSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ELIGIBLE", "INELIGIBLE", "INSUFFICIENT_INFORMATION"])
    coverage_bps = serializers.IntegerField(min_value=0, max_value=10000)
    fit_score_bps = serializers.IntegerField(min_value=0, max_value=10000, allow_null=True)
    fit_status = serializers.ChoiceField(choices=["AVAILABLE", "INSUFFICIENT_COVERAGE"])
    confidence = serializers.ChoiceField(choices=["UNCALIBRATED"])
    domains = DomainResultSerializer(many=True)
    rules = RuleResultSerializer(many=True)
    missing_fields = serializers.ListField(child=serializers.CharField())
    limitations = serializers.ListField(child=serializers.CharField())


class EvaluationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    profile_version_id = serializers.UUIDField()
    scholarship_id = serializers.UUIDField()
    scholarship_version_id = serializers.UUIDField()
    rule_set_id = serializers.UUIDField(allow_null=True)
    policy_version = serializers.CharField()
    engine_version = serializers.CharField()
    weight_version = serializers.CharField()
    evaluated_at = serializers.DateTimeField()
    result = ResultSerializer()
