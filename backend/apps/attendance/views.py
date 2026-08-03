from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.application import services as attendance_services
from apps.attendance.domain import exceptions as domain_errors
from apps.attendance.models import Attendance, AttendanceRule, Shift
from apps.attendance.serializers import (
    AttendanceRuleSerializer,
    AttendanceSerializer,
    CheckRequestSerializer,
    ShiftSerializer,
    ShiftWriteSerializer,
)
from apps.authentication.models import Role
from apps.employees import services as employee_services
from core.exceptions import ApiError
from core.pagination import AttendanceHistoryCursorPagination
from core.permissions.roles import IsManagerOrAbove, IsOrgAdmin
from core.permissions.security import NotBlockedByPasswordChange

_READ_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange]
_WRITE_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]
_ADMIN_READ_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsManagerOrAbove]


def _employee_for(user):
    employee = getattr(user, "employee", None)
    if employee is None:
        raise PermissionDenied("Only staff with an employee profile can check in or out.")
    return employee


class ShiftListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        # A method, not a `queryset = ...` class attribute — see
        # apps/locations/views.py's BranchListCreateView for why a
        # TenantManager-backed queryset must be built fresh per request.
        return Shift.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ShiftWriteSerializer
        return ShiftSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ShiftDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return Shift.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ShiftWriteSerializer
        return ShiftSerializer


class AttendanceRuleView(APIView):
    """Singleton settings resource — one row per organization, created
    lazily on first access rather than requiring a bootstrap step.
    """

    permission_classes = _WRITE_PERMISSIONS

    def _get_or_create(self, request):
        rule, _ = AttendanceRule.objects.all_tenants().get_or_create(
            organization=request.user.organization
        )
        return rule

    def get(self, request):
        return Response(AttendanceRuleSerializer(self._get_or_create(request)).data)

    def patch(self, request):
        rule = self._get_or_create(request)
        serializer = AttendanceRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class _CheckView(APIView):
    """Shared plumbing for check-in/check-out — see
    docs/03-API-SPECIFICATION.md §8. Subclasses set `_service`.
    """

    permission_classes = _READ_PERMISSIONS
    throttle_scope = "check-in"
    _service = None

    def post(self, request):
        employee = _employee_for(request.user)
        serializer = CheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            attendance = self._service(
                employee=employee,
                gps=serializer.to_gps_reading(),
                device_id=serializer.validated_data["device_id"],
                request=request,
            )
        except domain_errors.AttendanceDomainError as exc:
            raise ApiError(code=exc.code, status_code=exc.status_code, message=exc.message) from exc

        return Response(AttendanceSerializer(attendance).data, status=201)


class CheckInView(_CheckView):
    _service = staticmethod(attendance_services.check_in)


class CheckOutView(_CheckView):
    _service = staticmethod(attendance_services.check_out)


class AttendanceTodayView(APIView):
    permission_classes = _READ_PERMISSIONS

    def get(self, request):
        employee = _employee_for(request.user)
        today = (
            Attendance.objects.all_tenants()
            .filter(employee=employee, attendance_date=timezone.now().date())
            .first()
        )
        if today is None:
            return Response(status=204)
        return Response(AttendanceSerializer(today).data)


class AttendanceHistoryView(generics.ListAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = _READ_PERMISSIONS
    pagination_class = AttendanceHistoryCursorPagination

    def get_queryset(self):
        employee = _employee_for(self.request.user)
        return Attendance.objects.filter(employee=employee)


class AttendanceListView(generics.ListAPIView):
    """Org Admin/Manager view — list/filter by branch/department/date/status,
    see docs/03-API-SPECIFICATION.md §8 and
    docs/05-DEVELOPMENT-ROADMAP.md Phase 5's "live attendance list" bullet.
    """

    serializer_class = AttendanceSerializer
    permission_classes = _ADMIN_READ_PERMISSIONS
    filterset_fields = ["branch", "employee__department", "attendance_date", "status"]

    def get_queryset(self):
        visible_employees = employee_services.employees_visible_to(user=self.request.user)
        return Attendance.objects.filter(employee__in=visible_employees)


class AttendanceDetailView(generics.RetrieveAPIView):
    serializer_class = AttendanceSerializer
    permission_classes = _READ_PERMISSIONS

    def get_queryset(self):
        return Attendance.objects.all()

    def get_object(self):
        attendance = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        user = self.request.user

        if user.role == Role.ORG_ADMIN:
            return attendance
        if user.role == Role.MANAGER and employee_services.employee_in_manager_scope(
            user=user, employee=attendance.employee
        ):
            return attendance
        if attendance.employee.user_id == user.id:
            return attendance

        raise PermissionDenied("You may not access this attendance record.")
