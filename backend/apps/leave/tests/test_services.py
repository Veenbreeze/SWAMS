import datetime

import pytest

from apps.authentication.models import Role
from apps.leave import services
from apps.leave.models import LeaveBalance, LeaveRequestStatus
from apps.notifications.models import Notification
from core.db import rls
from core.middleware.tenant_context import current_organization_id
from tests.factories import (
    EmployeeFactory,
    LeaveRequestFactory,
    LeaveTypeFactory,
    ManagerAssignmentFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_tenant_context():
    # Direct service-layer calls, not through an authenticated request —
    # see apps/reports/tests/test_aggregations.py for the same pattern and
    # why both the contextvar and Postgres RLS need explicit binding here.
    yield
    current_organization_id.set(None)
    rls.reset()


def _bind(organization):
    current_organization_id.set(str(organization.id))
    rls.bind(organization_id=organization.id)


def test_submit_creates_pending_request_without_touching_balance():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)

    leave_request = services.submit_leave_request(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 3),
        reason="Family trip",
    )

    assert leave_request.status == LeaveRequestStatus.PENDING
    assert leave_request.days_requested == 3
    assert not LeaveBalance.objects.all_tenants().filter(employee=employee).exists()


def test_submit_notifies_org_admin_approvers():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization)

    services.submit_leave_request(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 1),
        reason="",
    )

    assert Notification.objects.all_tenants().filter(user=admin, title="New leave request").exists()


def test_submit_rejects_end_before_start():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization)

    with pytest.raises(services.InvalidDateRangeError):
        services.submit_leave_request(
            employee=employee,
            leave_type=leave_type,
            start_date=datetime.date(2026, 6, 5),
            end_date=datetime.date(2026, 6, 1),
            reason="",
        )


def test_approve_decrements_balance_and_notifies_employee():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)
    leave_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 5),
    )

    services.approve_leave_request(leave_request=leave_request, actor=admin)

    leave_request.refresh_from_db()
    assert leave_request.status == LeaveRequestStatus.APPROVED
    assert leave_request.approved_by_id == admin.id
    assert leave_request.decided_at is not None

    balance = LeaveBalance.objects.all_tenants().get(
        employee=employee, leave_type=leave_type, year=2026
    )
    assert balance.allocated_days == 20
    assert balance.used_days == 5

    assert Notification.objects.all_tenants().filter(
        user=employee.user, title="Leave request approved"
    ).exists()


def test_approve_accumulates_across_multiple_requests_same_year():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)

    first = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 3, 1),
        end_date=datetime.date(2026, 3, 2),
    )
    second = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 4),
    )
    services.approve_leave_request(leave_request=first, actor=admin)
    services.approve_leave_request(leave_request=second, actor=admin)

    balance = LeaveBalance.objects.all_tenants().get(
        employee=employee, leave_type=leave_type, year=2026
    )
    assert balance.used_days == 2 + 4


def test_balance_is_tracked_separately_per_year():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)

    dec_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2025, 12, 30),
        end_date=datetime.date(2025, 12, 31),
    )
    jan_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 1, 2),
        end_date=datetime.date(2026, 1, 2),
    )
    services.approve_leave_request(leave_request=dec_request, actor=admin)
    services.approve_leave_request(leave_request=jan_request, actor=admin)

    balance_2025 = LeaveBalance.objects.all_tenants().get(
        employee=employee, leave_type=leave_type, year=2025
    )
    balance_2026 = LeaveBalance.objects.all_tenants().get(
        employee=employee, leave_type=leave_type, year=2026
    )
    assert balance_2025.used_days == 2
    assert balance_2026.used_days == 1


def test_cannot_approve_a_non_pending_request():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)
    services.approve_leave_request(leave_request=leave_request, actor=admin)

    with pytest.raises(services.LeaveRequestNotPendingError):
        services.approve_leave_request(leave_request=leave_request, actor=admin)


def test_reject_requires_no_balance_change_and_notifies_employee():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)
    leave_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 5),
    )

    services.reject_leave_request(leave_request=leave_request, actor=admin, reason="Understaffed")

    leave_request.refresh_from_db()
    assert leave_request.status == LeaveRequestStatus.REJECTED
    assert leave_request.decision_reason == "Understaffed"
    assert not LeaveBalance.objects.all_tenants().filter(employee=employee).exists()
    assert Notification.objects.all_tenants().filter(
        user=employee.user, title="Leave request rejected"
    ).exists()


def test_cancel_pending_request_has_no_balance_effect():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)

    services.cancel_leave_request(leave_request=leave_request, actor=employee.user)

    leave_request.refresh_from_db()
    assert leave_request.status == LeaveRequestStatus.CANCELLED
    assert not LeaveBalance.objects.all_tenants().filter(employee=employee).exists()


def test_cancel_approved_request_restores_balance():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_type = LeaveTypeFactory(organization=admin.organization, default_annual_days=20)
    leave_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 5),
    )
    services.approve_leave_request(leave_request=leave_request, actor=admin)

    services.cancel_leave_request(leave_request=leave_request, actor=admin)

    leave_request.refresh_from_db()
    assert leave_request.status == LeaveRequestStatus.CANCELLED
    balance = LeaveBalance.objects.all_tenants().get(
        employee=employee, leave_type=leave_type, year=2026
    )
    assert balance.used_days == 0


def test_cannot_cancel_a_rejected_request():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)
    services.reject_leave_request(leave_request=leave_request, actor=admin, reason="No")

    with pytest.raises(services.LeaveRequestNotCancellableError):
        services.cancel_leave_request(leave_request=leave_request, actor=admin)


def test_update_only_allowed_while_pending():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)
    services.approve_leave_request(leave_request=leave_request, actor=admin)

    with pytest.raises(services.LeaveRequestNotEditableError):
        services.update_leave_request(leave_request=leave_request, data={"reason": "Changed"})


def test_manager_scoped_approver_notified_but_not_unrelated_manager():
    admin = UserAccountFactory(role=Role.ORG_ADMIN)
    _bind(admin.organization)
    employee = EmployeeFactory(user__organization=admin.organization)
    manager_user = UserAccountFactory(role=Role.MANAGER, organization=admin.organization)
    manager_employee = EmployeeFactory(user=manager_user)
    ManagerAssignmentFactory(manager=manager_employee, employee=employee)

    unrelated_manager_user = UserAccountFactory(role=Role.MANAGER, organization=admin.organization)
    EmployeeFactory(user=unrelated_manager_user)

    leave_type = LeaveTypeFactory(organization=admin.organization)
    services.submit_leave_request(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 1),
        reason="",
    )

    assert Notification.objects.all_tenants().filter(
        user=manager_user, title="New leave request"
    ).exists()
    assert not Notification.objects.all_tenants().filter(
        user=unrelated_manager_user, title="New leave request"
    ).exists()
