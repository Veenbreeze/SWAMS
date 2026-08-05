"""Authentication business logic — kept out of views/serializers so it is
testable without going through the DRF request/response cycle (see
docs/04-PROJECT-STRUCTURE.md's note on why `authentication` gets a service
layer even without full domain/application/infrastructure folders).
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken as SimpleJWTRefreshToken

from apps.authentication.models import Device, LoginHistory, Role, UserAccount
from apps.organizations.models import Organization, OrganizationStatus
from core.db import rls
from core.exceptions import ApiError
from core.validation import validate_password_strength
from storage import local_dev, supabase_client

# Local copy, not an import from apps.employees.services — that module
# imports apps.authentication.models, so importing back from it here would
# be a circular import (same reasoning as UserSummarySerializer.get_employee's
# local import, just at module scope instead).
_PROFILE_PICTURE_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class StorageUnavailableError(ApiError):
    code = "STORAGE_NOT_CONFIGURED"
    status_code = 503
    default_message = "File storage is not configured for this environment."


def _max_failed_attempts():
    # Read from settings at call time, not import time — settings.py values
    # (and test overrides via pytest-django's `settings` fixture) must be
    # honored per-request, not frozen at first import.
    return getattr(settings, "AUTH_MAX_FAILED_ATTEMPTS", 5)


def _lockout_duration():
    return timedelta(minutes=getattr(settings, "AUTH_LOCKOUT_MINUTES", 15))

password_reset_token_generator = PasswordResetTokenGenerator()


class InvalidCredentialsError(ApiError):
    code = "INVALID_CREDENTIALS"
    status_code = 401
    default_message = "Invalid organization code, identifier, or password."


class AccountLockedError(ApiError):
    code = "ACCOUNT_LOCKED"
    status_code = 403
    default_message = (
        "This account is temporarily locked due to too many failed sign-in attempts."
    )


class OrganizationNotFoundError(ApiError):
    code = "ORGANIZATION_NOT_FOUND"
    status_code = 404
    default_message = "No organization was found with that code."


class OrganizationSuspendedError(ApiError):
    code = "ORGANIZATION_SUSPENDED"
    status_code = 403
    default_message = "This organization's access has been suspended."


class TokenReuseDetectedError(ApiError):
    code = "TOKEN_REUSE_DETECTED"
    status_code = 401
    default_message = "This session is no longer valid. Please sign in again."


class InvalidResetTokenError(ApiError):
    code = "INVALID_RESET_TOKEN"
    status_code = 400
    default_message = "This password reset link is invalid or has expired."


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _record_login(*, organization, user, identifier, request, was_successful, failure_reason=""):
    LoginHistory.objects.create(
        organization=organization,
        user=user,
        identifier_used=identifier,
        ip_address=_client_ip(request),
        device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
        was_successful=was_successful,
        failure_reason=failure_reason,
    )


def _upsert_device(user, device_id, device_name, platform):
    if not device_id:
        return None, False
    return Device.objects.update_or_create(
        user=user,
        device_id=device_id,
        defaults={"device_name": device_name or "", "platform": platform or ""},
    )


def _notify_new_device_login(*, user, device, request):
    """New-device-login detection — see docs/03-API-SPECIFICATION.md §1
    and docs/05-DEVELOPMENT-ROADMAP.md Phase 7 ("notification to employee
    and Org Admin per brief §21"). Fires whenever `_upsert_device` just
    created a `Device` row rather than updating an existing one.
    """
    from apps.notifications.models import NotificationCategory
    from apps.notifications.services import NotificationDispatcher
    from apps.security.models import SecurityEventType
    from apps.security.services import SecurityEventLogger

    device_label = device.device_name or device.platform or "a new device"

    SecurityEventLogger.record(
        event_type=SecurityEventType.NEW_DEVICE_LOGIN,
        user=user,
        organization=user.organization,
        description=f"New device login: {device_label}.",
        request=request,
    )
    NotificationDispatcher.notify(
        user=user,
        category=NotificationCategory.SECURITY,
        title="New device signed in",
        message=f"Your account was just signed in from {device_label}.",
        send_email=True,
    )

    if not user.organization_id:
        return
    org_admins = UserAccount.objects.filter(
        organization=user.organization, role=Role.ORG_ADMIN
    ).exclude(pk=user.pk)
    for org_admin in org_admins:
        NotificationDispatcher.notify(
            user=org_admin,
            category=NotificationCategory.SECURITY,
            title="New device login",
            message=f"{user.email} signed in from {device_label}.",
            send_email=True,
        )


def _notify_password_changed(user):
    from apps.notifications.models import NotificationCategory
    from apps.notifications.services import NotificationDispatcher

    NotificationDispatcher.notify(
        user=user,
        category=NotificationCategory.SECURITY,
        title="Password changed",
        message=(
            "Your password was just changed. If this wasn't you, "
            "contact your administrator immediately."
        ),
        send_email=True,
    )


def _issue_tokens(user):
    refresh = SimpleJWTRefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["organization_id"] = str(user.organization_id) if user.organization_id else None
    return str(refresh.access_token), str(refresh)


def _find_user(organization, identifier):
    return (
        UserAccount.objects.filter(organization=organization)
        .filter(Q(email__iexact=identifier) | Q(employee_number__iexact=identifier))
        .first()
    )


def authenticate(
    *,
    organization_code,
    identifier,
    password,
    request,
    device_id=None,
    device_name=None,
    platform=None,
):
    """Resolve the org_code + identifier + password login triple.

    `organization_code` is None for Super Admin logins, which resolve only
    against platform-wide accounts (organization IS NULL) — see
    docs/03-API-SPECIFICATION.md §1.
    """
    organization = None
    if organization_code:
        organization = Organization.objects.filter(code__iexact=organization_code).first()
        if organization is None:
            _record_login(
                organization=None,
                user=None,
                identifier=identifier,
                request=request,
                was_successful=False,
                failure_reason="organization_not_found",
            )
            raise OrganizationNotFoundError()

        if organization.status == OrganizationStatus.SUSPENDED:
            _record_login(
                organization=organization,
                user=None,
                identifier=identifier,
                request=request,
                was_successful=False,
                failure_reason="organization_suspended",
            )
            raise OrganizationSuspendedError()

    user = _find_user(organization, identifier)

    if user is None or not user.is_active:
        _record_login(
            organization=organization,
            user=user,
            identifier=identifier,
            request=request,
            was_successful=False,
            failure_reason="user_not_found",
        )
        raise InvalidCredentialsError()

    if user.locked_until and user.locked_until > timezone.now():
        _record_login(
            organization=organization,
            user=user,
            identifier=identifier,
            request=request,
            was_successful=False,
            failure_reason="account_locked",
        )
        raise AccountLockedError()

    if not user.check_password(password):
        user.failed_login_attempts += 1
        just_locked = user.failed_login_attempts >= _max_failed_attempts()
        if just_locked:
            user.locked_until = timezone.now() + _lockout_duration()
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        _record_login(
            organization=organization,
            user=user,
            identifier=identifier,
            request=request,
            was_successful=False,
            failure_reason="bad_password",
        )
        if just_locked:
            raise AccountLockedError()
        raise InvalidCredentialsError()

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = timezone.now()
    user.save(update_fields=["failed_login_attempts", "locked_until", "last_login"])

    _record_login(
        organization=organization,
        user=user,
        identifier=identifier,
        request=request,
        was_successful=True,
    )
    device, device_created = _upsert_device(user, device_id, device_name, platform)
    if device_created:
        _notify_new_device_login(user=user, device=device, request=request)

    # Binds the same tenant context/RLS session a JWT-authenticated request
    # would (see `TenantAwareJWTAuthentication`) — there is no JWT yet at
    # this point for that to have done it, but the response below still
    # needs to read this user's own tenant-scoped data (e.g. `employee`
    # nested into `UserSummarySerializer`) in this same request.
    rls.bind_for_user(user)

    access_token, refresh_token = _issue_tokens(user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "must_change_password": user.must_change_password,
        "user": user,
    }


def change_password(user, current_password, new_password):
    if not user.check_password(current_password):
        raise ApiError(
            code="INVALID_CREDENTIALS",
            status_code=401,
            message="Current password is incorrect.",
        )
    validate_password_strength(new_password, user=user, field="new_password")
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password"])
    _notify_password_changed(user)


def request_profile_picture_upload(*, user, content_type):
    """Same presigned-upload pattern as
    apps.employees.services.request_profile_picture_upload, generalized to
    any UserAccount — Org Admin / Super Admin accounts have no Employee
    row to hang a picture off of, so it lives on UserAccount directly.
    """
    extension = _PROFILE_PICTURE_CONTENT_TYPE_EXTENSIONS[content_type]
    bucket = settings.SUPABASE_STORAGE_BUCKET_PROFILE_PICTURES
    path_prefix = f"{user.organization_id or 'platform'}/{user.id}"

    try:
        upload_url, path = supabase_client.create_signed_upload_path(
            bucket=bucket, path_prefix=path_prefix, extension=extension
        )
        public_url = supabase_client.public_url(bucket=bucket, path=path)
    except supabase_client.StorageNotConfiguredError as exc:
        if not settings.DEBUG:
            raise StorageUnavailableError() from exc
        upload_url, path = local_dev.create_local_upload_path(
            bucket=bucket, path_prefix=path_prefix, extension=extension
        )
        public_url = local_dev.local_public_url(bucket=bucket, path=path)
    except supabase_client.StorageRequestError as exc:
        raise ApiError(
            code="STORAGE_REQUEST_FAILED", status_code=502, message=str(exc)
        ) from exc

    user.profile_picture_url = public_url
    user.save(update_fields=["profile_picture_url"])
    return upload_url, user.profile_picture_url


def request_password_reset(*, organization_code, identifier):
    """Always returns None regardless of whether an account was found —
    the API response must not leak account existence (Architecture §6.1).
    """
    organization = None
    if organization_code:
        organization = Organization.objects.filter(code__iexact=organization_code).first()
        if organization is None:
            return

    user = _find_user(organization, identifier)
    if user is None or not user.is_active:
        return

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_PASSWORD_RESET_URL}?uid={uidb64}&token={token}"

    message = (
        f"Use this link to reset your password: {reset_url}\n\n"
        "If you did not request this, ignore this email."
    )
    send_mail(
        subject="Reset your SWAMS password",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def confirm_password_reset(*, uidb64, token, new_password):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = UserAccount.objects.get(pk=user_id)
    except (UserAccount.DoesNotExist, ValueError, TypeError, OverflowError):
        raise InvalidResetTokenError()

    if not password_reset_token_generator.check_token(user, token):
        raise InvalidResetTokenError()

    validate_password_strength(new_password, user=user, field="new_password")
    user.set_password(new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(
        update_fields=["password", "must_change_password", "failed_login_attempts", "locked_until"]
    )
    _notify_password_changed(user)


def revoke_all_sessions(user):
    """Blacklist every outstanding refresh token for a user — used for
    'logout from all devices' and on refresh-token-reuse detection.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    outstanding = OutstandingToken.objects.filter(user=user)
    already_blacklisted = set(
        BlacklistedToken.objects.filter(token__in=outstanding).values_list("token_id", flat=True)
    )
    for token in outstanding.exclude(id__in=already_blacklisted):
        BlacklistedToken.objects.create(token=token)
