from django.urls import path

from apps.reports import dashboard_views, views

urlpatterns = [
    path(
        "dashboard/org-admin",
        dashboard_views.OrgAdminDashboardView.as_view(),
        name="dashboard-org-admin",
    ),
    path(
        "dashboard/employee",
        dashboard_views.EmployeeDashboardView.as_view(),
        name="dashboard-employee",
    ),
    path(
        "dashboard/super-admin",
        dashboard_views.SuperAdminDashboardView.as_view(),
        name="dashboard-super-admin",
    ),
    path("reports/daily", views.DailyReportView.as_view(), name="report-daily"),
    path("reports/weekly", views.WeeklyReportView.as_view(), name="report-weekly"),
    path("reports/monthly", views.MonthlyReportView.as_view(), name="report-monthly"),
    path("reports/employee/<uuid:pk>", views.EmployeeReportView.as_view(), name="report-employee"),
    path(
        "reports/department/<uuid:pk>",
        views.DepartmentReportView.as_view(),
        name="report-department",
    ),
    path("reports/late", views.LateReportView.as_view(), name="report-late"),
    path("reports/overtime", views.OvertimeReportView.as_view(), name="report-overtime"),
    path(
        "reports/jobs/<uuid:job_id>",
        views.ReportExportJobStatusView.as_view(),
        name="report-export-job-status",
    ),
    path(
        "reports/<str:report_type>/export",
        views.ReportExportView.as_view(),
        name="report-export",
    ),
]
