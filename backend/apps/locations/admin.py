from django.contrib import admin

from apps.locations.models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "radius_meters", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "organization__code", "organization__name")

    def get_queryset(self, request):
        return Branch.objects.all_tenants()
