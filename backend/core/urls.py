from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.health import health
from storage.local_dev_views import local_storage_upload

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/", include("apps.authentication.urls")),
    path("api/v1/platform/", include("apps.organizations.urls")),
    path("api/v1/platform/", include("apps.subscriptions.urls")),
    path("api/v1/platform/", include("apps.audit_logs.urls")),
    path("api/v1/platform/", include("apps.security.urls")),
    path("api/v1/platform/", include("apps.platform_settings.urls")),
    path("api/v1/", include("apps.locations.urls")),
    path("api/v1/", include("apps.attendance.urls")),
    path("api/v1/", include("apps.employees.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.leave.urls")),
    path("api/v1/", include("apps.feedback.urls")),
    # Local-dev Supabase-Storage stand-in (see storage/local_dev.py) —
    # registered unconditionally so it's routable in tests, where
    # pytest-django forces settings.DEBUG False for the whole session
    # regardless of core.settings.local's own DEBUG=True; the view itself
    # is the real gate, checking settings.DEBUG per-request and 404ing
    # outside it (i.e. always, in an actual production process).
    path(
        "api/v1/dev/local-storage/<str:bucket>/<path:path>",
        local_storage_upload,
        name="dev-local-storage-upload",
    ),
    # Further domain app routes are mounted here as each is built.
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
