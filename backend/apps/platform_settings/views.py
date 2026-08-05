from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.platform_settings.models import PlatformSettings
from apps.platform_settings.serializers import PlatformSettingsSerializer
from core.permissions.roles import IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

_PLATFORM_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]


class PlatformSettingsView(APIView):
    """Singleton settings resource — one row platform-wide, created lazily
    on first access rather than requiring a bootstrap step (same pattern
    as `apps.attendance.views.AttendanceRuleView`).
    """

    permission_classes = _PLATFORM_PERMISSIONS

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.load()).data)

    def patch(self, request):
        settings_obj = PlatformSettings.load()
        serializer = PlatformSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
