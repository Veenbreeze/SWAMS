from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.audit_logs.models import AuditLog
from apps.audit_logs.serializers import AuditLogSerializer
from core.permissions.roles import IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

_PLATFORM_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]


class AuditLogListView(generics.ListAPIView):
    """Platform-wide, read-only — audit logs are append-only by design (see
    the model's docstring); there is deliberately no create/update/delete
    endpoint here, only Super Admin read access.
    """

    permission_classes = _PLATFORM_PERMISSIONS
    serializer_class = AuditLogSerializer
    filterset_fields = ["organization", "user", "action"]

    def get_queryset(self):
        return AuditLog.objects.all_tenants().select_related("organization", "user")
