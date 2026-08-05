from django.urls import path

from apps.platform_settings import views

urlpatterns = [
    path("settings", views.PlatformSettingsView.as_view(), name="platform-settings"),
]
