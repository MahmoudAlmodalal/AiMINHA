"""Strict source dates, never a guessed end-of-day or guessed timezone."""

import re
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers


def parse_round(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    kind = result["kind"]
    raw = result.get("closes_at")
    day = result.get("deadline_date")
    zone_name = result.get("timezone")
    for key in ("closes_at", "deadline_date", "timezone"):
        result.setdefault(key, None)
    if kind in {"UNKNOWN", "ROLLING"}:
        if raw is not None or day is not None:
            raise serializers.ValidationError("An unknown or rolling deadline has no fixed date")
        if zone_name:
            try:
                ZoneInfo(zone_name)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise serializers.ValidationError("Unknown IANA timezone") from exc
        return result
    if kind == "DATE_ONLY":
        if not day or raw is not None:
            raise serializers.ValidationError("Date-only rounds need only a source calendar date")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise serializers.ValidationError("Use an ISO calendar date")
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise serializers.ValidationError("Invalid calendar date") from exc
        if zone_name:
            try:
                ZoneInfo(zone_name)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise serializers.ValidationError("Unknown IANA timezone") from exc
        return result
    if not raw or not zone_name or day is not None or not result.get("source_text", "").strip():
        raise serializers.ValidationError("Confirmed deadlines require source text, time and zone")
    # datetime.fromisoformat alone accepts compact dates and other unreviewable variants.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?", raw
    ):
        raise serializers.ValidationError("Use an ISO date and explicit source local time")
    try:
        parsed = datetime.fromisoformat(raw)
        zone = ZoneInfo(zone_name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise serializers.ValidationError("Invalid deadline or timezone") from exc
    try:
        if raw.endswith("Z"):
            # Canonical absolute UTC instant (also the API response format). The IANA
            # zone is its display/source zone; Z never claims donor-local wall time.
            instant = parsed.astimezone(UTC)
            instant.astimezone(zone)  # Ensure the source-local date is representable.
        else:
            local = parsed.replace(tzinfo=None)
            candidates = {
                local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                for fold in (0, 1)
                if local.replace(tzinfo=zone, fold=fold)
                .astimezone(UTC)
                .astimezone(zone)
                .replace(tzinfo=None)
                == local
            }
            if parsed.tzinfo is not None:
                instant = parsed.astimezone(UTC)
                if instant not in candidates:
                    raise serializers.ValidationError(
                        "The UTC offset does not match the source timezone"
                    )
            elif len(candidates) == 1:
                instant = candidates.pop()
            else:
                raise serializers.ValidationError("Ambiguous or nonexistent source local time")
    except (OverflowError, ValueError) as exc:
        raise serializers.ValidationError("Deadline is outside the supported calendar") from exc
    result["closes_at"] = instant.isoformat().replace("+00:00", "Z")
    return result
