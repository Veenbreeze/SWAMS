"""Local development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

if not env.list("DJANGO_ALLOWED_HOSTS", default=[]):
    # The LAN IP is here so a physical phone running Expo Go (which can't
    # resolve "localhost" as this machine) can reach the dev server over
    # the same WiFi network — see mobile/.env's EXPO_PUBLIC_API_BASE_URL.
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.14"]

if not env.list("CORS_ALLOWED_ORIGINS", default=[]):
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",  # frontend-org-admin
        "http://localhost:5175",  # frontend-super-admin
    ]
    # Vite bumps to the next free port (5174, 5176, ...) whenever a prior
    # dev server is still holding the default one — a fixed port list here
    # means CORS breaks every time that happens. Local-only: staging/
    # production still require an explicit CORS_ALLOWED_ORIGINS with no
    # regex fallback.
    CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://localhost:\d+$"]

# Lets storage.local_dev issue upload/download URLs a physical phone on
# the same WiFi network can actually reach — same LAN IP as
# mobile/.env's EXPO_PUBLIC_API_BASE_URL, not "localhost".
LOCAL_DEV_PUBLIC_BASE_URL = env("LOCAL_DEV_PUBLIC_BASE_URL", default="http://192.168.1.14:8000")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Local dev/tests don't require a running Celery worker + Redis broker —
# tasks (report exports) execute synchronously in-process instead. Staging/
# production leave this at Celery's real-async default.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = True

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]

