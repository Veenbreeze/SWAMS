import pytest
from rest_framework.test import APIClient

from apps.audit_logs.services import AuditLogger
from apps.authentication.models import Role
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


def test_super_admin_can_list_audit_logs_across_organizations():
    admin = SuperAdminFactory(password=PASSWORD)
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    rls.bind(platform_wide=True)
    AuditLogger.record(actor=None, action="organization.created", organization=org_a)
    AuditLogger.record(actor=None, action="organization.created", organization=org_b)
    rls.reset()

    client = _client_as(admin)
    response = client.get("/api/v1/platform/audit-logs")

    assert response.status_code == 200
    results = response.json()["results"]
    organization_ids = {row["organization_id"] for row in results}
    assert str(org_a.id) in organization_ids
    assert str(org_b.id) in organization_ids


def test_audit_log_list_filters_by_action():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory()
    rls.bind(platform_wide=True)
    AuditLogger.record(actor=None, action="organization.created", organization=org)
    AuditLogger.record(actor=None, action="organization.suspended", organization=org)
    rls.reset()

    client = _client_as(admin)
    response = client.get("/api/v1/platform/audit-logs", {"action": "organization.suspended"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["action"] == "organization.suspended"


def test_audit_log_entry_with_null_organization_and_user_serializes_safely():
    admin = SuperAdminFactory(password=PASSWORD)
    rls.bind(platform_wide=True)
    AuditLogger.record(actor=None, action="system.maintenance")
    rls.reset()

    client = _client_as(admin)
    response = client.get("/api/v1/platform/audit-logs", {"action": "system.maintenance"})

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["organization_id"] is None
    assert row["organization_name"] is None
    assert row["user_email"] is None


@pytest.mark.parametrize("role", [Role.ORG_ADMIN, Role.MANAGER, Role.EMPLOYEE])
def test_listing_audit_logs_requires_super_admin_role(role):
    user = UserAccountFactory(password=PASSWORD, role=role)
    client = _client_as(user)

    response = client.get("/api/v1/platform/audit-logs")

    assert response.status_code == 403
