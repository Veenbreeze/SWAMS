from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.authentication.models import UserAccount


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
