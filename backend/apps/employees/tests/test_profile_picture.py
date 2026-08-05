from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.authentication.models import Role
from storage import supabase_client
from tests.factories import EmployeeFactory, UserAccountFactory

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


@patch("apps.employees.services.supabase_client.create_signed_upload_path")
def test_self_can_request_profile_picture_upload_url(mock_create_path):
    mock_create_path.return_value = ("https://storage.example/signed-put-url", "org/emp/uuid.jpg")
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.post(
        f"/api/v1/employees/{employee.id}/profile-picture",
        {"content_type": "image/jpeg", "file_size": 1024 * 200},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["upload_url"] == "https://storage.example/signed-put-url"
    assert "org/emp/uuid.jpg" in body["profile_picture_url"]

    mock_create_path.assert_called_once()
    call_kwargs = mock_create_path.call_args.kwargs
    assert call_kwargs["path_prefix"] == f"{employee.organization_id}/{employee.id}"
    assert call_kwargs["extension"] == "jpg"

    employee.refresh_from_db()
    assert employee.profile_picture_url == body["profile_picture_url"]


@patch("apps.employees.services.supabase_client.create_signed_upload_path")
def test_employee_cannot_request_upload_for_another_employee(mock_create_path):
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    other_employee = EmployeeFactory(user__organization=user.organization)
    client = _client_as(user)

    response = client.post(
        f"/api/v1/employees/{other_employee.id}/profile-picture",
        {"content_type": "image/jpeg", "file_size": 1024},
        format="json",
    )

    assert response.status_code == 403
    mock_create_path.assert_not_called()


def test_rejects_disallowed_content_type():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.post(
        f"/api/v1/employees/{employee.id}/profile-picture",
        {"content_type": "application/pdf", "file_size": 1024},
        format="json",
    )

    assert response.status_code == 400


def test_rejects_oversized_file():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.post(
        f"/api/v1/employees/{employee.id}/profile-picture",
        {"content_type": "image/jpeg", "file_size": 10 * 1024 * 1024},
        format="json",
    )

    assert response.status_code == 400


@override_settings(DEBUG=False)
def test_storage_not_configured_surfaces_as_clean_503_outside_debug():
    # No mocking here: SUPABASE_URL/SUPABASE_SERVICE_KEY are blank by
    # default in local/test settings, exercising the real
    # StorageNotConfiguredError path end-to-end. DEBUG is forced off here
    # to exercise the production-like branch — see the DEBUG=True fallback
    # test below for local dev's behavior under the same unconfigured state.
    assert supabase_client.settings.SUPABASE_URL == ""
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = client.post(
        f"/api/v1/employees/{employee.id}/profile-picture",
        {"content_type": "image/jpeg", "file_size": 1024},
        format="json",
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_NOT_CONFIGURED"


@override_settings(DEBUG=True)
def test_storage_not_configured_falls_back_to_local_dev_storage_under_debug():
    # Calls the service directly rather than through the HTTP client:
    # pytest-django forces settings.DEBUG False for the whole test session
    # regardless of core.settings.local's own DEBUG=True, and going through
    # a real request with DEBUG=True also activates debug_toolbar's
    # middleware, whose own URLs are never registered under that forced
    # DEBUG=False at urlconf import time — a failure unrelated to this path.
    from django.conf import settings

    from apps.employees import services

    assert supabase_client.settings.SUPABASE_URL == ""
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)

    upload_url, profile_picture_url = services.request_profile_picture_upload(
        employee=employee, content_type="image/jpeg", actor=user
    )

    assert upload_url.startswith(settings.LOCAL_DEV_PUBLIC_BASE_URL)
    assert profile_picture_url.startswith(settings.LOCAL_DEV_PUBLIC_BASE_URL)

    employee.refresh_from_db()
    assert employee.profile_picture_url == profile_picture_url
