import datetime

from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.serializers import AttendanceSerializer
from apps.authentication.models import Role
from apps.employees import services as employee_services
from apps.employees.models import Department, Employee, ManagerAssignment
from apps.reports.models import ExportFormat, ReportExportJob
from apps.reports.serializers import (
    DepartmentReportSerializer,
    EmployeeReportTotalsSerializer,
    RangeSummarySerializer,
    ReportExportJobSerializer,
)
from apps.reports.services import aggregations
from apps.reports.tasks import generate_report_export
from core.exceptions import ApiError
from core.permissions.roles import IsManagerOrAbove
from core.permissions.security import NotBlockedByPasswordChange

_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsManagerOrAbove]
_REPORT_TYPES = {"daily", "weekly", "monthly", "employee", "department", "late", "overtime"}


def _scope_for(user):
    """`None` for Org Admin (whole org); the Manager's assigned-employees
    queryset otherwise — passed straight through to
    `apps.reports.services.aggregations`.
    """
    if user.role == Role.ORG_ADMIN:
        return None
    return employee_services.employees_visible_to(user=user)


def _parse_date(value, param_name):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(
            code="VALIDATION_ERROR",
            status_code=400,
            message=f"'{param_name}' must be an ISO date (YYYY-MM-DD).",
        ) from exc


class DailyReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request):
        date = _parse_date(request.query_params.get("date"), "date") or datetime.date.today()
        data = aggregations.daily_summary(
            organization=request.user.organization, date=date, employees=_scope_for(request.user)
        )
        return Response(data)


class WeeklyReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request):
        start = _parse_date(request.query_params.get("start"), "start")
        if start is None:
            raise ApiError(code="VALIDATION_ERROR", status_code=400, message="'start' is required.")
        data = aggregations.weekly_summary(
            organization=request.user.organization,
            start_date=start,
            employees=_scope_for(request.user),
        )
        return Response(RangeSummarySerializer(data).data)


class MonthlyReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request):
        month_param = request.query_params.get("month")
        if not month_param:
            raise ApiError(code="VALIDATION_ERROR", status_code=400, message="'month' is required.")
        try:
            year, month = (int(part) for part in month_param.split("-", 1))
        except ValueError as exc:
            raise ApiError(
                code="VALIDATION_ERROR", status_code=400, message="'month' must be YYYY-MM."
            ) from exc

        data = aggregations.monthly_summary(
            organization=request.user.organization,
            year=year,
            month=month,
            employees=_scope_for(request.user),
        )
        return Response(RangeSummarySerializer(data).data)


class EmployeeReportView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange]

    def get(self, request, pk):
        employee = get_object_or_404(Employee.objects.all(), pk=pk)
        user = request.user

        is_self = employee.user_id == user.id
        in_scope = user.role == Role.MANAGER and employee_services.employee_in_manager_scope(
            user=user, employee=employee
        )
        if not (user.role == Role.ORG_ADMIN or in_scope or is_self):
            raise PermissionDenied("You may not view this employee's report.")

        data = aggregations.employee_report(
            employee=employee,
            start_date=_parse_date(request.query_params.get("start"), "start"),
            end_date=_parse_date(request.query_params.get("end"), "end"),
        )
        data["records"] = AttendanceSerializer(data["records"], many=True).data
        return Response(
            {
                "employee_id": str(data["employee_id"]),
                "employee_name": data["employee_name"],
                "records": data["records"],
                "totals": EmployeeReportTotalsSerializer(data["totals"]).data,
            }
        )


class DepartmentReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request, pk):
        department = get_object_or_404(Department.objects.all(), pk=pk)
        user = request.user

        if user.role == Role.MANAGER:
            manager_employee = getattr(user, "employee", None)
            in_scope = manager_employee is not None and ManagerAssignment.objects.filter(
                manager=manager_employee, department=department
            ).exists()
            if not in_scope:
                raise PermissionDenied("This department is outside your assigned scope.")

        data = aggregations.department_report(
            department=department,
            start_date=_parse_date(request.query_params.get("start"), "start"),
            end_date=_parse_date(request.query_params.get("end"), "end"),
        )
        return Response(DepartmentReportSerializer(data).data)


class LateReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request):
        records = aggregations.late_report(
            organization=request.user.organization,
            start_date=_parse_date(request.query_params.get("start"), "start"),
            end_date=_parse_date(request.query_params.get("end"), "end"),
            employees=_scope_for(request.user),
        )
        return Response(AttendanceSerializer(records, many=True).data)


