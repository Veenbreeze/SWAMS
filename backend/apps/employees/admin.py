from django.contrib import admin

from apps.employees.models import Department, Employee, ManagerAssignment


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "parent_department")
    search_fields = ("name", "organization__code", "organization__name")

    def get_queryset(self, request):
        return Department.objects.all_tenants()


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number",
        "first_name",
        "last_name",
        "organization",
        "department",
        "branch",
        "employment_status",
    )
    list_filter = ("employment_status",)
    search_fields = ("employee_number", "first_name", "last_name", "user__email")

    def get_queryset(self, request):
        return Employee.objects.all_tenants()


@admin.register(ManagerAssignment)
class ManagerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("manager", "department", "employee", "organization")

    def get_queryset(self, request):
        return ManagerAssignment.objects.all_tenants()
