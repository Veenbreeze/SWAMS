from django.urls import path

from apps.leave import views

urlpatterns = [
    path("leave/types", views.LeaveTypeListView.as_view(), name="leave-types"),
    path("leave/types/<uuid:pk>", views.LeaveTypeDetailView.as_view(), name="leave-type-detail"),
    path("leave/requests", views.LeaveRequestListCreateView.as_view(), name="leave-requests"),
    path(
        "leave/requests/<uuid:pk>",
        views.LeaveRequestDetailView.as_view(),
        name="leave-request-detail",
    ),
    path(
        "leave/requests/<uuid:pk>/approve",
        views.LeaveRequestApproveView.as_view(),
        name="leave-request-approve",
    ),
    path(
        "leave/requests/<uuid:pk>/reject",
        views.LeaveRequestRejectView.as_view(),
        name="leave-request-reject",
    ),
    path("leave/balance", views.LeaveBalanceView.as_view(), name="leave-balance"),
]
