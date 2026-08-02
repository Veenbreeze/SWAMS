"""Role-based permission classes — see docs/01-SYSTEM-ARCHITECTURE.md §5.

These check *role* only. Object-level tenant ownership (does this specific
row belong to the caller's organization?) is a separate concern, added
in Phase 3 once there's a tenant-scoped model to check it against.
"""

from rest_framework.permissions import BasePermission

from apps.authentication.models import Role


class IsSuperAdmin(BasePermission):
    message = "Super Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.SUPER_ADMIN)


class IsOrgAdmin(BasePermission):
    message = "Organization Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ORG_ADMIN)


class IsManagerOrAbove(BasePermission):
    message = "Manager access or higher required."

    _ALLOWED_ROLES = {Role.ORG_ADMIN, Role.MANAGER}

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self._ALLOWED_ROLES)


class IsSelf(BasePermission):
    """Object-level: the target object is (or belongs to) the caller.

    Works against either a UserAccount instance directly, or any object
    exposing a `.user` attribute (e.g. Employee, once it exists).
    """

    message = "You may only access your own resource."

    def has_object_permission(self, request, view, obj):
        target_user = getattr(obj, "user", obj)
        return target_user == request.user
