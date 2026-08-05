from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import Role
from apps.employees import services as employee_services
from apps.employees.models import Employee
from apps.leave import services
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.leave.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestRejectSerializer,
    LeaveRequestSerializer,
    LeaveRequestUpdateSerializer,
    LeaveTypeSerializer,
    LeaveTypeWriteSerializer,
)
from core.permissions.roles import IsManagerOrAbove, IsOrgAdmin
from core.permissions.security import NotBlockedByPasswordChange

_ANY_AUTHENTICATED = [IsAuthenticated, NotBlockedByPasswordChange]
_APPROVER_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsManagerOrAbove]
_ORG_ADMIN_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]


def _employee_for(user):
    employee = getattr(user, "employee", None)
    if employee is None:
        raise PermissionDenied("Only staff with an employee profile can do this.")
    return employee


def _can_view(*, user, leave_request):
    if user.role == Role.ORG_ADMIN:
        return True
    if user.role == Role.MANAGER and employee_services.employee_in_manager_scope(
        user=user, employee=leave_request.employee
    ):
        return True
    return leave_request.employee.user_id == user.id


class LeaveTypeListView(generics.ListCreateAPIView):
    def get_queryset(self):
        return LeaveType.objects.all()

    def get_permissions(self):
        permissions = _ANY_AUTHENTICATED if self.request.method == "GET" else _ORG_ADMIN_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveTypeWriteSerializer
        return LeaveTypeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_type = services.create_leave_type(
            organization=request.user.organization,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(LeaveTypeSerializer(leave_type).data, status=201)


class LeaveTypeDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = _ORG_ADMIN_PERMISSIONS

    def get_queryset(self):
        return LeaveType.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return LeaveTypeWriteSerializer
        return LeaveTypeSerializer

    def patch(self, request, *args, **kwargs):
        leave_type = self.get_object()
        serializer = self.get_serializer(leave_type, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_leave_type(
            leave_type=leave_type,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(LeaveTypeSerializer(leave_type).data)


class LeaveRequestListCreateView(generics.ListCreateAPIView):
    permission_classes = _ANY_AUTHENTICATED
    filterset_fields = ["status", "leave_type"]

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.ORG_ADMIN:
            return LeaveRequest.objects.all()
        if user.role == Role.MANAGER:
            scoped_employees = employee_services.employees_visible_to(user=user)
            return LeaveRequest.objects.filter(employee__in=scoped_employees)
        employee = _employee_for(user)
        return LeaveRequest.objects.filter(employee=employee)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveRequestCreateSerializer
        return LeaveRequestSerializer

    def create(self, request, *args, **kwargs):
        employee = _employee_for(request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_request = services.submit_leave_request(
            employee=employee, **serializer.validated_data
        )
        return Response(LeaveRequestSerializer(leave_request).data, status=201)


class LeaveRequestDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = _ANY_AUTHENTICATED

    def get_queryset(self):
        return LeaveRequest.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return LeaveRequestUpdateSerializer
        return LeaveRequestSerializer

    def get_object(self):
        leave_request = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        if not _can_view(user=self.request.user, leave_request=leave_request):
            raise PermissionDenied("You may not access this leave request.")
        return leave_request

    def patch(self, request, *args, **kwargs):
        leave_request = self.get_object()
        if leave_request.employee.user_id != request.user.id:
            raise PermissionDenied("You may only edit your own leave request.")

        serializer = self.get_serializer(leave_request, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_leave_request(
            leave_request=leave_request, data=serializer.validated_data
        )
        return Response(LeaveRequestSerializer(leave_request).data)


class _DecisionView(APIView):
    permission_classes = _APPROVER_PERMISSIONS

    def _get_leave_request(self, request, pk):
        leave_request = generics.get_object_or_404(LeaveRequest.objects.all(), pk=pk)
        if request.user.role == Role.MANAGER and not employee_services.employee_in_manager_scope(
            user=request.user, employee=leave_request.employee
        ):
            raise PermissionDenied("This employee is outside your assigned scope.")
        return leave_request


class LeaveRequestApproveView(_DecisionView):
    def post(self, request, pk):
        leave_request = self._get_leave_request(request, pk)
        services.approve_leave_request(
            leave_request=leave_request, actor=request.user, request=request
        )
        return Response(LeaveRequestSerializer(leave_request).data)


class LeaveRequestRejectView(_DecisionView):
    def post(self, request, pk):
        leave_request = self._get_leave_request(request, pk)
        serializer = LeaveRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_leave_request(
            leave_request=leave_request,
            actor=request.user,
            reason=serializer.validated_data["reason"],
            request=request,
        )
        return Response(LeaveRequestSerializer(leave_request).data)


class LeaveBalanceView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = _ANY_AUTHENTICATED

    def get_queryset(self):
        user = self.request.user
        employee_id = self.request.query_params.get("employee_id")

        if employee_id:
            employee = generics.get_object_or_404(Employee.objects.all(), pk=employee_id)
            is_self = employee.user_id == user.id
            in_scope = user.role == Role.MANAGER and employee_services.employee_in_manager_scope(
                user=user, employee=employee
            )
            if not (user.role == Role.ORG_ADMIN or in_scope or is_self):
                raise PermissionDenied("You may not view this employee's leave balance.")
        else:
            employee = _employee_for(user)

        return LeaveBalance.objects.filter(employee=employee).order_by("-year")
