import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.feedback.models import Recommendation
from tests.factories import EmployeeFactory, UserAccountFactory

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


def test_employee_can_submit_a_recommendation():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.post(
        "/api/v1/recommendations", {"message": "More parking spots please."}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "More parking spots please."
    assert body["employee_name"] == employee.full_name

    recommendation = Recommendation.objects.all_tenants().get()
    assert recommendation.employee_id == employee.id
    assert recommendation.organization_id == user.organization_id


def test_employee_without_profile_cannot_submit():
    user = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(user)

    response = client.post("/api/v1/recommendations", {"message": "Hello"}, format="json")

    assert response.status_code == 403


def test_org_admin_can_list_recommendations():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    employee_user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE, organization=admin.organization)
    EmployeeFactory(user=employee_user)
    client = _client_as(employee_user)
    client.post("/api/v1/recommendations", {"message": "Better coffee."}, format="json")

    admin_client = _client_as(admin)
    response = admin_client.get("/api/v1/recommendations")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["message"] == "Better coffee."


def test_employee_cannot_list_recommendations():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 403


def test_recommendations_are_scoped_to_organization():
    admin_a = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    employee_user_a = UserAccountFactory(
        password=PASSWORD, role=Role.EMPLOYEE, organization=admin_a.organization
    )
    EmployeeFactory(user=employee_user_a)
    _client_as(employee_user_a).post(
        "/api/v1/recommendations", {"message": "From org A"}, format="json"
    )

    admin_b = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    response = _client_as(admin_b).get("/api/v1/recommendations")

    assert response.status_code == 200
    assert response.json()["count"] == 0
