from django.urls import path

from apps.locations import views

urlpatterns = [
    path("branches", views.BranchListCreateView.as_view(), name="branches"),
    path("branches/<uuid:pk>", views.BranchDetailView.as_view(), name="branch-detail"),
    path(
        "branches/<uuid:pk>/capture-location",
        views.BranchCaptureLocationView.as_view(),
        name="branch-capture-location",
    ),
]
