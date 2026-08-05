import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.security.models import SecurityEventType
from apps.security.services import SecurityEventLogger
from core.db import rls
from tests.factories import OrganizationFactory, SuperAdminFactory, UserAccountFactory

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


@pytest.fixture(autouse=True)
def _reset_rls_after():
    yield
    rls.reset()


def test_super_admin_can_list_security_events_across_organizations():
    admin = SuperAdminFactory(password=PASSWORD)
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    SecurityEventLogger.record(
        event_type=SecurityEventType.MOCK_LOCATION_DETECTED, organization=org_a
    )
    SecurityEventLogger.record(
        event_type=SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED, organization=org_b
    )

    client = _client_as(admin)
    response = client.get("/api/v1/platform/security-events")

    assert response.status_code == 200
    results = response.json()["results"]
    organization_ids = {row["organization_id"] for row in results}
    assert str(org_a.id) in organization_ids
    assert str(org_b.id) in organization_ids


def test_security_event_list_filters_by_event_type():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory()
    SecurityEventLogger.record(
        event_type=SecurityEventType.MOCK_LOCATION_DETECTED, organization=org
    )
    SecurityEventLogger.record(
        event_type=SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED, organization=org
    )

    client = _client_as(admin)
    response = client.get(
        "/api/v1/platform/security-events",
        {"event_type": SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["event_type"] == SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED


@pytest.mark.parametrize("role", [Role.ORG_ADMIN, Role.MANAGER, Role.EMPLOYEE])
def test_listing_security_events_requires_super_admin_role(role):
    user = UserAccountFactory(password=PASSWORD, role=role)
    client = _client_as(user)

    response = client.get("/api/v1/platform/security-events")

    assert response.status_code == 403
