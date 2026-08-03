import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from tests.factories import ShiftFactory, UserAccountFactory

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


def test_org_admin_can_create_shift():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.post(
        "/api/v1/shifts",
        {"name": "Day Shift", "start_time": "08:00:00", "end_time": "17:00:00"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Day Shift"


def test_employee_can_read_but_not_create_shifts():
    employee = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    ShiftFactory(organization=employee.organization)
    client = _client_as(employee)

    list_response = client.get("/api/v1/shifts")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1

    create_response = client.post(
        "/api/v1/shifts", {"name": "Night Shift", "start_time": "22:00:00", "end_time": "06:00:00"}
    )
    assert create_response.status_code == 403


def test_shifts_are_tenant_isolated():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    other_admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    ShiftFactory(organization=admin.organization, name="Mine")
    ShiftFactory(organization=other_admin.organization, name="Theirs")

    client = _client_as(admin)
    response = client.get("/api/v1/shifts")

    names = {shift["name"] for shift in response.json()["results"]}
    assert names == {"Mine"}


def test_attendance_rule_is_created_lazily_with_defaults():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.get("/api/v1/attendance-rule")

    assert response.status_code == 200
    body = response.json()
    assert body["working_days"] == [0, 1, 2, 3, 4]
    assert body["late_threshold_minutes"] == 0


def test_attendance_rule_patch_persists_and_is_idempotent_per_org():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    client.get("/api/v1/attendance-rule")  # lazily creates the row
    response = client.patch(
        "/api/v1/attendance-rule",
        {"late_threshold_minutes": 10, "working_days": [0, 1, 2, 3, 4, 5]},
        format="json",  # default multipart encoding collapses a list to its last value
    )

    assert response.status_code == 200
    assert response.json()["late_threshold_minutes"] == 10

    refetch = client.get("/api/v1/attendance-rule")
    assert refetch.json()["late_threshold_minutes"] == 10
    assert refetch.json()["working_days"] == [0, 1, 2, 3, 4, 5]


def test_attendance_rule_rejects_invalid_working_day():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.patch("/api/v1/attendance-rule", {"working_days": [0, 7]}, format="json")

    assert response.status_code == 400


def test_manager_cannot_edit_attendance_rule():
    manager = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    client = _client_as(manager)

    response = client.get("/api/v1/attendance-rule")

    assert response.status_code == 403
