"""RLS-as-last-resort regression test — docs/05-DEVELOPMENT-ROADMAP.md Phase 3
acceptance criterion: raw SQL as a different `app.current_org_id` cannot read
another org's rows even bypassing the ORM manager.

Skipped outside Postgres (policies don't exist on SQLite) and when connected
as a Postgres superuser: superusers bypass RLS unconditionally, even with
`FORCE ROW LEVEL SECURITY`, so a superuser connection can't actually exercise
these policies — it would pass by accident, not by verifying anything.
"""

import pytest
from django.db import connection

from apps.attendance.models import Attendance, AttendanceRule, Shift
from apps.audit_logs.models import AuditLog
from apps.employees.models import Department, ManagerAssignment
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.locations.models import Branch
from apps.notifications.models import Notification, NotificationCategory
from apps.reports.models import ExportFormat, ReportExportJob
from apps.security.models import SecurityEvent, SecurityEventType
from apps.subscriptions.models import Subscription, SubscriptionPlan
from core.db import rls
from tests.factories import EmployeeFactory, OrganizationFactory, UserAccountFactory


def _connected_as_superuser():
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        return cursor.fetchone()[0]


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="RLS policies only exist on Postgres; local/CI default to SQLite.",
    ),
]


def _raw_org_ids(table):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT organization_id FROM {table}")
        return {row[0] for row in cursor.fetchall()}


@pytest.fixture(autouse=True)
def _skip_if_superuser():
    if connection.vendor == "postgresql" and _connected_as_superuser():
        pytest.skip("Connected as a Postgres superuser — RLS is bypassed unconditionally.")


@pytest.fixture(autouse=True)
def _reset_rls_after():
    yield
    rls.reset()


def test_audit_log_rls_blocks_cross_tenant_raw_sql_read():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()

    AuditLog.objects.all_tenants().create(organization=org_a, action="a.action")
    AuditLog.objects.all_tenants().create(organization=org_b, action="b.action")
    AuditLog.objects.all_tenants().create(organization=None, action="platform.action")

    rls.bind(organization_id=org_a.id)
    assert _raw_org_ids("audit_logs_auditlog") == {org_a.id}

    rls.bind(organization_id=org_b.id)
    assert _raw_org_ids("audit_logs_auditlog") == {org_b.id}

    rls.bind(platform_wide=True)
    assert _raw_org_ids("audit_logs_auditlog") == {org_a.id, org_b.id, None}

    rls.reset()
    assert _raw_org_ids("audit_logs_auditlog") == set()


def test_subscription_rls_blocks_cross_tenant_raw_sql_read():
    plan = SubscriptionPlan.objects.create(
        code="BASIC-RLS-TEST",
        name="Basic",
        max_employees=10,
        max_branches=1,
        monthly_price="10.00",
    )
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()

    Subscription.objects.all_tenants().create(
        organization=org_a, plan=plan, start_date="2026-01-01", expiry_date="2026-12-31"
    )
    Subscription.objects.all_tenants().create(
        organization=org_b, plan=plan, start_date="2026-01-01", expiry_date="2026-12-31"
    )

    rls.bind(organization_id=org_a.id)
    assert _raw_org_ids("subscriptions_subscription") == {org_a.id}

    rls.bind(platform_wide=True)
    assert _raw_org_ids("subscriptions_subscription") == {org_a.id, org_b.id}

    rls.reset()
    assert _raw_org_ids("subscriptions_subscription") == set()


def _assert_standard_tenant_rls(table, org_a, org_b):
    """Shared assertions for the plain "every row has a non-null
    organization_id" shape (locations/attendance/employees' Phase 4
    tables) — the audit_logs case above is the only table with a
    legitimate NULL-organization row, so it alone has the three-way
    (org-a / org-b / platform) assertion instead of this two-way one.
    """
    rls.bind(organization_id=org_a.id)
    assert _raw_org_ids(table) == {org_a.id}

    rls.bind(organization_id=org_b.id)
    assert _raw_org_ids(table) == {org_b.id}

    rls.bind(platform_wide=True)
    assert _raw_org_ids(table) == {org_a.id, org_b.id}

    rls.reset()
    assert _raw_org_ids(table) == set()


def test_branch_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    Branch.objects.all_tenants().create(
        organization=org_a, name="A", latitude="0", longitude="0"
    )
    Branch.objects.all_tenants().create(
        organization=org_b, name="B", latitude="0", longitude="0"
    )
    _assert_standard_tenant_rls("locations_branch", org_a, org_b)


def test_shift_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    Shift.objects.all_tenants().create(
        organization=org_a, name="Day", start_time="08:00", end_time="17:00"
    )
    Shift.objects.all_tenants().create(
        organization=org_b, name="Day", start_time="08:00", end_time="17:00"
    )
    _assert_standard_tenant_rls("attendance_shift", org_a, org_b)


def test_attendance_rule_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    AttendanceRule.objects.all_tenants().create(organization=org_a)
    AttendanceRule.objects.all_tenants().create(organization=org_b)
    _assert_standard_tenant_rls("attendance_attendancerule", org_a, org_b)


def test_department_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    Department.objects.all_tenants().create(organization=org_a, name="Eng")
    Department.objects.all_tenants().create(organization=org_b, name="Eng")
    _assert_standard_tenant_rls("employees_department", org_a, org_b)


