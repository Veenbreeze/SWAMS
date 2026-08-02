"""Tenant binding — see docs/01-SYSTEM-ARCHITECTURE.md §4.1.

This is implemented as a JWTAuthentication wrapper, not literal Django
`MIDDLEWARE`. DRF resolves `request.user` from the JWT lazily inside view
dispatch, which runs *after* Django's regular middleware stack — so plain
middleware can't see the authenticated identity at the point it would need
to bind tenant context. Wrapping the authentication class is the first
point at which that identity actually exists.

`ResetTenantContextMiddleware` below *is* real Django middleware; it only
clears the contextvars at the start of each request so a value from one
request can never leak into the next on a reused worker thread.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import ExpiredTokenError, TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from core.middleware.tenant_context import current_organization_id, current_role


class TenantAwareJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        """Distinguishes an expired access token from a genuinely invalid
        one — stock simplejwt collapses both into one generic
        `InvalidToken` (code "token_not_valid"), which loses the
        distinction docs/03-API-SPECIFICATION.md's error table promises
        (`TOKEN_EXPIRED` vs `TOKEN_INVALID`) and that the web/mobile
        clients' Axios interceptors key off of to decide whether to
        silently refresh or force a full logout.

        `ApiError` is imported locally (not at module level) to avoid a
        circular import: DRF eagerly resolves `DEFAULT_AUTHENTICATION_CLASSES`
        (this class) while importing `rest_framework.views`, which
        `core.exceptions` itself imports at module level.
        """
        from core.exceptions import ApiError

        for AuthToken in jwt_settings.AUTH_TOKEN_CLASSES:
            try:
                return AuthToken(raw_token)
            except ExpiredTokenError:
                raise ApiError(
                    code="TOKEN_EXPIRED",
                    status_code=401,
                    message="Your session has expired. Please sign in again.",
                )
            except TokenError:
                continue

        raise ApiError(
            code="TOKEN_INVALID", status_code=401, message="Invalid authentication token."
        )

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        current_organization_id.set(str(user.organization_id) if user.organization_id else None)
        current_role.set(user.role)
        return user, validated_token


class ResetTenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_organization_id.set(None)
        current_role.set(None)
        return self.get_response(request)
