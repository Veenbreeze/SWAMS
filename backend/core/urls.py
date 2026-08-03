from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/platform/", include("apps.organizations.urls")),
    path("api/v1/", include("apps.locations.urls")),
    path("api/v1/", include("apps.attendance.urls")),
    path("api/v1/", include("apps.employees.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.leave.urls")),
    # Further domain app routes are mounted here as each is built.
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
