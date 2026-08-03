from django.urls import path

from apps.organizations import views

urlpatterns = [
    path(
        "organizations", views.OrganizationListCreateView.as_view(), name="platform-organizations"
    ),
    path(
        "organizations/<uuid:pk>",
        views.OrganizationDetailView.as_view(),
        name="platform-organization-detail",
    ),
    path(
        "organizations/<uuid:pk>/suspend",
        views.OrganizationSuspendView.as_view(),
        name="platform-organization-suspend",
    ),
    path(
        "organizations/<uuid:pk>/activate",
        views.OrganizationActivateView.as_view(),
        name="platform-organization-activate",
    ),
]