class OvertimeReportView(APIView):
    permission_classes = _PERMISSIONS

    def get(self, request):
        records = aggregations.overtime_report(
            organization=request.user.organization,
            start_date=_parse_date(request.query_params.get("start"), "start"),
            end_date=_parse_date(request.query_params.get("end"), "end"),
            employees=_scope_for(request.user),
        )
        return Response(AttendanceSerializer(records, many=True).data)


def _check_employee_or_department_scope(*, request, report_type, params):
    """Mirrors EmployeeReportView/DepartmentReportView's object-level
    checks — the export endpoint accepts the same identifying query params
    rather than a path segment (see docs/03-API-SPECIFICATION.md §11's
    `/reports/{report}/export` shape), so it re-derives the same scoping
    decision from them before a job is ever created.
    """
    user = request.user

    if report_type == "employee":
        employee = get_object_or_404(Employee.objects.all(), pk=params["employee_id"])
        is_self = employee.user_id == user.id
        in_scope = user.role == Role.MANAGER and employee_services.employee_in_manager_scope(
            user=user, employee=employee
        )
        if not (user.role == Role.ORG_ADMIN or in_scope or is_self):
            raise PermissionDenied("You may not export this employee's report.")

    if report_type == "department":
        department = get_object_or_404(Department.objects.all(), pk=params["department_id"])
        if user.role == Role.MANAGER:
            manager_employee = getattr(user, "employee", None)
            in_scope = manager_employee is not None and ManagerAssignment.objects.filter(
                manager=manager_employee, department=department
            ).exists()
            if not in_scope:
                raise PermissionDenied("This department is outside your assigned scope.")


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange]

    def post(self, request, report_type):
        if report_type not in _REPORT_TYPES:
            raise ApiError(
                code="VALIDATION_ERROR", status_code=400, message=f"Unknown report '{report_type}'."
            )

        export_format = request.query_params.get("format")
        if export_format not in (ExportFormat.PDF, ExportFormat.XLSX):
            raise ApiError(
                code="VALIDATION_ERROR",
                status_code=400,
                message="'format' must be 'pdf' or 'xlsx'.",
            )

        if report_type not in ("employee", "department") and not IsManagerOrAbove().has_permission(
            request, self
        ):
            raise PermissionDenied("You may not export this report.")

        params = self._build_params(request, report_type)
        _check_employee_or_department_scope(request=request, report_type=report_type, params=params)

        scope = _scope_for(request.user)
        if scope is not None:
            params["employee_ids"] = [str(pk) for pk in scope.values_list("id", flat=True)]

        job = ReportExportJob.objects.create(
            organization=request.user.organization,
            requested_by=request.user,
            report_type=report_type,
            format=export_format,
            params=params,
        )
        generate_report_export.delay(str(job.id))
        return Response({"job_id": str(job.id)}, status=202)

    def _build_params(self, request, report_type):
        query = request.query_params

        if report_type == "daily":
            date = _parse_date(query.get("date"), "date") or datetime.date.today()
            return {"date": date.isoformat()}

        if report_type == "weekly":
            start = _parse_date(query.get("start"), "start")
            if start is None:
                raise ApiError(
                    code="VALIDATION_ERROR", status_code=400, message="'start' is required."
                )
            return {"start": start.isoformat()}

        if report_type == "monthly":
            month_param = query.get("month")
            if not month_param:
                raise ApiError(
                    code="VALIDATION_ERROR", status_code=400, message="'month' is required."
                )
            try:
                year, month = (int(part) for part in month_param.split("-", 1))
            except ValueError as exc:
                raise ApiError(
                    code="VALIDATION_ERROR", status_code=400, message="'month' must be YYYY-MM."
                ) from exc
            return {"year": year, "month": month}

        if report_type == "employee":
            employee_id = query.get("employee_id")
            if not employee_id:
                raise ApiError(
                    code="VALIDATION_ERROR", status_code=400, message="'employee_id' is required."
                )
            return {
                "employee_id": employee_id,
                "start": query.get("start"),
                "end": query.get("end"),
            }

        if report_type == "department":
            department_id = query.get("department_id")
            if not department_id:
                raise ApiError(
                    code="VALIDATION_ERROR", status_code=400, message="'department_id' is required."
                )
            return {
                "department_id": department_id,
                "start": query.get("start"),
                "end": query.get("end"),
            }

        # late / overtime
        return {"start": query.get("start"), "end": query.get("end")}


class ReportExportJobStatusView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange]

    def get(self, request, job_id):
        job = get_object_or_404(ReportExportJob.objects.all(), pk=job_id)
        if job.requested_by_id != request.user.id and request.user.role != Role.ORG_ADMIN:
            raise PermissionDenied("You may not view this export job.")
        return Response(ReportExportJobSerializer(job).data)
