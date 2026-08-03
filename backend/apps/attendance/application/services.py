"""Check-in/check-out orchestration — see docs/01-SYSTEM-ARCHITECTURE.md §7
and docs/05-DEVELOPMENT-ROADMAP.md Phase 5.

Pipeline (each step raises a specific `domain.exceptions` error, mapped by
the interfaces layer onto docs/03-API-SPECIFICATION.md's error codes):
auth (view permission) -> org (tenant context) -> branch -> distance ->
accuracy -> mock-location -> schedule -> persist.

The server's own clock (`timezone.now()`), never the client-supplied
`client_timestamp`, is what gets persisted as `check_in_time`/
`check_out_time` — docs/01-SYSTEM-ARCHITECTURE.md §6.2's "the backend is
the only trust boundary" applies just as much to a device's clock as to
its GPS reading. `client_timestamp` is accepted and bounds-checked (not
absurdly far from server time) purely as a client-side sanity signal, not
as an input to any calculation.
"""

from django.utils import timezone

from apps.attendance.domain import exceptions as domain_errors
from apps.attendance.domain import rules
from apps.attendance.models import Attendance, AttendanceRule
from apps.locations.domain.geofence import haversine_distance_meters
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationDispatcher
from apps.security.models import SecurityEventType
from apps.security.services import SecurityEventLogger

# Generous ceiling above any plausible ground-vehicle speed in an urban
# Tanzanian context — chosen to flag genuinely impossible jumps (e.g. two
# check-ins in different cities minutes apart) without false-positiving on
# ordinary traffic/commute variance. Flag-only, never blocking — see
# docs/01-SYSTEM-ARCHITECTURE.md §6.6.
_IMPLAUSIBLE_SPEED_KMH = 300


def _validate_location(*, employee, branch, gps, request=None):
    if branch is None:
        raise domain_errors.NoBranchAssignedError()

    distance = haversine_distance_meters(
        gps.latitude, gps.longitude, float(branch.latitude), float(branch.longitude)
    )
    if distance > branch.radius_meters:
        raise domain_errors.OutsideGeofenceError()

    if gps.accuracy > branch.gps_accuracy_limit_meters:
        raise domain_errors.PoorGpsAccuracyError()

    if gps.is_mock_location:
        SecurityEventLogger.record(
            event_type=SecurityEventType.MOCK_LOCATION_DETECTED,
            user=employee.user,
            organization=employee.organization,
            description="Mock/simulated location reported during attendance check-in/out.",
            metadata={"distance_meters": round(distance, 1), "branch_id": str(branch.id)},
            request=request,
        )
        raise domain_errors.MockLocationDetectedError()

    return distance


def _detect_implausible_travel(*, employee, current_time, gps, request=None):
    """Non-blocking: compares against the employee's last known checked
    location (their most recent check-in, or check-out if later) and logs
    a SecurityEvent for admin review if the implied speed is impossible —
    never denies the request itself.
    """
    last = (
        Attendance.objects.all_tenants()
        .filter(employee=employee)
        .exclude(check_in_time=None)
        .order_by("-check_in_time")
        .first()
    )
    if last is None:
        return

    if last.check_out_time and last.check_out_latitude is not None:
        last_time = last.check_out_time
        last_lat, last_lng = last.check_out_latitude, last.check_out_longitude
    elif last.check_in_latitude is not None:
        last_time = last.check_in_time
        last_lat, last_lng = last.check_in_latitude, last.check_in_longitude
    else:
        return

    elapsed_hours = (current_time - last_time).total_seconds() / 3600
    if elapsed_hours <= 0:
        return

    distance_meters = haversine_distance_meters(
        gps.latitude, gps.longitude, float(last_lat), float(last_lng)
    )
    distance_km = distance_meters / 1000
    implied_speed_kmh = distance_km / elapsed_hours

    if implied_speed_kmh > _IMPLAUSIBLE_SPEED_KMH:
        description = (
            f"Implied travel speed ~{implied_speed_kmh:.0f} km/h since last known location."
        )
        SecurityEventLogger.record(
            event_type=SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED,
            user=employee.user,
            organization=employee.organization,
            description=description,
            metadata={
                "distance_km": round(distance_km, 2),
                "elapsed_hours": round(elapsed_hours, 4),
            },
            request=request,
        )


