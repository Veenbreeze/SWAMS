from django.contrib import admin

from apps.security.models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "organization", "user", "created_at")
    list_filter = ("event_type",)
    search_fields = ("description", "user__email")
    readonly_fields = [f.name for f in SecurityEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return SecurityEvent.objects.all_tenants()
