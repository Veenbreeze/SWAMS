"""Read-optimized report aggregation — see docs/03-API-SPECIFICATION.md §11
and docs/05-DEVELOPMENT-ROADMAP.md Phase 6.

Every query here filters through the `Attendance`/`Employee` indexes laid
out in docs/02-DATABASE-ERD.md §4 (`(organization, attendance_date,
status)`, `(organization, employee, -attendance_date)`) — no report here
needs anything beyond those.

`ABSENT` is never a stored `Attendance.status` value (see
apps/attendance/domain/rules.py's module docstring) — it only exists in
report output, computed as "active employees minus those who have an
Attendance row for that date", and only on a working day per the org's
`AttendanceRule.working_days`.
"""

import datetime

from apps.attendance.domain.rules import is_working_day
from apps.attendance.models import Attendance, AttendanceRule, AttendanceStatus
from apps.employees.models import Employee, EmploymentStatus


def _attendance_rule(organization):
    rule, _ = AttendanceRule.objects.all_tenants().get_or_create(organization=organization)
    return rule


def _active_employee_count(organization, department=None, employees=None):
    qs = employees if employees is not None else Employee.objects.all()
    qs = qs.filter(employment_status=EmploymentStatus.ACTIVE)
    if department is not None:
        qs = qs.filter(department=department)
    return qs.count()


def daily_summary(*, organization, date, department=None, employees=None):
    """One day's present/late/early-departure/overtime/absent counts.

    `absent` is `None` (not zero) on a non-working day — there's no
    meaningful "who was absent" concept on a day nobody was scheduled to
    work, and collapsing that to 0 would read as "everyone showed up".

    `employees`, when given, restricts the count to that queryset (e.g. a
    Manager's `employees_visible_to()` scope) rather than the whole org.
    """
    rule = _attendance_rule(organization)
    total_employees = _active_employee_count(organization, department, employees)

    records = Attendance.objects.filter(attendance_date=date)
    if department is not None:
        records = records.filter(employee__department=department)
    if employees is not None:
        records = records.filter(employee__in=employees)

    present = records.exclude(check_in_time=None).count()
    late = records.filter(status=AttendanceStatus.LATE).count()
    early_departure = records.filter(status=AttendanceStatus.EARLY_DEPARTURE).count()
    overtime = records.filter(status=AttendanceStatus.OVERTIME).count()

    working_day = is_working_day(attendance_date=date, working_days=rule.working_days)
    absent = max(0, total_employees - present) if working_day else None

    return {
        "date": date,
        "is_working_day": working_day,
        "total_employees": total_employees,
        "present": present,
        "late": late,
        "early_departure": early_departure,
        "overtime": overtime,
        "absent": absent,
    }


def _date_range(start_date, end_date):
    days = (end_date - start_date).days
    return [start_date + datetime.timedelta(days=offset) for offset in range(days + 1)]


def range_summary(*, organization, start_date, end_date, department=None, employees=None):
    """A daily breakdown plus totals across an arbitrary date range —
    `weekly_summary`/`monthly_summary` are both this with a computed
    `start_date`/`end_date`.
    """
    days = [
        daily_summary(
            organization=organization, date=day, department=department, employees=employees
        )
        for day in _date_range(start_date, end_date)
    ]
    totals = {
        "present": sum(day["present"] for day in days),
        "late": sum(day["late"] for day in days),
        "early_departure": sum(day["early_departure"] for day in days),
        "overtime": sum(day["overtime"] for day in days),
        "absent": sum(day["absent"] or 0 for day in days if day["is_working_day"]),
    }
    return {"start_date": start_date, "end_date": end_date, "days": days, "totals": totals}


def weekly_summary(*, organization, start_date, department=None, employees=None):
    return range_summary(
        organization=organization,
        start_date=start_date,
        end_date=start_date + datetime.timedelta(days=6),
        department=department,
        employees=employees,
    )


def monthly_summary(*, organization, year, month, department=None, employees=None):
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year, 12, 31)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    return range_summary(
        organization=organization,
        start_date=start_date,
        end_date=end_date,
        department=department,
        employees=employees,
    )


def employee_report(*, employee, start_date=None, end_date=None):
    records = Attendance.objects.filter(employee=employee).order_by("-attendance_date")
    if start_date:
        records = records.filter(attendance_date__gte=start_date)
    if end_date:
        records = records.filter(attendance_date__lte=end_date)

    records = list(records)
    return {
        "employee_id": employee.id,
        "employee_name": employee.full_name,
        "records": records,
        "totals": {
            "days_present": len(records),
            "days_late": sum(1 for r in records if r.status == AttendanceStatus.LATE),
            "total_late_minutes": sum(r.late_minutes for r in records),
            "total_early_departure_minutes": sum(r.early_departure_minutes for r in records),
            "total_overtime_minutes": sum(r.overtime_minutes for r in records),
            "total_working_minutes": sum(r.working_minutes for r in records),
        },
    }


def department_report(*, department, start_date=None, end_date=None):
    today = datetime.date.today()
    summary = range_summary(
        organization=department.organization,
        start_date=start_date or today.replace(day=1),
        end_date=end_date or today,
        department=department,
    )
    summary["department_id"] = department.id
    summary["department_name"] = department.name
    return summary


def _status_report(*, status, start_date, end_date, department, employees):
    records = Attendance.objects.filter(status=status).order_by("-attendance_date")
    if start_date:
        records = records.filter(attendance_date__gte=start_date)
    if end_date:
        records = records.filter(attendance_date__lte=end_date)
    if department is not None:
        records = records.filter(employee__department=department)
    if employees is not None:
        records = records.filter(employee__in=employees)
    return list(records)


def late_report(*, organization, start_date=None, end_date=None, department=None, employees=None):
    return _status_report(
        status=AttendanceStatus.LATE,
        start_date=start_date,
        end_date=end_date,
        department=department,
        employees=employees,
    )


def overtime_report(
    *, organization, start_date=None, end_date=None, department=None, employees=None
):
    return _status_report(
        status=AttendanceStatus.OVERTIME,
        start_date=start_date,
        end_date=end_date,
        department=department,
        employees=employees,
    )
