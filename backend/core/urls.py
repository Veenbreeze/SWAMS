from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    # Domain app routes are mounted here as each is built, e.g.:
    # path("api/v1/auth/", include("apps.authentication.interfaces.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
