from django.urls import path

from apps.notifications import views

urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/<uuid:pk>/read",
        views.NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "notifications/read-all",
        views.NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
]
