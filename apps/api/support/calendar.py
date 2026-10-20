"""Business-hours arithmetic on an administrator working calendar.

Pure functions only: no database, no request, no wall-clock reading. Business time is
defined in the calendar's local wall clock. Each working day's window is resolved to
absolute instants in that zone, so a daylight-saving transition changes the absolute
instants without changing the staffed window, and the measured interval never runs
backwards across a transition. Durations are computed in whole seconds so that a
target is added exactly; only the value shown to a person is rounded to minutes.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_SEARCH_DAYS = 4000


class CalendarError(ValueError):
    """An unusable calendar configuration; never silently repaired."""


@dataclass(frozen=True)
class WorkingCalendar:
    timezone: str
    working_weekdays: tuple[int, ...]
    opens_local: time
    closes_local: time
    holidays: frozenset[date]

    @property
    def zone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise CalendarError("Unknown calendar timezone") from exc

    def window(self, day: date) -> tuple[datetime, datetime] | None:
        """Absolute working window of a local day, or None when the day is closed."""
        if day.weekday() not in self.working_weekdays or day in self.holidays:
            return None
        zone = self.zone
        opens = datetime.combine(day, self.opens_local, tzinfo=zone)
        closes = datetime.combine(day, self.closes_local, tzinfo=zone)
        if closes <= opens:
            raise CalendarError("A working day must close after it opens")
        return opens, closes

    def is_working(self, instant: datetime) -> bool:
        local = instant.astimezone(self.zone)
        window = self.window(local.date())
        return bool(window and window[0] <= local < window[1])


def parse_clock(value: str) -> time:
    try:
        parsed = time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CalendarError("A local clock time is required") from exc
    if parsed.second or parsed.microsecond:
        raise CalendarError("A local clock time has minute precision")
    return parsed


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CalendarError("A calendar date is required") from exc


def calendar_from_policy(policy: object) -> WorkingCalendar:
    """Build the arithmetic calendar from a stored support policy."""
    working = tuple(sorted({int(day) for day in policy.working_weekdays}))  # type: ignore[attr-defined]
    if not working or any(day < 0 or day > 6 for day in working):
        raise CalendarError("At least one working weekday is required")
    holidays = frozenset(parse_day(str(day)) for day in policy.holidays)  # type: ignore[attr-defined]
    return WorkingCalendar(
        timezone=str(policy.timezone),  # type: ignore[attr-defined]
        working_weekdays=working,
        opens_local=parse_clock(str(policy.opens_local)),  # type: ignore[attr-defined]
        closes_local=parse_clock(str(policy.closes_local)),  # type: ignore[attr-defined]
        holidays=holidays,
    )


def business_seconds(calendar: WorkingCalendar, start: datetime, end: datetime) -> int:
    """Working seconds inside [start, end); closed time contributes nothing."""
    if start.tzinfo is None or end.tzinfo is None:
        raise CalendarError("Business clocks require aware timestamps")
    if end <= start:
        return 0
    zone = calendar.zone
    day = start.astimezone(zone).date()
    last = end.astimezone(zone).date()
    total = 0
    while day <= last:
        window = calendar.window(day)
        if window is not None:
            lower, upper = max(start, window[0]), min(end, window[1])
            if upper > lower:
                total += int((upper - lower).total_seconds())
        day += timedelta(days=1)
    return total


def add_business_seconds(calendar: WorkingCalendar, start: datetime, seconds: int) -> datetime:
    """The instant reached after `seconds` of working time, or the start itself."""
    if start.tzinfo is None:
        raise CalendarError("Business clocks require aware timestamps")
    if seconds <= 0:
        return start
    zone = calendar.zone
    remaining = seconds
    day = start.astimezone(zone).date()
    cursor = start
    for _ in range(MAX_SEARCH_DAYS):
        window = calendar.window(day)
        if window is not None:
            begin = max(cursor, window[0])
            if window[1] > begin:
                available = int((window[1] - begin).total_seconds())
                if available >= remaining:
                    return begin + timedelta(seconds=remaining)
                remaining -= available
        day += timedelta(days=1)
        cursor = datetime.combine(day, time(0, 0), tzinfo=zone)
    raise CalendarError("The requested working time is outside the supported horizon")


def business_minutes(calendar: WorkingCalendar, start: datetime, end: datetime) -> int:
    """Whole working minutes inside [start, end), rounded down for display."""
    return business_seconds(calendar, start, end) // 60


def add_business_minutes(calendar: WorkingCalendar, start: datetime, minutes: int) -> datetime:
    """The instant reached after `minutes` of working time."""
    return add_business_seconds(calendar, start, minutes * 60)
