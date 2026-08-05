from rest_framework import serializers

from apps.security.models import SecurityEvent


class SecurityEventSerializer(serializers.ModelSerializer):
    organization_id = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = SecurityEvent
        fields = [
            "id",
            "organization_id",
            "organization_name",
            "user_email",
            "event_type",
            "description",
            "ip_address",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_organization_id(self, event):
        return event.organization_id

    def get_organization_name(self, event):
        return event.organization.name if event.organization_id else None

    def get_user_email(self, event):
        return event.user.email if event.user_id else None
