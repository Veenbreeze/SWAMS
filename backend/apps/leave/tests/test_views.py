import datetime

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from tests.factories import (
    EmployeeFactory,
    LeaveRequestFactory,
    LeaveTypeFactory,
    ManagerAssignmentFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"


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


def test_leave_types_are_listed_for_any_authenticated_user():
    admin = _org_admin()
    LeaveTypeFactory(organization=admin.organization, name="Annual")
    client = _client_as(admin)

    response = client.get("/api/v1/leave/types")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_employee_can_submit_and_list_own_leave_requests():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    EmployeeFactory(user=user)
    leave_type = LeaveTypeFactory(organization=user.organization)
    client = _client_as(user)

    response = client.post(
        "/api/v1/leave/requests",
        {
            "leave_type": str(leave_type.id),
            "start_date": "2026-06-01",
            "end_date": "2026-06-03",
            "reason": "Trip",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["days_requested"] == 3

    listing = client.get("/api/v1/leave/requests")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1


def test_org_admin_without_employee_profile_cannot_submit():
    admin = _org_admin()
    leave_type = LeaveTypeFactory(organization=admin.organization)
    client = _client_as(admin)

    response = client.post(
        "/api/v1/leave/requests",
        {"leave_type": str(leave_type.id), "start_date": "2026-06-01", "end_date": "2026-06-01"},
        format="json",
    )

    assert response.status_code == 403


def test_employee_cannot_see_another_employees_leave_requests():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    other = EmployeeFactory(user__organization=user.organization)
    LeaveRequestFactory(employee=other)
    LeaveRequestFactory(employee=employee)
    client = _client_as(user)

    response = client.get("/api/v1/leave/requests")

    assert response.json()["count"] == 1


def test_org_admin_approves_leave_request():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)
    client = _client_as(admin)

    response = client.post(f"/api/v1/leave/requests/{leave_request.id}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_reject_requires_a_reason():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    leave_request = LeaveRequestFactory(employee=employee)
    client = _client_as(admin)

    missing_reason = client.post(f"/api/v1/leave/requests/{leave_request.id}/reject")
    assert missing_reason.status_code == 400

    response = client.post(
        f"/api/v1/leave/requests/{leave_request.id}/reject",
        {"reason": "Not enough coverage"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["decision_reason"] == "Not enough coverage"


def test_manager_can_only_approve_within_scope():
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    manager_employee = EmployeeFactory(user=manager_user)
    in_scope = EmployeeFactory(user__organization=manager_user.organization)
    out_of_scope = EmployeeFactory(user__organization=manager_user.organization)
    ManagerAssignmentFactory(manager=manager_employee, employee=in_scope)
    in_scope_request = LeaveRequestFactory(employee=in_scope)
    out_of_scope_request = LeaveRequestFactory(employee=out_of_scope)
    client = _client_as(manager_user)

    allowed = client.post(f"/api/v1/leave/requests/{in_scope_request.id}/approve")
    assert allowed.status_code == 200

    denied = client.post(f"/api/v1/leave/requests/{out_of_scope_request.id}/approve")
    assert denied.status_code == 403


def test_employee_can_edit_own_pending_request_but_not_after_decision():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    leave_request = LeaveRequestFactory(employee=employee, reason="Old reason")
    client = _client_as(user)

    edited = client.patch(f"/api/v1/leave/requests/{leave_request.id}", {"reason": "New reason"})
    assert edited.status_code == 200
    assert edited.json()["reason"] == "New reason"

    admin = UserAccountFactory(
        password=PASSWORD, role=Role.ORG_ADMIN, organization=user.organization
    )
    admin_client = _client_as(admin)
    admin_client.post(f"/api/v1/leave/requests/{leave_request.id}/approve")

    blocked = client.patch(f"/api/v1/leave/requests/{leave_request.id}", {"reason": "Too late"})
    assert blocked.status_code == 400


def test_leave_balance_defaults_to_self():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    leave_type = LeaveTypeFactory(organization=user.organization, default_annual_days=15)
    leave_request = LeaveRequestFactory(
        employee=employee,
        leave_type=leave_type,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 2),
    )
    admin = UserAccountFactory(
        password=PASSWORD, role=Role.ORG_ADMIN, organization=user.organization
    )
    _client_as(admin).post(f"/api/v1/leave/requests/{leave_request.id}/approve")
    client = _client_as(user)

    response = client.get("/api/v1/leave/balance")

    assert response.status_code == 200
    body = response.json()["results"]
    assert len(body) == 1
    assert body[0]["allocated_days"] == "15.0"
    assert body[0]["used_days"] == "2.0"
    assert body[0]["remaining_days"] == "13.0"


def test_leave_balance_for_another_employee_requires_scope():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    other_user = UserAccountFactory(
        password=PASSWORD, role=Role.EMPLOYEE, organization=user.organization
    )
    other_employee = EmployeeFactory(user=other_user)
    client = _client_as(user)

    response = client.get(f"/api/v1/leave/balance?employee_id={employee.id}")
    assert response.status_code == 200

    denied = client.get(f"/api/v1/leave/balance?employee_id={other_employee.id}")
    assert denied.status_code == 403
