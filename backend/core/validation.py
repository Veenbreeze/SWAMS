"""Shared password-strength validation — wraps Django's built-in
validators (see AUTH_PASSWORD_VALIDATORS in settings) behind this
project's ApiError envelope. Every place that accepts a caller-supplied
password (self-service change, password reset, Super Admin setting an
Org Admin's password, Org Admin setting an employee's password) needs
the exact same check, so it lives here rather than duplicated per app.
"""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError

from core.exceptions import ApiError


def validate_password_strength(password, *, user=None, field="password"):
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ApiError(
            code="VALIDATION_ERROR",
            status_code=400,
            message="Password does not meet security requirements.",
            details={field: exc.messages},
        ) from exc
