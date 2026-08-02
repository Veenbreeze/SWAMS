import pytest
from rest_framework.test import APIClient

from tests.factories import UserAccountFactory

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
LOGOUT_ALL_URL = "/api/v1/auth/logout-all"
PASSWORD = "Sup3rSecret!Pass"


def _login(client, user):
    response = client.post(
        LOGIN_URL,
        {
            "organization_code": user.organization.code,
            "identifier": user.email,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_refresh_rotates_token_and_issues_new_access_token():
    user = UserAccountFactory(password=PASSWORD)
    client = APIClient()
    tokens = _login(client, user)

    response = client.post(REFRESH_URL, {"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != tokens["refresh_token"]


def test_reusing_a_rotated_refresh_token_is_detected_and_revokes_all_sessions():
    user = UserAccountFactory(password=PASSWORD)
    client = APIClient()
    tokens = _login(client, user)

    first_refresh = client.post(REFRESH_URL, {"refresh_token": tokens["refresh_token"]})
    assert first_refresh.status_code == 200
    new_refresh_token = first_refresh.json()["refresh_token"]

    # Replay the now-rotated-out original refresh token.
    replay = client.post(REFRESH_URL, {"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "TOKEN_REUSE_DETECTED"

    # The legitimate, newer refresh token must also now be revoked.
    followup = client.post(REFRESH_URL, {"refresh_token": new_refresh_token})
    assert followup.status_code == 401


def test_garbage_refresh_token_is_rejected_without_revoking_anything():
    response = APIClient().post(REFRESH_URL, {"refresh_token": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_logout_blacklists_the_presented_refresh_token():
    user = UserAccountFactory(password=PASSWORD)
    client = APIClient()
    tokens = _login(client, user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    logout = client.post(LOGOUT_URL, {"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 204

    reuse = APIClient().post(REFRESH_URL, {"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401


def test_logout_all_revokes_every_session():
    user = UserAccountFactory(password=PASSWORD)
    session_one = _login(APIClient(), user)
    session_two = _login(APIClient(), user)

    authed_client = APIClient()
    authed_client.credentials(HTTP_AUTHORIZATION=f"Bearer {session_one['access_token']}")
    response = authed_client.post(LOGOUT_ALL_URL)
    assert response.status_code == 204

    for token in (session_one["refresh_token"], session_two["refresh_token"]):
        refresh_response = APIClient().post(REFRESH_URL, {"refresh_token": token})
        assert refresh_response.status_code == 401
