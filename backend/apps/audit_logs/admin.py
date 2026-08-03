from django.contrib import admin

from apps.audit_logs.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "organization", "user", "timestamp")
    list_filter = ("organization",)
    search_fields = ("action", "description", "user__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return AuditLog.objects.all_tenants()
