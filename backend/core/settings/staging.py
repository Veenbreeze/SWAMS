"""Staging settings — production-like security, points at the staging
Supabase project. All values come from Render's staging environment vars."""

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
