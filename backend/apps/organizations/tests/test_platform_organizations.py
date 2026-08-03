import pytest
from rest_framework.test import APIClient

from apps.audit_logs.models import AuditLog
from apps.authentication.models import Role, UserAccount
from apps.organizations.models import OrganizationStatus
from tests.factories import OrganizationFactory, SuperAdminFactory, UserAccountFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"


def _new_org_payload(**overrides):
    payload = {
        "code": "NEWORG01",
        "name": "New Organization Ltd",
        "registration_number": "REG-000123",
        "email": "contact@neworg.example",
        "phone": "+255700000000",
        "address": "1 Example Street",
        "logo_url": "",
        "admin_email": "admin@neworg.example",
    }
    payload.update(overrides)
    return payload


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


def test_super_admin_can_create_organization_and_bootstrap_org_admin():
    admin = SuperAdminFactory(password=PASSWORD)
    client = _client_as(admin)

    response = client.post("/api/v1/platform/organizations", _new_org_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["organization"]["code"] == "NEWORG01"
    assert body["admin"]["email"] == "admin@neworg.example"
    assert body["admin"]["role"] == Role.ORG_ADMIN
    assert len(body["temporary_password"]) > 0

    org_admin = UserAccount.objects.get(email="admin@neworg.example")
    assert org_admin.must_change_password is True
    assert org_admin.check_password(body["temporary_password"])

    log = AuditLog.objects.all_tenants().get(action="organization.created")
    assert log.organization.code == "NEWORG01"
    assert log.user == admin


@pytest.mark.parametrize("role", [Role.ORG_ADMIN, Role.MANAGER, Role.EMPLOYEE])
def test_creating_organization_requires_super_admin_role(role):
    user = UserAccountFactory(password=PASSWORD, role=role)
    client = _client_as(user)

    response = client.post("/api/v1/platform/organizations", _new_org_payload())

    assert response.status_code == 403


def test_list_organizations_filters_by_status():
    admin = SuperAdminFactory(password=PASSWORD)
    OrganizationFactory(status=OrganizationStatus.ACTIVE)
    OrganizationFactory(status=OrganizationStatus.SUSPENDED)
    client = _client_as(admin)

    response = client.get(
        "/api/v1/platform/organizations", {"status": OrganizationStatus.SUSPENDED}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert all(org["status"] == OrganizationStatus.SUSPENDED for org in results)
    assert len(results) == 1


def test_retrieve_organization_detail():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory()
    client = _client_as(admin)

    response = client.get(f"/api/v1/platform/organizations/{org.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(org.id)


def test_patch_organization_updates_fields_and_logs_audit_entry():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory(name="Old Name")
    client = _client_as(admin)

    response = client.patch(f"/api/v1/platform/organizations/{org.id}", {"name": "New Name"})

    assert response.status_code == 200
    org.refresh_from_db()
    assert org.name == "New Name"
    assert AuditLog.objects.all_tenants().filter(action="organization.updated").exists()


def test_suspend_then_activate_organization_round_trip():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    client = _client_as(admin)

    suspend = client.post(f"/api/v1/platform/organizations/{org.id}/suspend")
    assert suspend.status_code == 200
    org.refresh_from_db()
    assert org.status == OrganizationStatus.SUSPENDED

    activate = client.post(f"/api/v1/platform/organizations/{org.id}/activate")
    assert activate.status_code == 200
    org.refresh_from_db()
    assert org.status == OrganizationStatus.ACTIVE

    actions = set(
        AuditLog.objects.all_tenants().filter(organization=org).values_list("action", flat=True)
    )
    assert {"organization.suspended", "organization.activated"} <= actions


def test_suspending_an_already_suspended_organization_is_rejected():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory(status=OrganizationStatus.SUSPENDED)
    client = _client_as(admin)

    response = client.post(f"/api/v1/platform/organizations/{org.id}/suspend")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORGANIZATION_STATUS_UNCHANGED"


def test_suspended_organization_blocks_login_for_its_users():
    admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    employee = UserAccountFactory(organization=org, password=PASSWORD)
    admin_client = _client_as(admin)

    admin_client.post(f"/api/v1/platform/organizations/{org.id}/suspend")

    login = APIClient().post(
        "/api/v1/auth/login",
        {"organization_code": org.code, "identifier": employee.email, "password": PASSWORD},
    )

    assert login.status_code == 403
    assert login.json()["error"]["code"] == "ORGANIZATION_SUSPENDED"
