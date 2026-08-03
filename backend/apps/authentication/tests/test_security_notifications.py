import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.notifications.models import Notification, NotificationCategory
from apps.security.models import SecurityEvent, SecurityEventType
from tests.factories import UserAccountFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"
LOGIN_URL = "/api/v1/auth/login"


def _login(user, **extra):
    return APIClient().post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code if user.organization else "",
            "identifier": user.email,
            "password": PASSWORD,
            **extra,
        },
    )


def test_first_login_with_a_device_id_notifies_user_and_logs_security_event():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)

    response = _login(user, device_id="device-123", device_name="Pixel 8", platform="android")

    assert response.status_code == 200
    assert Notification.objects.all_tenants().filter(
        user=user, category=NotificationCategory.SECURITY, title="New device signed in"
    ).exists()
    assert SecurityEvent.objects.all_tenants().filter(
        user=user, event_type=SecurityEventType.NEW_DEVICE_LOGIN
    ).exists()


def test_new_device_login_also_notifies_org_admins_but_not_the_actor_themself():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    employee = UserAccountFactory(
        password=PASSWORD, role=Role.EMPLOYEE, organization=admin.organization
    )

    _login(employee, device_id="device-456")

    assert Notification.objects.all_tenants().filter(
        user=admin, category=NotificationCategory.SECURITY, title="New device login"
    ).exists()
    # The Org Admin's own login (no device_id) never fires this at all,
    # and their notification above is about the *employee's* device.
    assert not Notification.objects.all_tenants().filter(
        user=admin, title="New device signed in"
    ).exists()


def test_repeat_login_with_same_device_does_not_renotify():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)

    _login(user, device_id="device-789")
    _login(user, device_id="device-789")

    assert (
        Notification.objects.all_tenants().filter(
            user=user, title="New device signed in"
        ).count()
        == 1
    )


def test_login_without_device_id_does_not_trigger_device_notification():
    user = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)

    _login(user)

    assert not Notification.objects.all_tenants().filter(user=user).exists()


def test_change_password_sends_security_notification():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    login = _login(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access_token']}")

    response = client.post(
        "/api/v1/auth/change-password",
        {"current_password": PASSWORD, "new_password": "NewSup3rSecret!2"},
    )

    assert response.status_code == 204
    assert Notification.objects.all_tenants().filter(
        user=user, category=NotificationCategory.SECURITY, title="Password changed"
    ).exists()
