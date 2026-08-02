import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from core.middleware.tenant_context import current_organization_id, current_role
from core.middleware.tenant_middleware import TenantAwareJWTAuthentication
from tests.factories import SuperAdminFactory, UserAccountFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"


def test_jwt_carries_the_users_own_organization_id_claim():
    user = UserAccountFactory(password=PASSWORD)
    response = APIClient().post(
        "/api/v1/auth/login",
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )

    decoded = AccessToken(response.json()["access_token"])
    assert decoded["organization_id"] == str(user.organization_id)
    assert decoded["role"] == user.role


def test_super_admin_jwt_has_null_organization_id():
    admin = SuperAdminFactory(password=PASSWORD)
    response = APIClient().post(
        "/api/v1/auth/login", {"identifier": admin.email, "password": PASSWORD}
    )

    decoded = AccessToken(response.json()["access_token"])
    assert decoded["organization_id"] is None


def test_tenant_context_binds_the_authenticated_users_organization(rf):
    user = UserAccountFactory()
    token = RefreshToken.for_user(user).access_token

    request = rf.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    TenantAwareJWTAuthentication().authenticate(request)

    assert current_organization_id.get() == str(user.organization_id)
    assert current_role.get() == user.role


def test_a_users_token_cannot_authenticate_under_a_different_organization_code():
    """The org_code in the login request must match the resolved user's
    actual organization — a correct password for org A's user cannot be
    used to sign in "as" org B."""
    from tests.factories import OrganizationFactory

    org_b = OrganizationFactory()
    user = UserAccountFactory(password=PASSWORD)

    response = APIClient().post(
        "/api/v1/auth/login",
        {"organization_code": org_b.code, "identifier": user.email, "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
