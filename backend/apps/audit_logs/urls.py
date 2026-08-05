from django.urls import path

from apps.audit_logs import views

urlpatterns = [
    path("audit-logs", views.AuditLogListView.as_view(), name="platform-audit-logs"),
]
