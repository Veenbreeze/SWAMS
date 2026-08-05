from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.feedback.models import Recommendation
from apps.feedback.serializers import RecommendationCreateSerializer, RecommendationSerializer
from core.permissions.roles import IsOrgAdmin
from core.permissions.security import NotBlockedByPasswordChange

_ANY_AUTHENTICATED = [IsAuthenticated, NotBlockedByPasswordChange]
_ORG_ADMIN_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]


class RecommendationListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        # Method, not a `queryset = ...` class attribute — see
        # apps/locations/views.py's BranchListCreateView for why a
        # TenantManager-backed queryset must be built fresh per request.
        return Recommendation.objects.all()

    def get_permissions(self):
        # Listing is an Org Admin-only "inbox"; submitting is any staff
        # member with an employee profile (mobile's Settings screen).
        permissions = _ORG_ADMIN_PERMISSIONS if self.request.method == "GET" else _ANY_AUTHENTICATED
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RecommendationCreateSerializer
        return RecommendationSerializer

    def create(self, request, *args, **kwargs):
        employee = getattr(request.user, "employee", None)
        if employee is None:
            raise PermissionDenied("Only staff with an employee profile can do this.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recommendation = Recommendation.objects.create(
            organization=employee.organization, employee=employee, **serializer.validated_data
        )
        return Response(RecommendationSerializer(recommendation).data, status=201)
