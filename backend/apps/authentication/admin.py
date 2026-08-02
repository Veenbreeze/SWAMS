from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.authentication.models import Device, LoginHistory, UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(UserAdmin):
    model = UserAccount
    ordering = ("email",)
    list_display = ("email", "organization", "role", "is_active", "must_change_password")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("email", "employee_number")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Tenant & Role", {"fields": ("organization", "role", "employee_number")}),
        (
            "Security",
            {"fields": ("must_change_password", "failed_login_attempts", "locked_until")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "organization", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("identifier_used", "organization", "was_successful", "ip_address", "created_at")
    list_filter = ("was_successful", "organization")
    search_fields = ("identifier_used", "ip_address")
    readonly_fields = [f.name for f in LoginHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "platform", "last_seen_at")
    search_fields = ("user__email", "device_id", "device_name")
