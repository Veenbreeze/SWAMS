from rest_framework import serializers

from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "name", "default_annual_days", "requires_approval"]
        read_only_fields = fields


class LeaveTypeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["name", "default_annual_days", "requires_approval"]
        extra_kwargs = {
            "default_annual_days": {"required": False},
            "requires_approval": {"required": False},
        }


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source="employee.id", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_id = serializers.UUIDField(source="leave_type.id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    days_requested = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_id",
            "employee_name",
            "leave_type_id",
            "leave_type_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "decision_reason",
            "days_requested",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    # Bare manager (`LeaveType.objects`), not `.objects.all()` — a
    # QuerySet built here would be fixed at import time, before any
    # request ever binds the tenant contextvar. See
    # apps/employees/serializers.py's EmployeeCreateSerializer for the
    # same fix applied to this exact class of bug.
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects)

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]
        extra_kwargs = {"reason": {"required": False}}


class LeaveRequestUpdateSerializer(serializers.ModelSerializer):
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects, required=False)

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]
        extra_kwargs = {field: {"required": False} for field in fields}


class LeaveRequestRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_id = serializers.UUIDField(source="leave_type.id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "leave_type_id",
            "leave_type_name",
            "year",
            "allocated_days",
            "used_days",
            "remaining_days",
        ]
        read_only_fields = fields
