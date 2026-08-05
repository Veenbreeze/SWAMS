import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from tests.factories import BranchFactory, OrganizationFactory, UserAccountFactory

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


def test_org_admin_can_create_branch_with_gps_accuracy():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post(
        "/api/v1/branches",
        {
            "name": "Head Office",
            "address": "1 Example Street",
            "latitude": -6.792354,
            "longitude": 39.208328,
            "radius_meters": 150,
            "gps_accuracy_limit_meters": 40,
            "gps_accuracy": 8.5,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Head Office"
    assert body["radius_meters"] == 150


def test_creating_branch_with_imprecise_gps_accuracy_is_rejected():
    # A desktop browser with no GPS chip falls back to WiFi/IP-based
    # positioning, which can report hundreds of meters of accuracy — that
    # can't be allowed to become a branch's permanent check-in center, or
    # no employee's real phone GPS could ever satisfy the geofence.
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post(
        "/api/v1/branches",
        {
            "name": "Head Office",
            "address": "1 Example Street",
            "latitude": -6.792354,
            "longitude": 39.208328,
            "radius_meters": 150,
            "gps_accuracy_limit_meters": 40,
            "gps_accuracy": 500,
        },
    )

    assert response.status_code == 400
    assert "gps_accuracy" in response.json()["error"]["details"]


def test_creating_branch_without_gps_accuracy_is_rejected():
    admin = _org_admin()
    client = _client_as(admin)

    response = client.post(
        "/api/v1/branches",
        {
            "name": "Head Office",
            "latitude": -6.792354,
            "longitude": 39.208328,
        },
    )

    assert response.status_code == 400
    assert "gps_accuracy" in response.json()["error"]["details"]


def test_manager_can_list_branches_but_not_create():
    manager = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    BranchFactory(organization=manager.organization)
    client = _client_as(manager)

    list_response = client.get("/api/v1/branches")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1

    create_response = client.post(
        "/api/v1/branches",
        {
            "name": "New Branch",
            "latitude": -6.8,
            "longitude": 39.2,
            "gps_accuracy": 5,
        },
    )
    assert create_response.status_code == 403


def test_employee_cannot_list_branches():
    employee = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    client = _client_as(employee)

    response = client.get("/api/v1/branches")

    assert response.status_code == 403


def test_branches_are_tenant_isolated():
    org_a_admin = _org_admin()
    org_b = OrganizationFactory()
    BranchFactory(organization=org_a_admin.organization, name="Org A Branch")
    BranchFactory(organization=org_b, name="Org B Branch")

    client = _client_as(org_a_admin)
    response = client.get("/api/v1/branches")

    names = {branch["name"] for branch in response.json()["results"]}
    assert names == {"Org A Branch"}


def test_capture_location_updates_branch_coordinates():
    admin = _org_admin()
    branch = BranchFactory(organization=admin.organization, latitude="0", longitude="0")
    client = _client_as(admin)

    response = client.post(
        f"/api/v1/branches/{branch.id}/capture-location",
        {"latitude": -6.793000, "longitude": 39.209000, "gps_accuracy": 6.2},
    )

    assert response.status_code == 200
    branch.refresh_from_db()
    assert str(branch.latitude) == "-6.793000"
    assert str(branch.longitude) == "39.209000"


def test_capture_location_without_gps_accuracy_is_rejected():
    admin = _org_admin()
    branch = BranchFactory(organization=admin.organization)
    client = _client_as(admin)

    response = client.post(
        f"/api/v1/branches/{branch.id}/capture-location",
        {"latitude": -6.793000, "longitude": 39.209000},
    )

    assert response.status_code == 400
