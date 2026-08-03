import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role, UserAccount
from apps.employees.models import Employee, EmploymentStatus
from tests.factories import BranchFactory, DepartmentFactory, EmployeeFactory, UserAccountFactory

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


def _employee_payload(**overrides):
    payload = {
        "email": "newhire@example.com",
        "employee_number": "EMP0001",
        "first_name": "Asha",
        "last_name": "Mwangi",
        "phone": "+255700000001",
        "position": "Cashier",
        "joining_date": "2026-01-15",
    }
    payload.update(overrides)
    return payload


def test_org_admin_can_create_employee_with_temp_password():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post("/api/v1/employees", _employee_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["employee"]["employee_number"] == "EMP0001"
    assert body["employee"]["role"] == Role.EMPLOYEE
    assert len(body["temporary_password"]) > 0

    user = UserAccount.objects.get(email="newhire@example.com")
    assert user.must_change_password is True
    assert user.check_password(body["temporary_password"])
    assert user.organization_id == admin.organization_id


def test_created_employee_can_log_in_with_temp_password_and_must_change_it():
    admin = _org_admin()
    client = _client_as(admin)
    create = client.post("/api/v1/employees", _employee_payload())
    temp_password = create.json()["temporary_password"]

    login = APIClient().post(
        "/api/v1/auth/login",
        {
            "organization_code": admin.organization.code,
            "identifier": "newhire@example.com",
            "password": temp_password,
        },
    )

    assert login.status_code == 200
    assert login.json()["must_change_password"] is True


def test_org_admin_can_create_employee_with_manager_role():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post("/api/v1/employees", _employee_payload(role=Role.MANAGER))

    assert response.status_code == 201
    assert response.json()["employee"]["role"] == Role.MANAGER


def test_cannot_create_employee_with_org_admin_role():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post("/api/v1/employees", _employee_payload(role=Role.ORG_ADMIN))

    assert response.status_code == 400


def test_employee_number_unique_per_organization():
    admin = _org_admin()
    client = _client_as(admin)
    client.post("/api/v1/employees", _employee_payload())

    response = client.post(
        "/api/v1/employees", _employee_payload(email="second@example.com")
    )

    assert response.status_code == 400


def test_employees_are_tenant_isolated():
    admin = _org_admin()
    EmployeeFactory(user__organization=admin.organization)
    EmployeeFactory()  # different org

    client = _client_as(admin)
    response = client.get("/api/v1/employees")

    assert response.json()["count"] == 1


def test_org_admin_can_update_any_field():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    department = DepartmentFactory(organization=admin.organization)
    client = _client_as(admin)

    response = client.patch(
        f"/api/v1/employees/{employee.id}",
        {"position": "Senior Cashier", "department": str(department.id)},
        format="json",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.position == "Senior Cashier"
    assert employee.department_id == department.id


def test_employee_can_update_own_phone_only():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.patch(f"/api/v1/employees/{employee.id}", {"phone": "+255711111111"})

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.phone == "+255711111111"


def test_employee_cannot_update_own_position_via_self_serializer():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user, position="Cashier")
    client = _client_as(user)

    response = client.patch(f"/api/v1/employees/{employee.id}", {"position": "Manager"})

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.position == "Cashier"  # field silently ignored, not writable by self


def test_employee_cannot_update_another_employees_record():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    other_employee = EmployeeFactory(user__organization=user.organization)
    client = _client_as(user)

    response = client.patch(f"/api/v1/employees/{other_employee.id}", {"phone": "+255700000000"})

    assert response.status_code == 403


def test_org_admin_soft_deletes_employee():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    client = _client_as(admin)

    response = client.delete(f"/api/v1/employees/{employee.id}")

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.employment_status == EmploymentStatus.TERMINATED
    assert Employee.objects.all_tenants().filter(pk=employee.pk).exists()  # row retained
    employee.user.refresh_from_db()
    assert employee.user.is_active is False


def test_reset_password_issues_new_temp_password():
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    client = _client_as(admin)

    response = client.post(f"/api/v1/employees/{employee.id}/reset-password")

    assert response.status_code == 200
    temp_password = response.json()["temporary_password"]
    employee.user.refresh_from_db()
    assert employee.user.must_change_password is True
    assert employee.user.check_password(temp_password)


def test_employee_create_rejects_branch_from_another_org():
    admin = _org_admin()
    foreign_branch = BranchFactory()  # different org
    client = _client_as(admin)

    response = client.post(
        "/api/v1/employees", _employee_payload(branch=str(foreign_branch.id))
    )

    assert response.status_code == 400
