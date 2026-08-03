from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from core.permissions.security import NotBlockedByPasswordChange

_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange]


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = _PERMISSIONS
    filterset_fields = ["is_read", "category"]

    def get_queryset(self):
        # Method, not a class-level `queryset = ...` attribute — see
        # apps/locations/views.py's BranchListCreateView for why.
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
    permission_classes = _PERMISSIONS

    def post(self, request, pk):
        notification = generics.get_object_or_404(
            Notification.objects.filter(user=request.user), pk=pk
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = _PERMISSIONS

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"updated": updated})
