import datetime
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.attendance.models import Attendance, AttendanceRule
from apps.authentication.models import Role
from apps.notifications.models import Notification
from apps.security.models import SecurityEvent, SecurityEventType
from tests.factories import (
    BranchFactory,
    EmployeeFactory,
    ManagerAssignmentFactory,
    ShiftFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"

# A branch at a fixed point with a modest radius/accuracy tolerance.
BRANCH_LAT = -6.792354
BRANCH_LON = 39.208328


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


def _employee_with_branch(**overrides):
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    branch = BranchFactory(
        organization=user.organization,
        latitude=str(BRANCH_LAT),
        longitude=str(BRANCH_LON),
        radius_meters=100,
        gps_accuracy_limit_meters=50,
    )
    employee = EmployeeFactory(user=user, branch=branch, **overrides)
    return user, employee, branch


def _in_geofence_payload(**overrides):
    payload = {
        "latitude": BRANCH_LAT,
        "longitude": BRANCH_LON,
        "accuracy": 10,
        "device_id": "device-1",
        "is_mock_location": False,
    }
    payload.update(overrides)
    return payload


def test_check_in_success_present_when_no_shift_assigned():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PRESENT"
    assert body["branch"]["name"] == branch.name

    attendance = Attendance.objects.all_tenants().get()
    assert attendance.employee_id == employee.id
    assert attendance.check_in_is_mock is False


def test_check_in_notifies_employee():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    notification = Notification.objects.all_tenants().get()
    assert notification.user_id == user.id
    assert notification.title == "Checked in"


def test_duplicate_check_in_is_rejected_409():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)
    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    response = client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_CHECKED_IN"


