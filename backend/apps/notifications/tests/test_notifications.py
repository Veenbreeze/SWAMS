import pytest
from rest_framework.test import APIClient

from apps.notifications.models import Notification, NotificationCategory
from apps.notifications.services import NotificationDispatcher
from core.db import rls
from tests.factories import UserAccountFactory

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


def test_dispatcher_creates_in_app_notification():
    user = UserAccountFactory(password=PASSWORD)

    NotificationDispatcher.notify(
        user=user,
        category=NotificationCategory.ATTENDANCE,
        title="Checked in",
        message="You checked in at 08:00.",
    )

    # `.notify()` is called directly here, outside any authenticated
    # request — reading the row back via `.all_tenants()` still needs the
    # RLS session bound on Postgres (INSERT is permissive, SELECT isn't);
    # a real request would have bound this via `TenantAwareJWTAuthentication`.
    rls.bind(platform_wide=True)
    notification = Notification.objects.all_tenants().get()
    rls.reset()
    assert notification.user_id == user.id
    assert notification.organization_id == user.organization_id
    assert notification.is_read is False


def test_user_sees_only_their_own_notifications():
    user = UserAccountFactory(password=PASSWORD)
    other_user = UserAccountFactory(organization=user.organization, password=PASSWORD)
    NotificationDispatcher.notify(
        user=user, category=NotificationCategory.ATTENDANCE, title="Mine"
    )
    NotificationDispatcher.notify(
        user=other_user, category=NotificationCategory.ATTENDANCE, title="Theirs"
    )

    client = _client_as(user)
    response = client.get("/api/v1/notifications")

    titles = {n["title"] for n in response.json()["results"]}
    assert titles == {"Mine"}


def test_mark_read_and_mark_all_read():
    user = UserAccountFactory(password=PASSWORD)
    NotificationDispatcher.notify(user=user, category=NotificationCategory.ATTENDANCE, title="A")
    n2 = NotificationDispatcher.notify(
        user=user, category=NotificationCategory.ATTENDANCE, title="B"
    )
    client = _client_as(user)

    read_one = client.post(f"/api/v1/notifications/{n2.id}/read")
    assert read_one.status_code == 200
    assert read_one.json()["is_read"] is True

    read_all = client.post("/api/v1/notifications/read-all")
    assert read_all.status_code == 200
    assert read_all.json()["updated"] == 1  # only the one still unread

    assert Notification.objects.all_tenants().filter(user=user, is_read=False).count() == 0


def test_cannot_mark_another_users_notification_read():
    user = UserAccountFactory(password=PASSWORD)
    other_user = UserAccountFactory(organization=user.organization, password=PASSWORD)
    theirs = NotificationDispatcher.notify(
        user=other_user, category=NotificationCategory.ATTENDANCE, title="Theirs"
    )

    client = _client_as(user)
    response = client.post(f"/api/v1/notifications/{theirs.id}/read")

    assert response.status_code == 404
