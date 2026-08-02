from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from core.permissions.roles import IsManagerOrAbove, IsOrgAdmin, IsSelf, IsSuperAdmin
from tests.factories import SuperAdminFactory, UserAccountFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"


def _request_for(user):
    return SimpleNamespace(user=user)


def test_is_super_admin_permission():
    admin = SuperAdminFactory()
    employee = UserAccountFactory()
    assert IsSuperAdmin().has_permission(_request_for(admin), None) is True
    assert IsSuperAdmin().has_permission(_request_for(employee), None) is False


def test_is_org_admin_permission():
    org_admin = UserAccountFactory(role=Role.ORG_ADMIN)
    employee = UserAccountFactory(role=Role.EMPLOYEE)
    assert IsOrgAdmin().has_permission(_request_for(org_admin), None) is True
    assert IsOrgAdmin().has_permission(_request_for(employee), None) is False


def test_is_manager_or_above_permission():
    manager = UserAccountFactory(role=Role.MANAGER)
    org_admin = UserAccountFactory(role=Role.ORG_ADMIN)
    employee = UserAccountFactory(role=Role.EMPLOYEE)
    assert IsManagerOrAbove().has_permission(_request_for(manager), None) is True
    assert IsManagerOrAbove().has_permission(_request_for(org_admin), None) is True
    assert IsManagerOrAbove().has_permission(_request_for(employee), None) is False


def test_is_self_permission_against_user_account_object():
    user = UserAccountFactory()
    other = UserAccountFactory()
    assert IsSelf().has_object_permission(_request_for(user), None, user) is True
    assert IsSelf().has_object_permission(_request_for(user), None, other) is False


def test_must_change_password_blocks_other_endpoints_but_not_change_password():
    user = UserAccountFactory(password=PASSWORD, must_change_password=True)
    client = APIClient()

    login = client.post(
        "/api/v1/auth/login",
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )
    assert login.json()["must_change_password"] is True
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access_token']}")

    blocked = client.post("/api/v1/auth/logout-all")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "MUST_CHANGE_PASSWORD"

    allowed = client.post(
        "/api/v1/auth/change-password",
        {"current_password": PASSWORD, "new_password": "NewSup3rSecret!2"},
    )
    assert allowed.status_code == 204

    user.refresh_from_db()
    assert user.must_change_password is False
