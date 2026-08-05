from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.security.models import SecurityEvent
from apps.security.serializers import SecurityEventSerializer
from core.permissions.roles import IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

_PLATFORM_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]


class SecurityEventListView(generics.ListAPIView):
    """Platform-wide, read-only — system-detected anomalies (see the model's
    docstring for how this differs from AuditLog). Super Admin only.
    """

    permission_classes = _PLATFORM_PERMISSIONS
    serializer_class = SecurityEventSerializer
    filterset_fields = ["organization", "event_type"]

    def get_queryset(self):
        return SecurityEvent.objects.all_tenants().select_related("organization", "user")
