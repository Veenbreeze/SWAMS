from django.contrib import admin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "created_at")
    search_fields = ("code", "name", "registration_number")
