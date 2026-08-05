"""Production settings — deployed on Render, DB/Storage on Supabase.

DEBUG is hardcoded False (never overridable by env var in production) and
ALLOWED_HOSTS/CORS_ALLOWED_ORIGINS/SECRET_KEY are required, not defaulted —
this environment should fail to boot rather than silently run insecurely.
"""

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")  # required, no default
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # required, no default
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")  # required, no default

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Render terminates TLS at the edge

# Defaults to real async dispatch (a separate `swams-worker`/`swams-beat`
# process consuming from REDIS_URL, per render.yaml). Only set
# CELERY_TASK_ALWAYS_EAGER=True here for a workerless deployment (e.g. a
# free-tier Render account with no paid background-worker service) — tasks
# then run synchronously in the web process itself, and scheduled/periodic
# tasks (subscription-expiry checks, report pre-generation) simply never
# fire, since there is no Beat process to trigger them regardless of this
# flag. Unset it once real worker/beat services exist.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
