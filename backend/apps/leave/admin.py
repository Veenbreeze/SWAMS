from django.contrib import admin

from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "default_annual_days", "requires_approval")

    def get_queryset(self, request):
        return LeaveType.objects.all_tenants()


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status")
    list_filter = ("status",)

    def get_queryset(self, request):
        return LeaveRequest.objects.all_tenants()


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "year", "allocated_days", "used_days")

    def get_queryset(self, request):
        return LeaveBalance.objects.all_tenants()
