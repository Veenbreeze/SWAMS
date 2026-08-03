from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import Role
from apps.employees import services
from apps.employees.models import Department, Employee, ManagerAssignment
from apps.employees.serializers import (
    DepartmentSerializer,
    DepartmentWriteSerializer,
    EmployeeCreateResponseSerializer,
    EmployeeCreateSerializer,
    EmployeeSelfUpdateSerializer,
    EmployeeSerializer,
    EmployeeUpdateSerializer,
    ManagerAssignmentSerializer,
    ProfilePictureRequestSerializer,
    ProfilePictureResponseSerializer,
)
from core.permissions.roles import IsManagerOrAbove, IsOrgAdmin
from core.permissions.security import NotBlockedByPasswordChange

_READ_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsManagerOrAbove]
_WRITE_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]
_ANY_AUTHENTICATED = [IsAuthenticated, NotBlockedByPasswordChange]


# --- Departments --------------------------------------------------------------


class DepartmentListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        # A method, not a `queryset = ...` class attribute — see
        # apps/locations/views.py's BranchListCreateView for why a
        # TenantManager-backed queryset must be built fresh per request.
        return Department.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DepartmentWriteSerializer
        return DepartmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = services.create_department(
            organization=request.user.organization,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(DepartmentSerializer(department).data, status=201)


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return Department.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return DepartmentWriteSerializer
        return DepartmentSerializer

    def patch(self, request, *args, **kwargs):
        department = self.get_object()
        serializer = self.get_serializer(department, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_department(
            department=department,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(DepartmentSerializer(department).data)

    def perform_destroy(self, instance):
        services.delete_department(
            department=instance, actor=self.request.user, request=self.request
        )


# --- Employees ------------------------------------------------------------------


class EmployeeListCreateView(generics.ListCreateAPIView):
    filterset_fields = ["employment_status", "department", "branch"]

    def get_queryset(self):
        return services.employees_visible_to(user=self.request.user)

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EmployeeCreateSerializer
        return EmployeeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee, temporary_password = services.create_employee(
            organization=request.user.organization,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        response = EmployeeCreateResponseSerializer(
            {"employee": employee, "temporary_password": temporary_password}
        )
        return Response(response.data, status=201)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    # Broadest permitted queryset for the role; object-level scoping (self,
    # Manager assignment) is enforced in get_object() below, matching
    # docs/01-SYSTEM-ARCHITECTURE.md §5's "object-level check" layer.
    permission_classes = _ANY_AUTHENTICATED

    def get_queryset(self):
        return Employee.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            if self.request.user.role == Role.ORG_ADMIN:
                return EmployeeUpdateSerializer
            return EmployeeSelfUpdateSerializer
        return EmployeeSerializer

    def get_object(self):
        employee = generics.get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        user = self.request.user
        in_manager_scope = user.role == Role.MANAGER and services.employee_in_manager_scope(
            user=user, employee=employee
        )

        if user.role == Role.ORG_ADMIN:
            return employee
        if in_manager_scope:
            return employee
        if employee.user_id == user.id:
            return employee

        raise PermissionDenied("You may not access this employee record.")

    def patch(self, request, *args, **kwargs):
        employee = self.get_object()
        user = request.user
        if user.role != Role.ORG_ADMIN and employee.user_id != user.id:
            raise PermissionDenied("You may only update your own record.")

        serializer = self.get_serializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_employee(
            employee=employee, data=serializer.validated_data, actor=user, request=request
        )
        return Response(EmployeeSerializer(employee).data)

    def perform_destroy(self, instance):
        if self.request.user.role != Role.ORG_ADMIN:
            raise PermissionDenied("Only an Org Admin may remove an employee.")
        services.terminate_employee(
            employee=instance, actor=self.request.user, request=self.request
        )

    def destroy(self, request, *args, **kwargs):
        # Soft delete: return the updated record, not 204, since the row
        # still exists (employment_status=TERMINATED).
        employee = self.get_object()
        self.perform_destroy(employee)
        return Response(EmployeeSerializer(employee).data)


class EmployeeResetPasswordView(APIView):
    permission_classes = _WRITE_PERMISSIONS

    def post(self, request, pk):
        employee = generics.get_object_or_404(Employee.objects.all(), pk=pk)
        temporary_password = services.reset_employee_password(
            employee=employee, actor=request.user, request=request
        )
        return Response({"temporary_password": temporary_password})


class EmployeeProfilePictureView(APIView):
    permission_classes = _ANY_AUTHENTICATED

    def post(self, request, pk):
        employee = generics.get_object_or_404(Employee.objects.all(), pk=pk)
        user = request.user
        if user.role != Role.ORG_ADMIN and employee.user_id != user.id:
            raise PermissionDenied("You may only upload your own profile picture.")

        serializer = ProfilePictureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload_url, profile_picture_url = services.request_profile_picture_upload(
            employee=employee,
            content_type=serializer.validated_data["content_type"],
            actor=user,
            request=request,
        )
        response = ProfilePictureResponseSerializer(
            {"upload_url": upload_url, "profile_picture_url": profile_picture_url}
        )
        return Response(response.data)


# --- Manager assignments --------------------------------------------------------
# Not itemized in docs/03-API-SPECIFICATION.md's endpoint tables, but the
# capability is a named Phase 4 deliverable ("Manager scoping") — Org Admin
# needs a reachable way to create these rows beyond the Django admin.


class ManagerAssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ManagerAssignmentSerializer
    permission_classes = _WRITE_PERMISSIONS

    def get_queryset(self):
        return ManagerAssignment.objects.all()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ManagerAssignmentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ManagerAssignmentSerializer
    permission_classes = _WRITE_PERMISSIONS

    def get_queryset(self):
        return ManagerAssignment.objects.all()
