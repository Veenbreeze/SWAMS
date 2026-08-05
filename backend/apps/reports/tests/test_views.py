import datetime

import pytest
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRule, AttendanceStatus
from apps.authentication.models import Role
from tests.factories import (
    AttendanceFactory,
    DepartmentFactory,
    EmployeeFactory,
    ManagerAssignmentFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"
MONDAY = datetime.date(2026, 8, 3)


def _client_as(user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login",
        {
            "organization_code": user.organization.code if user.organization else "",
            "identifier": user.email,
            "password": PASSWORD,
        },
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access_token']}")
    return client


def _org_admin():
    return UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)


def test_daily_report_requires_manager_or_above():
    employee = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    client = _client_as(employee)

    response = client.get("/api/v1/reports/daily", {"date": str(MONDAY)})

    assert response.status_code == 403


def test_daily_report_returns_aggregated_counts():
    admin = _org_admin()
    AttendanceRule.objects.all_tenants().create(
        organization=admin.organization, working_days=[0, 1, 2, 3, 4]
    )
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(employee=employee, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)
    client = _client_as(admin)

    response = client.get("/api/v1/reports/daily", {"date": str(MONDAY)})

    assert response.status_code == 200
    body = response.json()
    assert body["present"] == 1
    assert body["date"] == str(MONDAY)


def test_daily_report_defaults_to_today_and_validates_date_format():
    admin = _org_admin()
    client = _client_as(admin)

    bad = client.get("/api/v1/reports/daily", {"date": "not-a-date"})
    assert bad.status_code == 400

    default = client.get("/api/v1/reports/daily")
    assert default.status_code == 200
    assert default.json()["date"] == str(datetime.date.today())


def test_weekly_report_requires_start_param():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.get("/api/v1/reports/weekly")

    assert response.status_code == 400


def test_weekly_report_returns_aggregated_counts():
    admin = _org_admin()
    AttendanceRule.objects.all_tenants().create(
        organization=admin.organization, working_days=[0, 1, 2, 3, 4]
    )
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(employee=employee, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)
    client = _client_as(admin)

    response = client.get("/api/v1/reports/weekly", {"start": str(MONDAY)})

    assert response.status_code == 200
    body = response.json()
    assert len(body["days"]) == 7
    assert body["totals"]["present"] == 1


def test_monthly_report_requires_month_param():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.get("/api/v1/reports/monthly")

    assert response.status_code == 400

    ok = client.get("/api/v1/reports/monthly", {"month": "2026-08"})
    assert ok.status_code == 200
    assert len(ok.json()["days"]) == 31


def test_monthly_report_rejects_malformed_month():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.get("/api/v1/reports/monthly", {"month": "not-a-month"})

    assert response.status_code == 400


def test_employee_can_view_their_own_report_but_not_anothers():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    other_employee = EmployeeFactory(user__organization=user.organization)
    client = _client_as(user)

    own = client.get(f"/api/v1/reports/employee/{employee.id}")
    assert own.status_code == 200

    other = client.get(f"/api/v1/reports/employee/{other_employee.id}")
    assert other.status_code == 403


def test_manager_can_view_report_for_scoped_employee_only():
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    manager_employee = EmployeeFactory(user=manager_user)
    in_scope = EmployeeFactory(user__organization=manager_user.organization)
    out_of_scope = EmployeeFactory(user__organization=manager_user.organization)
    ManagerAssignmentFactory(manager=manager_employee, employee=in_scope)
    client = _client_as(manager_user)

    allowed = client.get(f"/api/v1/reports/employee/{in_scope.id}")
    assert allowed.status_code == 200

    denied = client.get(f"/api/v1/reports/employee/{out_of_scope.id}")
    assert denied.status_code == 403


def test_department_report_requires_manager_assignment():
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    manager_employee = EmployeeFactory(user=manager_user)
    department = DepartmentFactory(organization=manager_user.organization)
    client = _client_as(manager_user)

    denied = client.get(f"/api/v1/reports/department/{department.id}")
    assert denied.status_code == 403

    ManagerAssignmentFactory(manager=manager_employee, department=department)
    allowed = client.get(f"/api/v1/reports/department/{department.id}")
    assert allowed.status_code == 200
    assert allowed.json()["department_id"] == str(department.id)


def test_late_and_overtime_reports_return_matching_records():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(
        employee=employee, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    AttendanceFactory(
        employee=employee,
        attendance_date=MONDAY + datetime.timedelta(days=1),
        status=AttendanceStatus.OVERTIME,
        overtime_minutes=20,
    )
    client = _client_as(admin)

    late = client.get("/api/v1/reports/late")
    assert late.status_code == 200
    assert len(late.json()) == 1
    assert late.json()[0]["status"] == "LATE"

    overtime = client.get("/api/v1/reports/overtime")
    assert overtime.status_code == 200
    assert len(overtime.json()) == 1
    assert overtime.json()[0]["status"] == "OVERTIME"


def test_manager_scoping_applies_to_late_report():
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    manager_employee = EmployeeFactory(user=manager_user)
    in_scope = EmployeeFactory(user__organization=manager_user.organization)
    out_of_scope = EmployeeFactory(user__organization=manager_user.organization)
    ManagerAssignmentFactory(manager=manager_employee, employee=in_scope)
    AttendanceFactory(
        employee=in_scope, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    AttendanceFactory(
        employee=out_of_scope, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    client = _client_as(manager_user)

    response = client.get("/api/v1/reports/late")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["employee_id"] == str(in_scope.id)
