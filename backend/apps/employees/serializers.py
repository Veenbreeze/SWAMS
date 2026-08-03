from rest_framework import serializers

from apps.attendance.models import Shift
from apps.authentication.models import Role
from apps.employees.models import Department, Employee, ManagerAssignment
from apps.locations.models import Branch

# Org Admin issues accounts for their own staff only — SUPER_ADMIN/ORG_ADMIN
# are never assignable through this endpoint (creating another Org Admin is
# a Super Admin platform action, not a same-org self-service one).
_ASSIGNABLE_ROLES = [Role.MANAGER, Role.EMPLOYEE]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "parent_department", "created_at"]
        read_only_fields = ["id", "created_at"]


class DepartmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["name", "parent_department"]
        extra_kwargs = {"parent_department": {"required": False, "allow_null": True}}


class EmployeeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "email",
            "role",
            "employee_number",
            "first_name",
            "last_name",
            "phone",
            "profile_picture_url",
            "department",
            "branch",
            "shift",
            "position",
            "joining_date",
            "employment_status",
            "created_at",
        ]
        read_only_fields = ["id", "employment_status", "created_at"]


class EmployeeCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    role = serializers.ChoiceField(
        choices=_ASSIGNABLE_ROLES, default=Role.EMPLOYEE, write_only=True
    )
    # `queryset=Department.objects` (the manager), not `.objects.all()` (a
    # QuerySet): a QuerySet built here would be constructed once at class
    # -body/import time, before any request ever binds the tenant
    # contextvar, permanently baking in TenantManager's `.none()`. A bare
    # manager defers `.get_queryset()` until validation actually runs
    # per-request — the same lazy pattern ModelSerializer's own
    # auto-generated relational fields use internally (`_default_manager`).
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects, required=False, allow_null=True
    )
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects, required=False, allow_null=True
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects, required=False, allow_null=True
    )

    class Meta:
        model = Employee
        fields = [
            "email",
            "role",
            "employee_number",
            "first_name",
            "last_name",
            "phone",
            "department",
            "branch",
            "shift",
            "position",
            "joining_date",
        ]


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """Org Admin's full-field PATCH — see docs/03-API-SPECIFICATION.md §7."""

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects, required=False, allow_null=True
    )
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects, required=False, allow_null=True
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects, required=False, allow_null=True
    )

    class Meta:
        model = Employee
        fields = [
            "employee_number",
            "first_name",
            "last_name",
            "phone",
            "department",
            "branch",
            "shift",
            "position",
            "joining_date",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class EmployeeSelfUpdateSerializer(serializers.ModelSerializer):
    """Self-service PATCH — deliberately excludes `role`, `department`,
    `branch`, `employee_number`, `organization` per
    docs/01-SYSTEM-ARCHITECTURE.md §5's field-level RBAC example: an
    employee can update their own contact info, never their own scope.
    """

    class Meta:
        model = Employee
        fields = ["phone"]
        extra_kwargs = {"phone": {"required": False}}


class EmployeeCreateResponseSerializer(serializers.Serializer):
    employee = EmployeeSerializer()
    temporary_password = serializers.CharField()


class ManagerAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerAssignment
        fields = ["id", "manager", "department", "employee", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        department = attrs.get("department") or getattr(self.instance, "department", None)
        employee = attrs.get("employee") or getattr(self.instance, "employee", None)
        if not department and not employee:
            raise serializers.ValidationError(
                "A manager assignment needs a department, an employee, or both."
            )
        return attrs


class ProfilePictureRequestSerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=["image/jpeg", "image/png", "image/webp"])
    file_size = serializers.IntegerField(min_value=1, max_value=5 * 1024 * 1024)


class ProfilePictureResponseSerializer(serializers.Serializer):
    upload_url = serializers.CharField()
    profile_picture_url = serializers.CharField()
