import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from tests.factories import (
    DepartmentFactory,
    EmployeeFactory,
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


def _manager_employee():
    user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    employee = EmployeeFactory(user=user)
    return user, employee


def test_manager_sees_only_department_scoped_employees():
    manager_user, manager_employee = _manager_employee()
    org = manager_user.organization
    scoped_department = DepartmentFactory(organization=org)
    other_department = DepartmentFactory(organization=org)

    in_scope = EmployeeFactory(user__organization=org, department=scoped_department)
    EmployeeFactory(user__organization=org, department=other_department)  # out of scope

    ManagerAssignmentFactory(manager=manager_employee, department=scoped_department)

    client = _client_as(manager_user)
    response = client.get("/api/v1/employees")

    ids = {row["id"] for row in response.json()["results"]}
    assert ids == {str(in_scope.id)}


def test_manager_sees_directly_assigned_employee_outside_their_department():
    manager_user, manager_employee = _manager_employee()
    org = manager_user.organization
    directly_assigned = EmployeeFactory(user__organization=org)
    EmployeeFactory(user__organization=org)  # unrelated, out of scope

    ManagerAssignmentFactory(manager=manager_employee, employee=directly_assigned)

    client = _client_as(manager_user)
    response = client.get("/api/v1/employees")

    ids = {row["id"] for row in response.json()["results"]}
    assert ids == {str(directly_assigned.id)}


def test_manager_without_assignment_sees_no_employees():
    manager_user, _ = _manager_employee()
    EmployeeFactory(user__organization=manager_user.organization)

    client = _client_as(manager_user)
    response = client.get("/api/v1/employees")

    assert response.json()["count"] == 0


def test_manager_can_retrieve_in_scope_employee_detail():
    manager_user, manager_employee = _manager_employee()
    department = DepartmentFactory(organization=manager_user.organization)
    in_scope = EmployeeFactory(user__organization=manager_user.organization, department=department)
    ManagerAssignmentFactory(manager=manager_employee, department=department)

    client = _client_as(manager_user)
    response = client.get(f"/api/v1/employees/{in_scope.id}")

    assert response.status_code == 200


def test_manager_cannot_retrieve_out_of_scope_employee_detail():
    manager_user, _ = _manager_employee()
    out_of_scope = EmployeeFactory(user__organization=manager_user.organization)

    client = _client_as(manager_user)
    response = client.get(f"/api/v1/employees/{out_of_scope.id}")

    assert response.status_code == 403


def test_manager_assignment_requires_department_or_employee():
    org_admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    manager_employee = EmployeeFactory(user__organization=org_admin.organization)
    client = _client_as(org_admin)

    response = client.post("/api/v1/manager-assignments", {"manager": str(manager_employee.id)})

    assert response.status_code == 400
