from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations import services
from apps.locations.models import Branch
from apps.locations.serializers import (
    BranchCaptureLocationSerializer,
    BranchCreateSerializer,
    BranchSerializer,
    BranchUpdateSerializer,
)
from core.permissions.roles import IsManagerOrAbove, IsOrgAdmin
from core.permissions.security import NotBlockedByPasswordChange

_READ_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsManagerOrAbove]
_WRITE_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]


class BranchListCreateView(generics.ListCreateAPIView):
    filterset_fields = ["is_active"]

    def get_queryset(self):
        # Deliberately a method, not `queryset = Branch.objects.all()`:
        # TenantManager.get_queryset() reads the request-scoped contextvar
        # at the moment `.all()`/`.filter()` is called. A class attribute
        # would evaluate that once at import time — before any request
        # ever binds the contextvar — permanently baking in `.none()`.
        return Branch.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BranchCreateSerializer
        return BranchSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = services.create_branch(
            organization=request.user.organization,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(BranchSerializer(branch).data, status=201)


class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return Branch.objects.all()

    def get_permissions(self):
        permissions = _READ_PERMISSIONS if self.request.method == "GET" else _WRITE_PERMISSIONS
        return [permission() for permission in permissions]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return BranchUpdateSerializer
        return BranchSerializer

    def patch(self, request, *args, **kwargs):
        branch = self.get_object()
        serializer = self.get_serializer(branch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_branch(
            branch=branch, data=serializer.validated_data, actor=request.user, request=request
        )
        return Response(BranchSerializer(branch).data)

    def perform_destroy(self, instance):
        services.delete_branch(branch=instance, actor=self.request.user, request=self.request)


class BranchCaptureLocationView(APIView):
    permission_classes = _WRITE_PERMISSIONS

    def post(self, request, pk):
        branch = generics.get_object_or_404(Branch.objects.all(), pk=pk)
        serializer = BranchCaptureLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.capture_branch_location(
            branch=branch, data=serializer.validated_data, actor=request.user, request=request
        )
        return Response(BranchSerializer(branch).data)
