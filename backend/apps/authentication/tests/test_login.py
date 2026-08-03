import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Device, LoginHistory
from apps.organizations.models import OrganizationStatus
from tests.factories import (
    EmployeeFactory,
    OrganizationFactory,
    SuperAdminFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login"
PASSWORD = "Sup3rSecret!Pass"


def test_login_success_with_organization_code():
    user = UserAccountFactory(password=PASSWORD)
    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["must_change_password"] is False
    assert body["user"]["email"] == user.email
    assert LoginHistory.objects.filter(user=user, was_successful=True).exists()


def test_login_response_includes_nested_employee_profile():
    employee = EmployeeFactory()
    user = employee.user
    user.set_password(PASSWORD)
    user.save(update_fields=["password"])

    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    body = response.json()["user"]["employee"]
    assert body["id"] == str(employee.id)
    assert body["employee_number"] == employee.employee_number


def test_login_response_employee_is_null_for_org_admin():
    admin = UserAccountFactory(password=PASSWORD, role="ORG_ADMIN")
    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": admin.organization.code,
            "identifier": admin.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["employee"] is None


def test_me_rehydrates_the_authenticated_user():
    employee = EmployeeFactory()
    user = employee.user
    user.set_password(PASSWORD)
    user.save(update_fields=["password"])
    login = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access_token']}")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["employee"]["id"] == str(employee.id)


def test_me_requires_authentication():
    response = APIClient().get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_success_for_super_admin_without_organization_code():
    admin = SuperAdminFactory(password=PASSWORD)
    response = APIClient().post(LOGIN_URL, {"identifier": admin.email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["organization_id"] is None


def test_login_returns_must_change_password_flag():
    user = UserAccountFactory(password=PASSWORD, must_change_password=True)
    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_login_wrong_password_fails_and_is_recorded():
    user = UserAccountFactory(password=PASSWORD)
    response = APIClient().post(
        LOGIN_URL,
        {"organization_code": user.organization.code, "identifier": user.email, "password": "nope"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert LoginHistory.objects.filter(user=user, was_successful=False).exists()


def test_login_unknown_organization_code():
    response = APIClient().post(
        LOGIN_URL, {"organization_code": "NOPE", "identifier": "a@b.com", "password": "x"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_login_suspended_organization_is_rejected():
    org = OrganizationFactory(status=OrganizationStatus.SUSPENDED)
    user = UserAccountFactory(organization=org, password=PASSWORD)

    response = APIClient().post(
        LOGIN_URL,
        {"organization_code": org.code, "identifier": user.email, "password": PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_SUSPENDED"


def test_account_locks_after_max_failed_attempts(settings):
    settings.AUTH_MAX_FAILED_ATTEMPTS = 3
    user = UserAccountFactory(password=PASSWORD)
    payload = {
        "organization_code": user.organization.code,
        "identifier": user.email,
        "password": "wrong",
    }

    for _ in range(3):
        response = APIClient().post(LOGIN_URL, payload)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    user.refresh_from_db()
    assert user.locked_until is not None

    # Even the correct password is rejected while locked.
    good_payload = {**payload, "password": PASSWORD}
    response = APIClient().post(LOGIN_URL, good_payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_successful_login_resets_failed_attempt_counter():
    user = UserAccountFactory(password=PASSWORD, failed_login_attempts=2)
    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.failed_login_attempts == 0


def test_login_upserts_device_when_device_id_provided():
    user = UserAccountFactory(password=PASSWORD)
    response = APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
            "device_id": "device-123",
            "device_name": "Pixel 8",
            "platform": "android",
        },
    )

    assert response.status_code == 200
    device = Device.objects.get(user=user, device_id="device-123")
    assert device.device_name == "Pixel 8"


def test_login_across_organizations_does_not_leak_identity():
    """Same email in two different organizations must resolve independently."""
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    user_a = UserAccountFactory(organization=org_a, email="john@example.com", password=PASSWORD)
    UserAccountFactory(organization=org_b, email="john@example.com", password="different-pass")

    response = APIClient().post(
        LOGIN_URL,
        {"organization_code": org_a.code, "identifier": "john@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user_a.id)
