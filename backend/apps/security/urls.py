from django.urls import path

from apps.security import views

urlpatterns = [
    path("security-events", views.SecurityEventListView.as_view(), name="platform-security-events"),
]
