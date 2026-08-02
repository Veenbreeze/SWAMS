"""Local development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

if not env.list("DJANGO_ALLOWED_HOSTS", default=[]):
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

if not env.list("CORS_ALLOWED_ORIGINS", default=[]):
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",  # frontend-org-admin
        "http://localhost:5175",  # frontend-super-admin
    ]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]

