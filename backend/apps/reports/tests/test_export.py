import datetime
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRule, AttendanceStatus
from apps.authentication.models import Role
from apps.reports.models import ExportStatus, ReportExportJob
from core.db import rls
from tests.factories import (
    AttendanceFactory,
    DepartmentFactory,
    EmployeeFactory,
    ManagerAssignmentFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"
MONDAY = datetime.date(2026, 8, 3)


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


def _org_admin():
    return UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)


def _export(client, report_type, **params):
    # The export endpoint reads everything (`format`, `date`, `employee_id`,
    # ...) from the query string, matching docs/03-API-SPECIFICATION.md
    # §11's literal `POST /reports/{report}/export?format=pdf|xlsx` shape —
    # there is no request body.
    return client.post(f"/api/v1/reports/{report_type}/export?{urlencode(params)}")


def _get_job(job_id):
    # In eager mode the Celery task runs synchronously inside the request
    # above and resets RLS to unbound in its own `finally` block once done
    # (see apps/reports/tasks.py) — a real async worker would do the same
    # on a separate connection, invisible to the caller. Reading the job
    # back here needs its own fresh bind, same as any other direct
    # (non-request) read — see apps/security/tests/test_security_events.py
    # for the same pattern.
    rls.bind(platform_wide=True)
    try:
        return ReportExportJob.objects.all_tenants().get(pk=job_id)
    finally:
        rls.reset()


@patch("apps.reports.tasks.supabase_client.create_signed_download_url")
@patch("apps.reports.tasks.supabase_client.upload_object")
def test_daily_export_pdf_completes_synchronously_in_eager_mode(mock_upload, mock_sign):
    mock_sign.return_value = "https://storage.example/signed-download-url"
    admin = _org_admin()
    AttendanceRule.objects.all_tenants().create(
        organization=admin.organization, working_days=[0, 1, 2, 3, 4]
    )
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(employee=employee, attendance_date=MONDAY, status=AttendanceStatus.PRESENT)
    client = _client_as(admin)

    response = _export(client, "daily", format="pdf", date=str(MONDAY))

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job = _get_job(job_id)
    assert job.status == ExportStatus.COMPLETED
    assert job.download_url == "https://storage.example/signed-download-url"
    assert job.completed_at is not None

    mock_upload.assert_called_once()
    call_kwargs = mock_upload.call_args.kwargs
    assert call_kwargs["content_type"] == "application/pdf"
    assert call_kwargs["content"].startswith(b"%PDF")  # a real PDF was generated


@patch("apps.reports.tasks.supabase_client.create_signed_download_url")
@patch("apps.reports.tasks.supabase_client.upload_object")
def test_late_export_xlsx_completes(mock_upload, mock_sign):
    mock_sign.return_value = "https://storage.example/signed-download-url"
    admin = _org_admin()
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(
        employee=employee, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    client = _client_as(admin)

    response = _export(client, "late", format="xlsx")

    assert response.status_code == 202
    job = _get_job(response.json()["job_id"])
    assert job.status == ExportStatus.COMPLETED

    call_kwargs = mock_upload.call_args.kwargs
    assert call_kwargs["content_type"].endswith("spreadsheetml.sheet")
    assert call_kwargs["content"].startswith(b"PK")  # xlsx is a zip archive


def test_export_job_marked_failed_when_storage_is_not_configured():
    # No mocking — SUPABASE_URL is blank by default, so the real
    # StorageNotConfiguredError path runs end-to-end.
    admin = _org_admin()
    client = _client_as(admin)

    response = _export(client, "daily", format="pdf")

    job = _get_job(response.json()["job_id"])
    assert job.status == ExportStatus.FAILED
    assert "SUPABASE" in job.error_message.upper() or "storage" in job.error_message.lower()


def test_export_rejects_invalid_report_type():
    admin = _org_admin()
    client = _client_as(admin)

    response = _export(client, "bogus", format="pdf")

    assert response.status_code == 400


def test_export_rejects_invalid_format():
    admin = _org_admin()
    client = _client_as(admin)

    response = _export(client, "daily", format="docx")

    assert response.status_code == 400


def test_employee_cannot_export_report_for_another_employee():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    EmployeeFactory(user=user)
    other_employee = EmployeeFactory(user__organization=user.organization)
    client = _client_as(user)

    response = _export(client, "employee", format="pdf", employee_id=str(other_employee.id))

    assert response.status_code == 403


@patch("apps.reports.tasks.supabase_client.create_signed_download_url")
@patch("apps.reports.tasks.supabase_client.upload_object")
def test_employee_can_export_their_own_report(mock_upload, mock_sign):
    mock_sign.return_value = "https://storage.example/signed-download-url"
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    client = _client_as(user)

    response = _export(client, "employee", format="pdf", employee_id=str(employee.id))

    assert response.status_code == 202
    job = _get_job(response.json()["job_id"])
    assert job.status == ExportStatus.COMPLETED


@patch("apps.reports.tasks.supabase_client.create_signed_download_url")
@patch("apps.reports.tasks.supabase_client.upload_object")
def test_manager_export_is_scoped_to_assigned_employees(mock_upload, mock_sign):
    mock_sign.return_value = "https://storage.example/signed-download-url"
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    manager_employee = EmployeeFactory(user=manager_user)
    in_scope = EmployeeFactory(user__organization=manager_user.organization)
    out_of_scope = EmployeeFactory(user__organization=manager_user.organization)
    ManagerAssignmentFactory(manager=manager_employee, employee=in_scope)
    AttendanceFactory(
        employee=in_scope, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    AttendanceFactory(
        employee=out_of_scope, attendance_date=MONDAY, status=AttendanceStatus.LATE, late_minutes=5
    )
    client = _client_as(manager_user)

    response = _export(client, "late", format="pdf")
    job = _get_job(response.json()["job_id"])

    assert job.params["employee_ids"] == [str(in_scope.id)]


def test_job_status_endpoint_requires_requester_or_org_admin():
    admin = _org_admin()
    other_user = UserAccountFactory(password=PASSWORD, organization=admin.organization)
    EmployeeFactory(user=other_user)
    client = _client_as(admin)

    response = _export(client, "daily", format="pdf")
    job_id = response.json()["job_id"]

    other_client = _client_as(other_user)
    denied = other_client.get(f"/api/v1/reports/jobs/{job_id}")
    assert denied.status_code == 403

    admin_client = _client_as(admin)
    allowed = admin_client.get(f"/api/v1/reports/jobs/{job_id}")
    assert allowed.status_code == 200
    assert allowed.json()["job_id"] == job_id


def test_department_report_export_requires_manager_scope():
    manager_user = UserAccountFactory(password=PASSWORD, role=Role.MANAGER)
    EmployeeFactory(user=manager_user)
    department = DepartmentFactory(organization=manager_user.organization)
    client = _client_as(manager_user)

    response = _export(client, "department", format="pdf", department_id=str(department.id))

    assert response.status_code == 403
