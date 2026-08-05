from rest_framework import serializers

from apps.platform_settings.models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ["maintenance_mode", "default_trial_days", "support_email", "updated_at"]
        read_only_fields = ["updated_at"]