def _get_attendance_rule(organization):
    rule, _ = AttendanceRule.objects.all_tenants().get_or_create(organization=organization)
    return rule


def check_in(*, employee, gps, device_id="", request=None):
    now = timezone.now()
    attendance_date = now.date()

    existing = (
        Attendance.objects.all_tenants()
        .filter(employee=employee, attendance_date=attendance_date)
        .first()
    )
    if existing and existing.check_in_time:
        raise domain_errors.AlreadyCheckedInError()

    branch = employee.branch
    _validate_location(employee=employee, branch=branch, gps=gps, request=request)
    _detect_implausible_travel(employee=employee, current_time=now, gps=gps, request=request)

    rule = _get_attendance_rule(employee.organization)
    shift = employee.shift
    status, late_minutes = rules.calculate_check_in_status(
        check_in_time=now,
        attendance_date=attendance_date,
        shift_start_time=shift.start_time if shift else None,
        late_threshold_minutes=rule.late_threshold_minutes,
    )

    attendance = existing or Attendance(
        organization=employee.organization, employee=employee, attendance_date=attendance_date
    )
    attendance.branch = branch
    attendance.check_in_time = now
    attendance.check_in_latitude = gps.latitude
    attendance.check_in_longitude = gps.longitude
    attendance.check_in_accuracy = gps.accuracy
    attendance.check_in_device_id = device_id
    attendance.check_in_is_mock = gps.is_mock_location
    attendance.status = status
    attendance.late_minutes = late_minutes
    attendance.save()

    NotificationDispatcher.notify(
        user=employee.user,
        category=NotificationCategory.ATTENDANCE,
        title="Checked in",
        message=f"You checked in at {timezone.localtime(now):%H:%M}.",
    )

    return attendance


def check_out(*, employee, gps, device_id="", request=None):
    now = timezone.now()
    attendance_date = now.date()

    attendance = (
        Attendance.objects.all_tenants()
        .filter(employee=employee, attendance_date=attendance_date)
        .first()
    )
    if attendance is None or not attendance.check_in_time:
        raise domain_errors.NotCheckedInYetError()
    if attendance.check_out_time:
        raise domain_errors.AlreadyCheckedOutError()

    # Validated against the branch captured at check-in time, not the
    # employee's current assignment — an Org Admin reassigning branches
    # mid-day shouldn't retroactively change where this checkout must
    # happen from.
    _validate_location(employee=employee, branch=attendance.branch, gps=gps, request=request)
    _detect_implausible_travel(employee=employee, current_time=now, gps=gps, request=request)

    rule = _get_attendance_rule(employee.organization)
    shift = employee.shift
    early_departure_minutes = rules.minutes_early_departure(
        check_out_time=now,
        attendance_date=attendance_date,
        shift_end_time=shift.end_time if shift else None,
        shift_crosses_midnight=shift.crosses_midnight if shift else False,
        early_departure_threshold_minutes=rule.early_departure_threshold_minutes,
    )
    overtime_minutes = rules.minutes_overtime(
        check_out_time=now,
        attendance_date=attendance_date,
        shift_end_time=shift.end_time if shift else None,
        shift_crosses_midnight=shift.crosses_midnight if shift else False,
        overtime_threshold_minutes=rule.overtime_threshold_minutes,
    )
    status = rules.calculate_final_status(
        late_minutes=attendance.late_minutes,
        early_departure_minutes=early_departure_minutes,
        overtime_minutes=overtime_minutes,
    )

    attendance.check_out_time = now
    attendance.check_out_latitude = gps.latitude
    attendance.check_out_longitude = gps.longitude
    attendance.check_out_accuracy = gps.accuracy
    attendance.check_out_device_id = device_id
    attendance.check_out_is_mock = gps.is_mock_location
    attendance.early_departure_minutes = early_departure_minutes
    attendance.overtime_minutes = overtime_minutes
    attendance.working_minutes = rules.working_minutes(
        check_in_time=attendance.check_in_time, check_out_time=now
    )
    attendance.status = status
    attendance.save()

    NotificationDispatcher.notify(
        user=employee.user,
        category=NotificationCategory.ATTENDANCE,
        title="Checked out",
        message=f"You checked out at {timezone.localtime(now):%H:%M}.",
    )

    return attendance
