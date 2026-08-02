from datetime import timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from tests.factories import UserAccountFactory

pytestmark = pytest.mark.django_db

# Any authenticated, POST-only endpoint works as a probe here.
PROBE_URL = "/api/v1/auth/logout-all"


def test_expired_access_token_returns_token_expired_code():
    user = UserAccountFactory()
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=timedelta(seconds=-1))

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.post(PROBE_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_garbage_access_token_returns_token_invalid_code():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    response = client.post(PROBE_URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_missing_token_is_not_authenticated():
    response = APIClient().post(PROBE_URL)
    assert response.status_code == 401
