from django.utils import timezone
from rest_framework import serializers

from apps.attendance.domain.entities import GpsReading
from apps.attendance.models import Attendance, AttendanceRule, Shift

# Beyond this, a device's clock is considered too unreliable to trust for
# anything — see docs/01-SYSTEM-ARCHITECTURE.md §6.4 ("timestamps can't be
# in the future beyond clock-skew tolerance"). Purely a sanity check on the
# client-supplied `client_timestamp`; the persisted check-in/out time is
# always the server's own clock (see application/services.py's docstring).
_MAX_CLOCK_SKEW_SECONDS = 300


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["id", "name", "start_time", "end_time", "crosses_midnight", "created_at"]
        read_only_fields = ["id", "created_at"]


class ShiftWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ["name", "start_time", "end_time", "crosses_midnight"]
        extra_kwargs = {field: {"required": False} for field in ["crosses_midnight"]}


class AttendanceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRule
        fields = [
            "id",
            "working_days",
            "late_threshold_minutes",
            "early_departure_threshold_minutes",
            "overtime_threshold_minutes",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate_working_days(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("working_days must be a non-empty list.")
        if any(not isinstance(day, int) or day < 0 or day > 6 for day in value):
            raise serializers.ValidationError(
                "Each working day must be an integer 0 (Monday) through 6 (Sunday)."
            )
        return sorted(set(value))


class CheckRequestSerializer(serializers.Serializer):
    """Shared payload shape for both check-in and check-out — see
    docs/03-API-SPECIFICATION.md §8.
    """

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.FloatField(min_value=0)
    device_id = serializers.CharField(required=False, allow_blank=True, default="")
    is_mock_location = serializers.BooleanField(required=False, default=False)
    client_timestamp = serializers.DateTimeField(required=False, allow_null=True)

    def validate_client_timestamp(self, value):
        if value is None:
            return value
        skew_seconds = abs((timezone.now() - value).total_seconds())
        if skew_seconds > _MAX_CLOCK_SKEW_SECONDS:
            raise serializers.ValidationError(
                "Device clock is too far out of sync with the server."
            )
        return value

    def to_gps_reading(self):
        data = self.validated_data
        return GpsReading(
            latitude=data["latitude"],
            longitude=data["longitude"],
            accuracy=data["accuracy"],
            is_mock_location=data["is_mock_location"],
        )


class AttendanceSerializer(serializers.ModelSerializer):
    employee_id = serializers.UUIDField(source="employee.id", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    branch = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee_id",
            "employee_name",
            "branch",
            "attendance_date",
            "check_in_time",
            "check_out_time",
            "status",
            "working_minutes",
            "late_minutes",
            "early_departure_minutes",
            "overtime_minutes",
        ]
        read_only_fields = fields

    def get_branch(self, attendance):
        if not attendance.branch_id:
            return None
        return {"id": str(attendance.branch_id), "name": attendance.branch.name}
