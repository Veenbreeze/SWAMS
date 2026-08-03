import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from tests.factories import DepartmentFactory, EmployeeFactory, UserAccountFactory

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


def test_org_admin_can_create_and_list_departments():
    admin = _org_admin()
    client = _client_as(admin)

    create = client.post("/api/v1/departments", {"name": "Engineering"})
    assert create.status_code == 201

    listing = client.get("/api/v1/departments")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1


def test_departments_are_tenant_isolated():
    admin = _org_admin()
    DepartmentFactory(organization=admin.organization, name="Mine")
    DepartmentFactory(name="Theirs")  # different org via SubFactory default

    client = _client_as(admin)
    response = client.get("/api/v1/departments")

    names = {d["name"] for d in response.json()["results"]}
    assert names == {"Mine"}


def test_deleting_department_with_active_employees_is_blocked():
    admin = _org_admin()
    department = DepartmentFactory(organization=admin.organization)
    EmployeeFactory(user__organization=admin.organization, department=department)
    client = _client_as(admin)

    response = client.delete(f"/api/v1/departments/{department.id}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DEPARTMENT_HAS_EMPLOYEES"


def test_deleting_empty_department_succeeds():
    admin = _org_admin()
    department = DepartmentFactory(organization=admin.organization)
    client = _client_as(admin)

    response = client.delete(f"/api/v1/departments/{department.id}")

    assert response.status_code == 204


def test_manager_can_read_but_not_write_departments():
    manager = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    DepartmentFactory(organization=manager.organization)
    client = _client_as(manager)

    assert client.get("/api/v1/departments").status_code == 200
    assert client.post("/api/v1/departments", {"name": "New"}).status_code == 403
