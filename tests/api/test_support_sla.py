"""Business-hours arithmetic: weekends, holidays, working windows and DST."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from support.calendar import (
    CalendarError,
    WorkingCalendar,
    add_business_minutes,
    business_minutes,
    calendar_from_policy,
)

HEBRON = ZoneInfo("Asia/Hebron")
# Sunday=6, Monday=0 .. Thursday=3 (Friday=4 and Saturday=5 are closed).
WEEKDAYS = (6, 0, 1, 2, 3)


def calendar(holidays=()):
    return WorkingCalendar(
        timezone="Asia/Hebron",
        working_weekdays=WEEKDAYS,
        opens_local=time(9, 0),
        closes_local=time(17, 0),
        holidays=frozenset(holidays),
    )


def local(*args):
    return datetime(*args, tzinfo=HEBRON)


def test_working_day_measures_only_the_open_window():
    value = business_minutes(calendar(), local(2026, 10, 20, 9, 0), local(2026, 10, 20, 17, 0))
    assert value == 480


def test_night_and_early_morning_contribute_nothing():
    value = business_minutes(calendar(), local(2026, 10, 20, 17, 0), local(2026, 10, 21, 9, 0))
    assert value == 0


def test_friday_and_saturday_are_closed():
    value = business_minutes(calendar(), local(2026, 10, 23, 9, 0), local(2026, 10, 25, 9, 0))
    assert value == 0


def test_a_request_after_closing_rolls_to_the_next_working_morning():
    due = add_business_minutes(calendar(), local(2026, 10, 22, 16, 0), 240)
    # Thursday closes at 17:00, Friday and Saturday are closed, Sunday opens at 09:00.
    assert due == local(2026, 10, 25, 12, 0)


def test_a_holiday_inside_the_interval_is_skipped():
    value = business_minutes(
        calendar(holidays=[date(2026, 10, 21)]),
        local(2026, 10, 19, 9, 0),
        local(2026, 10, 22, 9, 0),
    )
    # Monday and Tuesday count; Wednesday is a public holiday; Thursday is not reached.
    assert value == 960


def test_several_working_days_accumulate():
    value = business_minutes(calendar(), local(2026, 10, 19, 9, 0), local(2026, 10, 22, 9, 0))
    # Sunday, Monday and Tuesday: three full working days.
    assert value == 1440


def test_spring_forward_keeps_the_local_window_and_shifts_the_utc_instant():
    # Thursday 2026-03-26 is a working day before the Saturday night transition.
    due = add_business_minutes(calendar(), local(2026, 3, 26, 16, 0), 240)
    assert due.astimezone(HEBRON).date() == date(2026, 3, 29)
    assert due.astimezone(HEBRON).hour == 12
    # Sunday 2026-03-29 already runs on UTC+03:00.
    assert due.utcoffset() == timedelta(hours=3)
    assert due.astimezone(ZoneInfo("UTC")).hour == 9


def test_autumn_back_keeps_the_local_window_and_shifts_the_utc_instant():
    # Thursday 2026-10-22 is a working day before the Saturday night transition.
    due = add_business_minutes(calendar(), local(2026, 10, 22, 16, 0), 240)
    assert due.astimezone(HEBRON).date() == date(2026, 10, 25)
    assert due.astimezone(HEBRON).hour == 12
    # Sunday 2026-10-25 already runs on UTC+02:00.
    assert due.utcoffset() == timedelta(hours=2)
    assert due.astimezone(ZoneInfo("UTC")).hour == 10


def test_the_same_local_deadline_maps_to_different_instants_across_transitions():
    spring = add_business_minutes(calendar(), local(2026, 3, 26, 16, 0), 240)
    autumn = add_business_minutes(calendar(), local(2026, 10, 22, 16, 0), 240)
    assert spring.astimezone(HEBRON).hour == autumn.astimezone(HEBRON).hour == 12
    assert spring != autumn
    assert spring.utcoffset() != autumn.utcoffset()


def test_the_working_day_length_is_stable_across_a_transition():
    spring = business_minutes(calendar(), local(2026, 3, 29, 0, 0), local(2026, 3, 30, 0, 0))
    autumn = business_minutes(calendar(), local(2026, 10, 25, 0, 0), local(2026, 10, 26, 0, 0))
    assert spring == autumn == 480


def test_elapsed_and_added_business_minutes_are_inverses():
    start = local(2026, 10, 19, 11, 15)
    for minutes in (1, 60, 240, 1440, 2880):
        due = add_business_minutes(calendar(), start, minutes)
        assert business_minutes(calendar(), start, due) == minutes


def test_adding_zero_minutes_returns_the_same_instant():
    start = local(2026, 10, 19, 11, 15)
    assert add_business_minutes(calendar(), start, 0) == start


def test_naive_timestamps_are_refused():
    with pytest.raises(CalendarError):
        business_minutes(calendar(), datetime(2026, 10, 19, 9, 0), local(2026, 10, 19, 17, 0))


def test_a_closed_calendar_is_refused():
    empty = WorkingCalendar(
        timezone="Asia/Hebron",
        working_weekdays=(),
        opens_local=time(9, 0),
        closes_local=time(17, 0),
        holidays=frozenset(),
    )
    with pytest.raises(CalendarError):
        add_business_minutes(empty, local(2026, 10, 19, 9, 0), 60)


def test_a_policy_projection_builds_the_same_calendar():
    class Policy:
        timezone = "Asia/Hebron"
        working_weekdays = [6, 0, 1, 2, 3]
        opens_local = "09:00"
        closes_local = "17:00"
        holidays = ["2026-10-21"]

    built = calendar_from_policy(Policy())
    assert built.working_weekdays == tuple(sorted(WEEKDAYS))
    assert business_minutes(built, local(2026, 10, 19, 9, 0), local(2026, 10, 22, 9, 0)) == 960
