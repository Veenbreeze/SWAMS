from django.urls import path

from apps.attendance import views

urlpatterns = [
    path("shifts", views.ShiftListCreateView.as_view(), name="shifts"),
    path("shifts/<uuid:pk>", views.ShiftDetailView.as_view(), name="shift-detail"),
    path("attendance-rule", views.AttendanceRuleView.as_view(), name="attendance-rule"),
    path("attendance/check-in", views.CheckInView.as_view(), name="attendance-check-in"),
    path("attendance/check-out", views.CheckOutView.as_view(), name="attendance-check-out"),
    path("attendance/today", views.AttendanceTodayView.as_view(), name="attendance-today"),
    path("attendance/history", views.AttendanceHistoryView.as_view(), name="attendance-history"),
    path("attendance", views.AttendanceListView.as_view(), name="attendance-list"),
    path("attendance/<uuid:pk>", views.AttendanceDetailView.as_view(), name="attendance-detail"),
]
