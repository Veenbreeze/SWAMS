from rest_framework.permissions import BasePermission


class NotBlockedByPasswordChange(BasePermission):
    """Global gate: an admin-issued temporary password (must_change_password
    = True) blocks every endpoint except change-password — see
    docs/01-SYSTEM-ARCHITECTURE.md §6.1 "First Login Security".

    Views that must stay reachable (change-password itself) opt out by
    setting `permission_classes` explicitly, which replaces the global
    default list rather than appending to it.
    """

    message = "You must change your temporary password before continuing."
    code = "must_change_password"

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return True  # unauthenticated requests are handled by IsAuthenticated/AllowAny
        return not getattr(user, "must_change_password", False)
