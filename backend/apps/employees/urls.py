from django.urls import path

from apps.employees import views

urlpatterns = [
    path("departments", views.DepartmentListCreateView.as_view(), name="departments"),
    path("departments/<uuid:pk>", views.DepartmentDetailView.as_view(), name="department-detail"),
    path("employees", views.EmployeeListCreateView.as_view(), name="employees"),
    path("employees/<uuid:pk>", views.EmployeeDetailView.as_view(), name="employee-detail"),
    path(
        "employees/<uuid:pk>/reset-password",
        views.EmployeeResetPasswordView.as_view(),
        name="employee-reset-password",
    ),
    path(
        "employees/<uuid:pk>/profile-picture",
        views.EmployeeProfilePictureView.as_view(),
        name="employee-profile-picture",
    ),
    path(
        "manager-assignments",
        views.ManagerAssignmentListCreateView.as_view(),
        name="manager-assignments",
    ),
    path(
        "manager-assignments/<uuid:pk>",
        views.ManagerAssignmentDetailView.as_view(),
        name="manager-assignment-detail",
    ),
]
