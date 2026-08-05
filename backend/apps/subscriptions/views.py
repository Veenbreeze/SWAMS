import datetime

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.subscriptions import services
from apps.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
from apps.subscriptions.serializers import (
    SubscriptionCreateSerializer,
    SubscriptionPlanSerializer,
    SubscriptionPlanUpdateSerializer,
    SubscriptionSerializer,
)
from core.permissions.roles import IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

# Explicit (not appended) — see NotBlockedByPasswordChange's docstring on
# why views that need a non-default role check must restate the full list.
_PLATFORM_PERMISSIONS = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]


class SubscriptionPlanListCreateView(generics.ListCreateAPIView):
    permission_classes = _PLATFORM_PERMISSIONS
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = services.create_plan(data=serializer.validated_data)
        return Response(SubscriptionPlanSerializer(plan).data, status=201)


class SubscriptionPlanDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = _PLATFORM_PERMISSIONS
    queryset = SubscriptionPlan.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return SubscriptionPlanUpdateSerializer
        return SubscriptionPlanSerializer

    def patch(self, request, *args, **kwargs):
        plan = self.get_object()
        serializer = self.get_serializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_plan(plan=plan, data=serializer.validated_data)
        return Response(SubscriptionPlanSerializer(plan).data)


class SubscriptionListCreateView(generics.ListCreateAPIView):
    permission_classes = _PLATFORM_PERMISSIONS
    filterset_fields = ["status", "organization"]

    def get_queryset(self):
        return Subscription.objects.all_tenants().select_related("organization", "plan")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubscriptionCreateSerializer
        return SubscriptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.assign_subscription(
            actor=request.user, request=request, **serializer.validated_data
        )
        return Response(SubscriptionSerializer(subscription).data, status=201)


class SubscriptionCancelView(APIView):
    permission_classes = _PLATFORM_PERMISSIONS

    def post(self, request, pk):
        subscription = generics.get_object_or_404(
            Subscription.objects.all_tenants().select_related("organization", "plan"), pk=pk
        )
        services.cancel_subscription(subscription=subscription, actor=request.user, request=request)
        return Response(SubscriptionSerializer(subscription).data)


class SubscriptionExpiryMonitorView(generics.ListAPIView):
    """Expiry monitoring view — every subscription that is the *current*
    term for its organization and is either already `EXPIRED` or expiring
    within the next 30 days, soonest first. Feeds the Super Admin web
    "expiry monitoring" page (docs/05-DEVELOPMENT-ROADMAP.md Phase 8).
    """

    permission_classes = _PLATFORM_PERMISSIONS
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        # `.distinct("organization_id")` (Postgres DISTINCT ON) would be a
        # one-liner here, but this app runs on SQLite in dev/test — so the
        # "most recent term per organization" reduction is done in Python
        # instead, same tradeoff as `Organization.current_subscription`.
        horizon = datetime.date.today() + datetime.timedelta(days=30)
        current_id_by_org = {}
        for subscription_id, organization_id in (
            Subscription.objects.all_tenants()
            .exclude(status=SubscriptionStatus.CANCELLED)
            .order_by("organization_id", "-start_date")
            .values_list("id", "organization_id")
        ):
            current_id_by_org.setdefault(organization_id, subscription_id)

        return (
            Subscription.objects.all_tenants()
            .filter(id__in=current_id_by_org.values(), expiry_date__lte=horizon)
            .select_related("organization", "plan")
            .order_by("expiry_date")
        )
