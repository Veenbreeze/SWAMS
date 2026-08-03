import datetime

import pytest

from apps.attendance.models import Attendance, AttendanceRule, AttendanceStatus
from apps.employees.models import Employee, EmploymentStatus
from apps.reports.services import aggregations
from core.db import rls
from core.middleware.tenant_context import current_organization_id
from tests.factories import (
    AttendanceFactory,
    DepartmentFactory,
    EmployeeFactory,
    OrganizationFactory,
)

pytestmark = pytest.mark.django_db

MONDAY = datetime.date(2026, 8, 3)
SATURDAY = datetime.date(2026, 8, 8)


@pytest.fixture(autouse=True)
def _reset_tenant_context():
    # `aggregations.py` deliberately queries through the tenant-scoped
    # default manager (not `.all_tenants()`) — by design, it's meant to run
    # inside a request that already bound both `current_organization_id`
    # and the Postgres RLS session via `TenantAwareJWTAuthentication`.
    # These tests call it directly, so they bind both themselves via
    # `_bind(org)` below, matching what a real authenticated request would
    # have already done (the contextvar alone is enough on SQLite, since
    # RLS doesn't exist there — but not on Postgres).
    yield
    current_organization_id.set(None)
    rls.reset()


def _bind(organization):
    current_organization_id.set(str(organization.id))
    rls.bind(organization_id=organization.id)


def test_daily_summary_reconciles_against_raw_attendance_rows():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])

    present = EmployeeFactory(user__organization=org)
    late = EmployeeFactory(user__organization=org)
    early = EmployeeFactory(user__organization=org)
    overtime = EmployeeFactory(user__organization=org)
    absent = EmployeeFactory(user__organization=org)  # no Attendance row at all

    AttendanceFactory(employee=present, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)
    AttendanceFactory(
        employee=late, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=10
    )
    AttendanceFactory(
        employee=early,
        attendance_date=MONDAY,
        status=AttendanceStatus.EARLY_DEPARTURE,
        early_departure_minutes=15,
    )
    AttendanceFactory(
        employee=overtime,
        attendance_date=MONDAY,
        status=AttendanceStatus.OVERTIME,
        overtime_minutes=30,
    )
    assert absent  # exists as an active employee but has no attendance row

    summary = aggregations.daily_summary(organization=org, date=MONDAY)

    assert summary["total_employees"] == 5
    assert summary["is_working_day"] is True
    assert summary["present"] == 4  # anyone who checked in, regardless of status
    assert summary["late"] == 1
    assert summary["early_departure"] == 1
    assert summary["overtime"] == 1
    assert summary["absent"] == 1

    # Cross-check against the raw table directly, independent of the
    # aggregation's own internal logic.
    assert (
        summary["present"]
        == Attendance.objects.filter(organization=org, attendance_date=MONDAY)
        .exclude(check_in_time=None)
        .count()
    )


def test_daily_summary_absent_is_none_on_a_non_working_day():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])
    EmployeeFactory(user__organization=org)

    summary = aggregations.daily_summary(organization=org, date=SATURDAY)

    assert summary["is_working_day"] is False
    assert summary["absent"] is None


def test_terminated_employees_are_excluded_from_total_and_absent_count():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])
    EmployeeFactory(user__organization=org)  # active, no attendance -> counts as absent
    EmployeeFactory(user__organization=org, employment_status=EmploymentStatus.TERMINATED)

    summary = aggregations.daily_summary(organization=org, date=MONDAY)

    assert summary["total_employees"] == 1
    assert summary["absent"] == 1


def test_weekly_summary_totals_match_sum_of_daily_breakdowns():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])
    employee = EmployeeFactory(user__organization=org)
    for offset in range(3):
        AttendanceFactory(
            employee=employee,
            attendance_date=MONDAY + datetime.timedelta(days=offset),
            status=AttendanceStatus.PRESENT,
        )

    summary = aggregations.weekly_summary(organization=org, start_date=MONDAY)

    assert summary["totals"]["present"] == sum(day["present"] for day in summary["days"])
    assert summary["totals"]["present"] == 3
    assert len(summary["days"]) == 7


def test_monthly_summary_covers_the_full_calendar_month():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])

    summary = aggregations.monthly_summary(organization=org, year=2026, month=2)

    assert summary["start_date"] == datetime.date(2026, 2, 1)
    assert summary["end_date"] == datetime.date(2026, 2, 28)
    assert len(summary["days"]) == 28


def test_department_scoping_excludes_other_departments():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])

    dept_a = DepartmentFactory(organization=org)
    dept_b = DepartmentFactory(organization=org)
    employee_a = EmployeeFactory(user__organization=org, department=dept_a)
    employee_b = EmployeeFactory(user__organization=org, department=dept_b)
    AttendanceFactory(employee=employee_a, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)
    AttendanceFactory(employee=employee_b, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)

    summary = aggregations.daily_summary(organization=org, date=MONDAY, department=dept_a)

    assert summary["total_employees"] == 1
    assert summary["present"] == 1


def test_employee_scoping_restricts_total_employee_count():
    org = OrganizationFactory()
    _bind(org)
    AttendanceRule.objects.all_tenants().create(organization=org, working_days=[0, 1, 2, 3, 4])

    scoped_employee = EmployeeFactory(user__organization=org)
    EmployeeFactory(user__organization=org)  # not in scope

    summary = aggregations.daily_summary(
        organization=org,
        date=MONDAY,
        employees=Employee.objects.filter(pk=scoped_employee.pk),
    )

    assert summary["total_employees"] == 1


def test_employee_report_totals_reconcile_against_records():
    employee = EmployeeFactory()
    _bind(employee.organization)
    AttendanceFactory(
        employee=employee,
        attendance_date=MONDAY,
        status=AttendanceStatus.LATE,
        late_minutes=10,
        working_minutes=470,
    )
    AttendanceFactory(
        employee=employee,
        attendance_date=MONDAY + datetime.timedelta(days=1),
        status=AttendanceStatus.OVERTIME,
        overtime_minutes=45,
        working_minutes=525,
    )

    report = aggregations.employee_report(employee=employee)

    assert report["totals"]["days_present"] == 2
    assert report["totals"]["days_late"] == 1
    assert report["totals"]["total_late_minutes"] == 10
    assert report["totals"]["total_overtime_minutes"] == 45
    assert report["totals"]["total_working_minutes"] == 470 + 525
    assert len(report["records"]) == 2


def test_late_report_returns_only_late_records_within_range():
    employee = EmployeeFactory()
    _bind(employee.organization)
    other_employee = EmployeeFactory(user__organization=employee.organization)
    in_range = AttendanceFactory(
        employee=employee, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    AttendanceFactory(
        employee=employee,
        attendance_date=MONDAY - datetime.timedelta(days=10),
        status=AttendanceStatus.LATE,
        late_minutes=5,
    )
    AttendanceFactory(
        employee=other_employee, attendance_date=MONDAY, status=AttendanceStatus.PRESENT
    )

    records = aggregations.late_report(
        organization=employee.organization,
        start_date=MONDAY - datetime.timedelta(days=1),
        end_date=MONDAY + datetime.timedelta(days=1),
    )

    assert [r.id for r in records] == [in_range.id]