def test_employee_rls_blocks_cross_tenant_raw_sql_read():
    employee_a = EmployeeFactory()
    employee_b = EmployeeFactory()
    _assert_standard_tenant_rls(
        "employees_employee", employee_a.organization, employee_b.organization
    )


def test_manager_assignment_rls_blocks_cross_tenant_raw_sql_read():
    manager_a = EmployeeFactory()
    manager_b = EmployeeFactory()
    ManagerAssignment.objects.all_tenants().create(
        organization=manager_a.organization, manager=manager_a, employee=manager_a
    )
    ManagerAssignment.objects.all_tenants().create(
        organization=manager_b.organization, manager=manager_b, employee=manager_b
    )
    _assert_standard_tenant_rls(
        "employees_managerassignment", manager_a.organization, manager_b.organization
    )


def test_attendance_rls_blocks_cross_tenant_raw_sql_read():
    employee_a = EmployeeFactory()
    employee_b = EmployeeFactory()
    Attendance.objects.all_tenants().create(
        organization=employee_a.organization, employee=employee_a, attendance_date="2026-08-01"
    )
    Attendance.objects.all_tenants().create(
        organization=employee_b.organization, employee=employee_b, attendance_date="2026-08-01"
    )
    _assert_standard_tenant_rls(
        "attendance_attendance", employee_a.organization, employee_b.organization
    )


def test_security_event_rls_blocks_cross_tenant_raw_sql_read():
    # Mirrors the audit_logs case: a nullable-organization (platform-level)
    # row must be visible only under WILDCARD, never to a tenant session.
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    SecurityEvent.objects.all_tenants().create(
        organization=org_a, event_type=SecurityEventType.MOCK_LOCATION_DETECTED
    )
    SecurityEvent.objects.all_tenants().create(
        organization=org_b, event_type=SecurityEventType.MOCK_LOCATION_DETECTED
    )
    SecurityEvent.objects.all_tenants().create(
        organization=None, event_type=SecurityEventType.CROSS_TENANT_ACCESS_ATTEMPT
    )

    rls.bind(organization_id=org_a.id)
    assert _raw_org_ids("security_events_securityevent") == {org_a.id}

    rls.bind(platform_wide=True)
    assert _raw_org_ids("security_events_securityevent") == {org_a.id, org_b.id, None}

    rls.reset()
    assert _raw_org_ids("security_events_securityevent") == set()


def test_notification_rls_blocks_cross_tenant_raw_sql_read():
    user_a = UserAccountFactory()
    user_b = UserAccountFactory()
    Notification.objects.all_tenants().create(
        organization=user_a.organization,
        user=user_a,
        title="A",
        category=NotificationCategory.ATTENDANCE,
    )
    Notification.objects.all_tenants().create(
        organization=user_b.organization,
        user=user_b,
        title="B",
        category=NotificationCategory.ATTENDANCE,
    )
    _assert_standard_tenant_rls(
        "notifications_notification", user_a.organization, user_b.organization
    )


def test_report_export_job_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    ReportExportJob.objects.all_tenants().create(
        organization=org_a, report_type="daily", format=ExportFormat.PDF
    )
    ReportExportJob.objects.all_tenants().create(
        organization=org_b, report_type="daily", format=ExportFormat.PDF
    )
    _assert_standard_tenant_rls("reports_reportexportjob", org_a, org_b)


def test_leave_type_rls_blocks_cross_tenant_raw_sql_read():
    org_a, org_b = OrganizationFactory(), OrganizationFactory()
    LeaveType.objects.all_tenants().create(organization=org_a, name="Annual")
    LeaveType.objects.all_tenants().create(organization=org_b, name="Annual")
    _assert_standard_tenant_rls("leave_leavetype", org_a, org_b)


def test_leave_request_rls_blocks_cross_tenant_raw_sql_read():
    employee_a = EmployeeFactory()
    employee_b = EmployeeFactory()
    leave_type_a = LeaveType.objects.all_tenants().create(
        organization=employee_a.organization, name="Annual"
    )
    leave_type_b = LeaveType.objects.all_tenants().create(
        organization=employee_b.organization, name="Annual"
    )
    LeaveRequest.objects.all_tenants().create(
        organization=employee_a.organization,
        employee=employee_a,
        leave_type=leave_type_a,
        start_date="2026-06-01",
        end_date="2026-06-02",
    )
    LeaveRequest.objects.all_tenants().create(
        organization=employee_b.organization,
        employee=employee_b,
        leave_type=leave_type_b,
        start_date="2026-06-01",
        end_date="2026-06-02",
    )
    _assert_standard_tenant_rls(
        "leave_leaverequest", employee_a.organization, employee_b.organization
    )


def test_leave_balance_rls_blocks_cross_tenant_raw_sql_read():
    employee_a = EmployeeFactory()
    employee_b = EmployeeFactory()
    leave_type_a = LeaveType.objects.all_tenants().create(
        organization=employee_a.organization, name="Annual"
    )
    leave_type_b = LeaveType.objects.all_tenants().create(
        organization=employee_b.organization, name="Annual"
    )
    LeaveBalance.objects.all_tenants().create(
        organization=employee_a.organization,
        employee=employee_a,
        leave_type=leave_type_a,
        year=2026,
    )
    LeaveBalance.objects.all_tenants().create(
        organization=employee_b.organization,
        employee=employee_b,
        leave_type=leave_type_b,
        year=2026,
    )
    _assert_standard_tenant_rls(
        "leave_leavebalance", employee_a.organization, employee_b.organization
    )
