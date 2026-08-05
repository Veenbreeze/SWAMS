import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.platform_settings.models import PlatformSettings
from tests.factories import SuperAdminFactory, UserAccountFactory

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


def test_get_creates_default_settings_on_first_access():
    admin = SuperAdminFactory(password=PASSWORD)
    client = _client_as(admin)

    response = client.get("/api/v1/platform/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_mode"] is False
    assert body["default_trial_days"] == 14
    assert body["support_email"] == ""
    assert PlatformSettings.objects.count() == 1


def test_patch_updates_settings_and_persists():
    admin = SuperAdminFactory(password=PASSWORD)
    client = _client_as(admin)

    response = client.patch(
        "/api/v1/platform/settings",
        {"maintenance_mode": True, "default_trial_days": 30, "support_email": "help@swams.app"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["maintenance_mode"] is True
    assert body["default_trial_days"] == 30
    assert body["support_email"] == "help@swams.app"

    settings_obj = PlatformSettings.load()
    assert settings_obj.maintenance_mode is True
    assert settings_obj.default_trial_days == 30


def test_patch_is_a_true_singleton_across_requests():
    admin = SuperAdminFactory(password=PASSWORD)
    client = _client_as(admin)

    client.patch("/api/v1/platform/settings", {"default_trial_days": 21})
    response = client.get("/api/v1/platform/settings")

    assert response.json()["default_trial_days"] == 21
    assert PlatformSettings.objects.count() == 1


@pytest.mark.parametrize("role", [Role.ORG_ADMIN, Role.MANAGER, Role.EMPLOYEE])
def test_platform_settings_requires_super_admin_role(role):
    user = UserAccountFactory(password=PASSWORD, role=role)
    client = _client_as(user)

    get_response = client.get("/api/v1/platform/settings")
    patch_response = client.patch("/api/v1/platform/settings", {"maintenance_mode": True})

    assert get_response.status_code == 403
    assert patch_response.status_code == 403
