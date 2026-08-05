"""
Base Django settings for the SWAMS backend, shared by every environment.

Environment-specific settings (local/staging/production) import from this
module and override only what differs. Nothing here should hardcode a
secret — every sensitive or environment-dependent value is read via
django-environ from the process environment (see .env.example).
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-do-not-use-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    # organizations/authentication now carry real endpoints (Phase 2).
    # Registered ahead of that (Phase 1, schema-only) because Django
    # requires AUTH_USER_MODEL to exist before the first migration. The
    # rest are registered incrementally as each domain app is built.
    "apps.organizations",
    "apps.authentication",
    "apps.subscriptions",
    "apps.audit_logs",
    "apps.platform_settings",
    "apps.locations",
    "apps.attendance",
    "apps.employees",
    "apps.security",
    "apps.notifications",
    "apps.reports",
    "apps.leave",
    "apps.feedback",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.tenant_middleware.ResetTenantContextMiddleware",
    "core.middleware.tenant_middleware.AdminSessionRlsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# ---------------------------------------------------------------------------
# Database — Supabase PostgreSQL via DATABASE_URL, sqlite fallback for a
# bare `manage.py check`/first boot before any .env is configured.
# ---------------------------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
# Supabase's pooled connection (pgbouncer) does not support Django's
# persistent connections in transaction-pooling mode; keep this at 0
# unless the DB is accessed via Supabase's *session*-mode pooler.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=0)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "authentication.UserAccount"  # introduced in Phase 2

# UserAccount.email is unique per-organization (composite UniqueConstraint),
# not globally — by design, since two different organizations may have an
# employee with the same email (ERD §3). Django's auth.E003 check assumes
# USERNAME_FIELD needs a bare field-level unique=True; our composite +
# partial constraints enforce uniqueness correctly for our tenancy model,
# so this specific check is a deliberate, documented exception.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# DRF / JWT
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core.middleware.tenant_middleware.TenantAwareJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.security.NotBlockedByPasswordChange",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "password-reset": "5/min",
        "check-in": "30/min",
    },
    "EXCEPTION_HANDLER": "core.exceptions.uniform_exception_handler",
    # This API always returns JSON — DRF's `?format=` query-param renderer
    # override (default `URL_FORMAT_OVERRIDE = "format"`) is otherwise a
    # silent collision waiting to happen with any endpoint that legitimately
    # needs a `format` param of its own (e.g. Phase 6's
    # `POST /reports/{report}/export?format=pdf|xlsx` per
    # docs/03-API-SPECIFICATION.md §11): DRF interprets `format=pdf` as "no
    # such renderer" and raises a bare 404 with no indication why.
    "URL_FORMAT_OVERRIDE": None,
}

_JWT_ACCESS_MINUTES = env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
_JWT_REFRESH_DAYS = env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=_JWT_ACCESS_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=_JWT_REFRESH_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = False  # token auth, not cookie auth — see Architecture §6.4

# ---------------------------------------------------------------------------
# Celery / Redis
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BEAT_SCHEDULE = {
    # Daily subscription expiry sweep — see apps/subscriptions/tasks.py and
    # docs/05-DEVELOPMENT-ROADMAP.md Phase 8. Requires `celery beat` running
    # alongside the worker in staging/production; local/test settings run
    # tasks eagerly and never consult this schedule.
    "check-subscription-expiries": {
        "task": "apps.subscriptions.tasks.check_subscription_expiries",
        "schedule": crontab(hour=1, minute=0),
    },
}

# ---------------------------------------------------------------------------
# Supabase (Postgres connection above; Storage client for file uploads)
# ---------------------------------------------------------------------------

SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_SERVICE_KEY = env("SUPABASE_SERVICE_KEY", default="")
SUPABASE_STORAGE_BUCKET_PROFILE_PICTURES = env(
    "SUPABASE_BUCKET_PROFILE_PICTURES", default="profile-pictures"
)
SUPABASE_STORAGE_BUCKET_ORG_LOGOS = env("SUPABASE_BUCKET_ORG_LOGOS", default="org-logos")
SUPABASE_STORAGE_BUCKET_DOCUMENTS = env("SUPABASE_BUCKET_DOCUMENTS", default="documents")

# Backs storage.local_dev's fallback upload path, used only when Supabase
# isn't configured and DEBUG is True — see storage/local_dev.py.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# ---------------------------------------------------------------------------
# Email / SMS (see notifications app, Phase 7)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@swams.app")

# Set EMAIL_BACKEND to "core.mail.resend_backend.ResendEmailBackend" (instead
# of Django's smtp backend) on hosts that block outbound SMTP ports — e.g.
# Render's free web services, since September 2025. Until RESEND_API_KEY's
# account has a verified sending domain, Resend only delivers to the
# account owner's own address, not arbitrary recipients — fine for
# confirming the integration works, not yet real multi-user production email.
RESEND_API_KEY = env("RESEND_API_KEY", default="")

SMS_API_KEY = env("SMS_API_KEY", default="")

# ---------------------------------------------------------------------------
# Authentication (see apps/authentication/services.py)
# ---------------------------------------------------------------------------

AUTH_MAX_FAILED_ATTEMPTS = env.int("AUTH_MAX_FAILED_ATTEMPTS", default=5)
AUTH_LOCKOUT_MINUTES = env.int("AUTH_LOCKOUT_MINUTES", default=15)
# Org Admin Web's reset-password page — password reset links point here.
FRONTEND_PASSWORD_RESET_URL = env(
    "FRONTEND_PASSWORD_RESET_URL", default="http://localhost:5173/reset-password"
)

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Africa/Dar_es_Salaam")
USE_I18N = True
USE_TZ = True
LANGUAGES = [("en", "English"), ("sw", "Kiswahili")]

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Misc security defaults (tightened further in production.py)
# ---------------------------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
