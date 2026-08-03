"""Async report export — see docs/03-API-SPECIFICATION.md §11 and
docs/05-DEVELOPMENT-ROADMAP.md Phase 6.

Runs entirely outside any HTTP request, so — unlike `apps/reports/views.py`
— it must bind the tenant contextvar and Postgres RLS session itself
before touching any tenant-scoped model; see
core/tests/test_row_level_security.py and
apps/employees/tests/test_profile_picture.py for the same pattern
elsewhere. Briefly binds `WILDCARD` only to locate the job by ID (its
organization isn't known yet at that point), then immediately narrows to
that job's own organization for everything else — a bug in the report
build step still can't read another org's data.
"""

import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.employees.models import Department, Employee
from apps.reports.models import ExportFormat, ExportStatus, ReportExportJob
from apps.reports.services import aggregations, table_builder
from apps.reports.services.exporters.excel import render_table_xlsx
from apps.reports.services.exporters.pdf import render_table_pdf
from core.db import rls
from core.middleware.tenant_context import current_organization_id
from storage import supabase_client

_XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _parse_date(value):
    return datetime.date.fromisoformat(value) if value else None


def _resolve_employees(params):
    employee_ids = params.get("employee_ids")
    if employee_ids is None:
        return None
    return Employee.objects.filter(id__in=employee_ids)


def _build_title_and_table(job):
    params = job.params
    employees = _resolve_employees(params)
    start = _parse_date(params.get("start"))
    end = _parse_date(params.get("end"))

    if job.report_type == "daily":
        date = _parse_date(params["date"])
        data = aggregations.daily_summary(
            organization=job.organization, date=date, employees=employees
        )
        return f"Daily Report - {date}", *table_builder.daily_summary_table(data)

    if job.report_type == "weekly":
        data = aggregations.weekly_summary(
            organization=job.organization, start_date=start, employees=employees
        )
        return f"Weekly Report - {start}", *table_builder.range_summary_table(data)

    if job.report_type == "monthly":
        year, month = params["year"], params["month"]
        data = aggregations.monthly_summary(
            organization=job.organization, year=year, month=month, employees=employees
        )
        return f"Monthly Report - {year}-{month:02d}", *table_builder.range_summary_table(data)

    if job.report_type == "employee":
        employee = Employee.objects.all_tenants().get(pk=params["employee_id"])
        data = aggregations.employee_report(employee=employee, start_date=start, end_date=end)
        return f"Employee Report - {employee.full_name}", *table_builder.employee_report_table(data)

    if job.report_type == "department":
        department = Department.objects.all_tenants().get(pk=params["department_id"])
        data = aggregations.department_report(department=department, start_date=start, end_date=end)
        return f"Department Report - {department.name}", *table_builder.range_summary_table(data)

    if job.report_type in ("late", "overtime"):
        report_fn = (
            aggregations.late_report if job.report_type == "late" else aggregations.overtime_report
        )
        records = report_fn(
            organization=job.organization, start_date=start, end_date=end, employees=employees
        )
        return f"{job.report_type.title()} Report", *table_builder.attendance_records_table(records)

    raise ValueError(f"Unknown report_type: {job.report_type}")


@shared_task
def generate_report_export(job_id):
    rls.bind(platform_wide=True)  # job's own org isn't known until it's fetched
    job = ReportExportJob.objects.all_tenants().get(pk=job_id)

    current_organization_id.set(str(job.organization_id))
    rls.bind(organization_id=job.organization_id)
    try:
        job.status = ExportStatus.PROCESSING
        job.save(update_fields=["status"])

        title, headers, rows = _build_title_and_table(job)

        if job.format == ExportFormat.PDF:
            content = render_table_pdf(title=title, headers=headers, rows=rows)
            content_type = "application/pdf"
        else:
            content = render_table_xlsx(title=title, headers=headers, rows=rows)
            content_type = _XLSX_CONTENT_TYPE

        path = f"{job.organization_id}/reports/{job.id}.{job.format}"
        bucket = settings.SUPABASE_STORAGE_BUCKET_DOCUMENTS
        supabase_client.upload_object(
            bucket=bucket, path=path, content=content, content_type=content_type
        )
        download_url = supabase_client.create_signed_download_url(bucket=bucket, path=path)

        job.status = ExportStatus.COMPLETED
        job.file_path = path
        job.download_url = download_url
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "file_path", "download_url", "completed_at"])
    except Exception as exc:  # a failed export must land on FAILED, never stay PROCESSING forever
        job.status = ExportStatus.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
    finally:
        current_organization_id.set(None)
        rls.reset()
