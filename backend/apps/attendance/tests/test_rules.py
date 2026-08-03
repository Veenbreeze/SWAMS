import datetime

import pytest

from apps.attendance.domain import rules

TZ = datetime.timezone.utc
DAY = datetime.date(2026, 8, 2)


def _dt(hour, minute, date=DAY):
    return datetime.datetime(date.year, date.month, date.day, hour, minute, tzinfo=TZ)


def test_literal_brief_example_08_10_checkin_vs_08_00_shift_is_late_by_10():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(8, 10),
        attendance_date=DAY,
        shift_start_time=datetime.time(8, 0),
        late_threshold_minutes=0,
    )
    assert status == rules.LATE
    assert late_minutes == 10


def test_check_in_exactly_on_time_is_present():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(8, 0),
        attendance_date=DAY,
        shift_start_time=datetime.time(8, 0),
        late_threshold_minutes=0,
    )
    assert status == rules.PRESENT
    assert late_minutes == 0


def test_check_in_early_is_present():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(7, 45),
        attendance_date=DAY,
        shift_start_time=datetime.time(8, 0),
        late_threshold_minutes=0,
    )
    assert status == rules.PRESENT
    assert late_minutes == 0


def test_grace_period_absorbs_small_delays():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(8, 5),
        attendance_date=DAY,
        shift_start_time=datetime.time(8, 0),
        late_threshold_minutes=5,
    )
    assert status == rules.PRESENT
    assert late_minutes == 0


def test_grace_period_boundary_one_minute_over_is_late_by_full_delta():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(8, 6),
        attendance_date=DAY,
        shift_start_time=datetime.time(8, 0),
        late_threshold_minutes=5,
    )
    assert status == rules.LATE
    assert late_minutes == 6  # full delta, not delta-minus-grace


def test_no_assigned_shift_is_always_present():
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=_dt(23, 0),
        attendance_date=DAY,
        shift_start_time=None,
        late_threshold_minutes=0,
    )
    assert status == rules.PRESENT
    assert late_minutes == 0


def test_early_departure_uses_full_delta_past_grace():
    minutes = rules.minutes_early_departure(
        check_out_time=_dt(16, 40),
        attendance_date=DAY,
        shift_end_time=datetime.time(17, 0),
        shift_crosses_midnight=False,
        early_departure_threshold_minutes=5,
    )
    assert minutes == 20


def test_leaving_within_grace_period_is_not_early_departure():
    minutes = rules.minutes_early_departure(
        check_out_time=_dt(16, 57),
        attendance_date=DAY,
        shift_end_time=datetime.time(17, 0),
        shift_crosses_midnight=False,
        early_departure_threshold_minutes=5,
    )
    assert minutes == 0


def test_overtime_uses_full_delta_past_grace():
    minutes = rules.minutes_overtime(
        check_out_time=_dt(18, 30),
        attendance_date=DAY,
        shift_end_time=datetime.time(17, 0),
        shift_crosses_midnight=False,
        overtime_threshold_minutes=15,
    )
    assert minutes == 90


def test_overnight_shift_end_lands_on_next_calendar_day():
    # Night shift 22:00 -> 06:00 (crosses midnight); attendance_date is the
    # day the shift *started*, so the expected end is 06:00 the next day.
    minutes = rules.minutes_overtime(
        check_out_time=datetime.datetime(2026, 8, 3, 6, 30, tzinfo=TZ),
        attendance_date=DAY,
        shift_end_time=datetime.time(6, 0),
        shift_crosses_midnight=True,
        overtime_threshold_minutes=0,
    )
    assert minutes == 30


def test_working_minutes_computes_duration():
    assert rules.working_minutes(check_in_time=_dt(8, 0), check_out_time=_dt(17, 0)) == 540


@pytest.mark.parametrize(
    "late,early,overtime,expected",
    [
        (10, 0, 0, rules.LATE),
        (0, 10, 0, rules.EARLY_DEPARTURE),
        (0, 0, 10, rules.OVERTIME),
        (0, 0, 0, rules.PRESENT),
        (10, 10, 0, rules.LATE),  # late wins over early departure
        (10, 0, 10, rules.LATE),  # late wins over overtime
        (0, 10, 10, rules.EARLY_DEPARTURE),  # early departure wins over overtime
    ],
)
def test_final_status_priority(late, early, overtime, expected):
    assert (
        rules.calculate_final_status(
            late_minutes=late, early_departure_minutes=early, overtime_minutes=overtime
        )
        == expected
    )


def test_is_working_day():
    monday = datetime.date(2026, 8, 3)
    saturday = datetime.date(2026, 8, 8)
    assert rules.is_working_day(attendance_date=monday, working_days=[0, 1, 2, 3, 4]) is True
    assert rules.is_working_day(attendance_date=saturday, working_days=[0, 1, 2, 3, 4]) is False
