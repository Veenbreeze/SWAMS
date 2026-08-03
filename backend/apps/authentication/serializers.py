from rest_framework import serializers

from apps.authentication.models import UserAccount


class UserSummarySerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(read_only=True, allow_null=True)
    employee = serializers.SerializerMethodField()

    class Meta:
        model = UserAccount
        fields = ["id", "email", "employee_number", "role", "organization_id", "employee"]
        read_only_fields = fields

    def get_employee(self, user):
        # Local import: apps.employees didn't exist when this serializer
        # was first written (Phase 2, before Phase 4's Employee model), and
        # apps.employees.serializers imports from apps.locations/attendance
        # models — importing at module level here risks a circular import
        # the moment any of those apps import something auth-adjacent.
        from apps.employees.serializers import EmployeeSerializer

        employee = getattr(user, "employee", None)
        if employee is None:
            return None
        return EmployeeSerializer(employee).data


class LoginSerializer(serializers.Serializer):
    organization_code = serializers.CharField(required=False, allow_blank=True, default="")
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField(required=False, allow_blank=True, default="")
    device_name = serializers.CharField(required=False, allow_blank=True, default="")
    platform = serializers.CharField(required=False, allow_blank=True, default="")


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    organization_code = serializers.CharField(required=False, allow_blank=True, default="")
    identifier = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
