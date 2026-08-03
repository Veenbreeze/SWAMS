from django.contrib import admin

from apps.attendance.models import Attendance, AttendanceRule, Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "start_time", "end_time", "crosses_midnight")
    search_fields = ("name", "organization__code", "organization__name")

    def get_queryset(self, request):
        return Shift.objects.all_tenants()


@admin.register(AttendanceRule)
class AttendanceRuleAdmin(admin.ModelAdmin):
    list_display = ("organization", "late_threshold_minutes", "overtime_threshold_minutes")

    def get_queryset(self, request):
        return AttendanceRule.objects.all_tenants()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "attendance_date", "status", "check_in_time", "check_out_time")
    list_filter = ("status",)
    search_fields = ("employee__employee_number", "employee__first_name", "employee__last_name")

    def get_queryset(self, request):
        return Attendance.objects.all_tenants()
