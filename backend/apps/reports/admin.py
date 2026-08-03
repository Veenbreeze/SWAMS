from django.contrib import admin

from apps.reports.models import ReportExportJob


@admin.register(ReportExportJob)
class ReportExportJobAdmin(admin.ModelAdmin):
    list_display = ("report_type", "format", "status", "organization", "requested_by", "created_at")
    list_filter = ("report_type", "format", "status")

    def get_queryset(self, request):
        return ReportExportJob.objects.all_tenants()
