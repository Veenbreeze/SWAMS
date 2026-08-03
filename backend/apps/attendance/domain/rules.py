"""Attendance status calculation — pure domain logic, no Django/ORM
imports (mirrors apps/locations/domain/geofence.py's rationale). See
docs/01-SYSTEM-ARCHITECTURE.md §7.

Threshold semantics (confirmed against the brief's own worked example —
shift start 08:00, check-in 08:10 -> "Late by 10"): `late_threshold_minutes`
is a *grace period*, not a subtracted allowance. A check-in inside the
grace period is on-time; once it exceeds the grace period, `late_minutes`
is the full raw delta from the scheduled time, not the delta minus the
grace period. `early_departure_threshold_minutes`/`overtime_threshold_minutes`
follow the identical shape on the check-out side.

`ABSENT` is deliberately never produced here: it can only be known in
hindsight (a working day passed with no check-in at all), which requires
inspecting the *absence* of an Attendance row — a job for Phase 6's
reporting aggregation, not this check-in/check-out pipeline, which only
ever runs when there *is* a check-in/check-out event.
"""

import datetime

PRESENT = "PRESENT"
LATE = "LATE"
EARLY_DEPARTURE = "EARLY_DEPARTURE"
OVERTIME = "OVERTIME"


def is_working_day(*, attendance_date, working_days):
    return attendance_date.weekday() in working_days


def _expected_start_datetime(attendance_date, shift_start_time, tzinfo):
    return datetime.datetime.combine(attendance_date, shift_start_time, tzinfo=tzinfo)


def _expected_end_datetime(attendance_date, shift_end_time, shift_crosses_midnight, tzinfo):
    end_date = attendance_date + datetime.timedelta(days=1 if shift_crosses_midnight else 0)
    return datetime.datetime.combine(end_date, shift_end_time, tzinfo=tzinfo)


def minutes_late(*, check_in_time, attendance_date, shift_start_time, late_threshold_minutes):
    """0 if there's no assigned shift to be late against, or if the
    check-in falls inside the grace period (including arriving early).
    """
    if shift_start_time is None:
        return 0

    expected_start = _expected_start_datetime(
        attendance_date, shift_start_time, check_in_time.tzinfo
    )
    delta_minutes = int((check_in_time - expected_start).total_seconds() // 60)
    return delta_minutes if delta_minutes > late_threshold_minutes else 0


def minutes_early_departure(
    *,
    check_out_time,
    attendance_date,
    shift_end_time,
    shift_crosses_midnight,
    early_departure_threshold_minutes,
):
    if shift_end_time is None:
        return 0

    expected_end = _expected_end_datetime(
        attendance_date, shift_end_time, shift_crosses_midnight, check_out_time.tzinfo
    )
    delta_minutes = int((expected_end - check_out_time).total_seconds() // 60)
    return delta_minutes if delta_minutes > early_departure_threshold_minutes else 0


def minutes_overtime(
    *,
    check_out_time,
    attendance_date,
    shift_end_time,
    shift_crosses_midnight,
    overtime_threshold_minutes,
):
    if shift_end_time is None:
        return 0

    expected_end = _expected_end_datetime(
        attendance_date, shift_end_time, shift_crosses_midnight, check_out_time.tzinfo
    )
    delta_minutes = int((check_out_time - expected_end).total_seconds() // 60)
    return delta_minutes if delta_minutes > overtime_threshold_minutes else 0


def working_minutes(*, check_in_time, check_out_time):
    return max(0, int((check_out_time - check_in_time).total_seconds() // 60))


def calculate_check_in_status(
    *, check_in_time, attendance_date, shift_start_time, late_threshold_minutes
):
    """The status known immediately at check-in, before any check-out
    exists — can only ever be PRESENT or LATE.
    """
    late_minutes = minutes_late(
        check_in_time=check_in_time,
        attendance_date=attendance_date,
        shift_start_time=shift_start_time,
        late_threshold_minutes=late_threshold_minutes,
    )
    return (LATE if late_minutes else PRESENT), late_minutes


def calculate_final_status(*, late_minutes, early_departure_minutes, overtime_minutes):
    """The headline `status` once check-out numbers are also known.

    Priority: LATE > EARLY_DEPARTURE > OVERTIME > PRESENT — arriving late
    is the more actionable signal for an Org Admin than how the day ended,
    so it wins if both occurred on the same day.
    """
    if late_minutes > 0:
        return LATE
    if early_departure_minutes > 0:
        return EARLY_DEPARTURE
    if overtime_minutes > 0:
        return OVERTIME
    return PRESENT
