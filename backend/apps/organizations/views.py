from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations import services
from apps.organizations.models import Organization
from apps.organizations.serializers import (
    OrganizationCreateResponseSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
)
from core.permissions.roles import IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

# Explicit (not appended) — see NotBlockedByPasswordChange's docstring on
# why views that need a non-default role check must restate the full list.
_PLATFORM_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]


class OrganizationListCreateView(generics.ListCreateAPIView):
    permission_classes = _PLATFORM_PERMISSIONS
    queryset = Organization.objects.all()
    filterset_fields = ["status"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        admin_email = data.pop("admin_email")

        organization, admin, temporary_password = services.create_organization(
            data=data, admin_email=admin_email, actor=request.user, request=request
        )

        response = OrganizationCreateResponseSerializer(
            {
                "organization": organization,
                "admin": admin,
                "temporary_password": temporary_password,
            }
        )
        return Response(response.data, status=201)


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = _PLATFORM_PERMISSIONS
    queryset = Organization.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return OrganizationUpdateSerializer
        return OrganizationSerializer

    def patch(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = self.get_serializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_organization(
            organization=organization,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(OrganizationSerializer(organization).data)


class OrganizationSuspendView(APIView):
    permission_classes = _PLATFORM_PERMISSIONS

    def post(self, request, pk):
        organization = generics.get_object_or_404(Organization, pk=pk)
        services.suspend_organization(
            organization=organization, actor=request.user, request=request
        )
        return Response(OrganizationSerializer(organization).data)


class OrganizationActivateView(APIView):
    permission_classes = _PLATFORM_PERMISSIONS

    def post(self, request, pk):
        organization = generics.get_object_or_404(Organization, pk=pk)
        services.activate_organization(
            organization=organization, actor=request.user, request=request
        )
        return Response(OrganizationSerializer(organization).data)
