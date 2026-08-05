from django.contrib import admin

from apps.platform_settings.models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ("maintenance_mode", "default_trial_days", "support_email", "updated_at")

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
