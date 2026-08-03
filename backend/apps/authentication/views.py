from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import RefreshToken as SimpleJWTRefreshToken

from apps.authentication import services
from apps.authentication.models import UserAccount
from apps.authentication.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSummarySerializer,
)
from core.exceptions import ApiError


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.authenticate(
            organization_code=data["organization_code"] or None,
            identifier=data["identifier"],
            password=data["password"],
            request=request,
            device_id=data["device_id"] or None,
            device_name=data["device_name"] or None,
            platform=data["platform"] or None,
        )

        return Response(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "must_change_password": result["must_change_password"],
                "user": UserSummarySerializer(result["user"]).data,
            }
        )


class MeView(APIView):
    """Rehydrates `user` from a stored access token on app restart — a
    token surviving app restart doesn't mean the session is still valid
    server-side, so mobile calls this once at bootstrap rather than
    trusting the token's mere presence (see mobile's
    `AuthContext.js`).
    """

    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)


def _user_from_undecoded_token(raw_token):
    """Decode signature + expiry only (no blacklist check) so we can tell a
    replayed-but-legitimately-issued token (reuse attack) apart from a
    genuinely forged/garbage one — see docs/01-SYSTEM-ARCHITECTURE.md §6.1.
    """
    try:
        payload = token_backend.decode(raw_token, verify=True)
    except TokenBackendError:
        return None
    user_id = payload.get("user_id")
    if not user_id:
        return None
    return UserAccount.objects.filter(pk=user_id).first()


class TokenRefreshView(APIView):
    """Custom refresh endpoint (not simplejwt's stock TokenRefreshView) so
    the wire format matches docs/03-API-SPECIFICATION.md (`refresh_token`,
    not simplejwt's default `refresh` field) and so a blacklisted-token
    replay revokes every session for that user rather than just failing.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.data.get("refresh_token")
        if not raw_token:
            raise ApiError(
                code="VALIDATION_ERROR", status_code=400, message="refresh_token is required."
            )

        try:
            refresh = SimpleJWTRefreshToken(raw_token)
        except TokenError:
            user = _user_from_undecoded_token(raw_token)
            if user is not None:
                services.revoke_all_sessions(user)
                raise services.TokenReuseDetectedError()
            raise ApiError(
                code="TOKEN_INVALID", status_code=401, message="Invalid or expired refresh token."
            )

        response_data = {"access_token": str(refresh.access_token)}

        if jwt_settings.ROTATE_REFRESH_TOKENS:
            if jwt_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            # Registers the newly-rotated jti as its own OutstandingToken
            # row — without this, revoke_all_sessions()/"logout everywhere"
            # can never find (and therefore never blacklist) a token that
            # has already been rotated at least once, since set_jti() only
            # mutates the in-memory payload and touches no table.
            refresh.outstand()
            response_data["refresh_token"] = str(refresh)

        return Response(response_data)


class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            SimpleJWTRefreshToken(serializer.validated_data["refresh_token"]).blacklist()
        except TokenError:
            pass  # already invalid/expired/blacklisted — logout is idempotent
        return Response(status=204)


class LogoutAllView(APIView):
    def post(self, request):
        services.revoke_all_sessions(request.user)
        return Response(status=204)


class ChangePasswordView(APIView):
    # Explicit override (not the global default list) so this is the one
    # endpoint reachable while must_change_password is still set — see
    # core/permissions/security.py.
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(
            request.user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
        )
        return Response(status=204)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password-reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(
            organization_code=serializer.validated_data["organization_code"] or None,
            identifier=serializer.validated_data["identifier"],
        )
        # Always 200 regardless of whether an account was found — see
        # services.request_password_reset docstring.
        return Response(status=200)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "password-reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_password_reset(
            uidb64=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response(status=204)