def test_check_out_without_check_in_is_rejected_400():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.post("/api/v1/attendance/check-out", _in_geofence_payload(), format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NOT_CHECKED_IN_YET"


def test_full_check_in_check_out_cycle():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)
    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    response = client.post("/api/v1/attendance/check-out", _in_geofence_payload(), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["check_out_time"] is not None
    assert body["working_minutes"] >= 0

    # A second check-out is rejected.
    second = client.post("/api/v1/attendance/check-out", _in_geofence_payload(), format="json")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_CHECKED_OUT"


def test_check_in_outside_geofence_is_denied():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.post(
        "/api/v1/attendance/check-in",
        _in_geofence_payload(latitude=BRANCH_LAT + 5, longitude=BRANCH_LON + 5),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "OUTSIDE_GEOFENCE"
    assert Attendance.objects.all_tenants().count() == 0


def test_check_in_poor_accuracy_is_denied():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.post(
        "/api/v1/attendance/check-in", _in_geofence_payload(accuracy=500), format="json"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "POOR_GPS_ACCURACY"


def test_check_in_mock_location_is_denied_and_logs_security_event():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.post(
        "/api/v1/attendance/check-in",
        _in_geofence_payload(is_mock_location=True),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MOCK_LOCATION_DETECTED"
    assert Attendance.objects.all_tenants().count() == 0

    event = SecurityEvent.objects.all_tenants().get()
    assert event.event_type == SecurityEventType.MOCK_LOCATION_DETECTED
    assert event.user_id == user.id


def test_check_in_without_assigned_branch_is_denied():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    EmployeeFactory(user=user, branch=None)
    client = _client_as(user)

    response = client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_BRANCH_ASSIGNED"


def test_org_admin_without_employee_profile_cannot_check_in():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    assert response.status_code == 403


def test_today_endpoint_returns_null_before_check_in_and_record_after():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    before = client.get("/api/v1/attendance/today")
    assert before.status_code == 204

    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    after = client.get("/api/v1/attendance/today")
    assert after.json()["status"] == "PRESENT"


def test_history_endpoint_returns_only_own_records():
    user, employee, branch = _employee_with_branch()
    other_user, other_employee, other_branch = _employee_with_branch()
    client = _client_as(user)
    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")
    other_client = _client_as(other_user)
    other_client.post(
        "/api/v1/attendance/check-in",
        _in_geofence_payload(latitude=other_branch.latitude, longitude=other_branch.longitude),
        format="json",
    )

    response = client.get("/api/v1/attendance/history")

    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["employee_id"] == str(employee.id)


def test_org_admin_and_manager_can_list_scoped_attendance():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)
    client.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    admin = UserAccountFactory(
        password=PASSWORD, role=Role.ORG_ADMIN, organization=user.organization
    )
    admin_client = _client_as(admin)
    response = admin_client.get("/api/v1/attendance")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_manager_only_sees_attendance_of_assigned_employees():
    user, employee, branch = _employee_with_branch()
    manager_user = UserAccountFactory(
        password=PASSWORD, role=Role.MANAGER, organization=user.organization
    )
    manager_employee = EmployeeFactory(user=manager_user)
    ManagerAssignmentFactory(manager=manager_employee, employee=employee)

    client_in_scope = _client_as(user)
    client_in_scope.post("/api/v1/attendance/check-in", _in_geofence_payload(), format="json")

    out_of_scope_user = UserAccountFactory(
        password=PASSWORD, role=Role.EMPLOYEE, organization=user.organization
    )
    out_of_scope_branch = BranchFactory(
        organization=user.organization,
        latitude=str(BRANCH_LAT + 1),
        longitude=str(BRANCH_LON + 1),
        radius_meters=100,
        gps_accuracy_limit_meters=50,
    )
    EmployeeFactory(user=out_of_scope_user, branch=out_of_scope_branch)
    out_of_scope_client = _client_as(out_of_scope_user)
    out_of_scope_client.post(
        "/api/v1/attendance/check-in",
        _in_geofence_payload(
            latitude=out_of_scope_branch.latitude, longitude=out_of_scope_branch.longitude
        ),
        format="json",
    )

    manager_client = _client_as(manager_user)
    response = manager_client.get("/api/v1/attendance")

    results = response.json()["results"]
    assert {row["employee_id"] for row in results} == {str(employee.id)}


def test_employee_cannot_list_admin_attendance_view():
    user, employee, branch = _employee_with_branch()
    client = _client_as(user)

    response = client.get("/api/v1/attendance")

    assert response.status_code == 403


def test_late_check_in_status_end_to_end():
    """Confirms the shift/AttendanceRule -> domain rules wiring end-to-end
    (the arithmetic itself is exhaustively covered by
    apps/attendance/tests/test_rules.py's unit tests).

    Builds the employee with its shift already assigned at creation
    (rather than assigning it afterwards via `employee.save()`) — mutating
    an existing tenant-scoped row's field outside of a request that has
    bound `app.current_org_id` hits Postgres RLS's UPDATE-requires-
    SELECT-visibility rule and fails closed, same as any other unbound
    write; the fix isn't to work around RLS in the test; it's to build
    the fixture the way `EmployeeFactory` already supports.
    """
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    branch = BranchFactory(
        organization=user.organization,
        latitude=str(BRANCH_LAT),
        longitude=str(BRANCH_LON),
        radius_meters=100,
        gps_accuracy_limit_meters=50,
    )
    shift = ShiftFactory(
        organization=user.organization,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(17, 0),
    )
    EmployeeFactory(user=user, branch=branch, shift=shift)
    AttendanceRule.objects.all_tenants().create(
        organization=user.organization, late_threshold_minutes=0
    )

    frozen_now = datetime.datetime(2026, 8, 3, 8, 10, tzinfo=datetime.timezone.utc)
    client = _client_as(user)

    with patch("apps.attendance.application.services.timezone.now", return_value=frozen_now):
        response = client.post(
            "/api/v1/attendance/check-in", _in_geofence_payload(), format="json"
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "LATE"
    assert body["late_minutes"] == 10
