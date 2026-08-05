from rest_framework import serializers

from apps.audit_logs.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    organization_id = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "organization_id",
            "organization_name",
            "user_email",
            "action",
            "description",
            "ip_address",
            "device_info",
            "timestamp",
        ]
        read_only_fields = fields

    def get_organization_id(self, log):
        return log.organization_id

    def get_organization_name(self, log):
        return log.organization.name if log.organization_id else None

    def get_user_email(self, log):
        return log.user.email if log.user_id else None
