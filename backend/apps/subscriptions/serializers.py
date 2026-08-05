from rest_framework import serializers

from apps.organizations.models import Organization
from apps.subscriptions.models import Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "code",
            "name",
            "max_employees",
            "max_branches",
            "monthly_price",
            "features",
            "is_active",
            "grace_period_days",
        ]
        read_only_fields = ["id"]


class SubscriptionPlanUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "name",
            "max_employees",
            "max_branches",
            "monthly_price",
            "features",
            "is_active",
            "grace_period_days",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class SubscriptionSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_code = serializers.CharField(source="organization.code", read_only=True)
    plan_id = serializers.UUIDField(source="plan.id", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "organization_id",
            "organization_name",
            "organization_code",
            "plan_id",
            "plan_code",
            "plan_name",
            "status",
            "start_date",
            "expiry_date",
            "created_at",
        ]
        read_only_fields = fields


class SubscriptionCreateSerializer(serializers.Serializer):
    # Neither Organization nor SubscriptionPlan is tenant-scoped (both are
    # platform-wide, Super-Admin-managed catalogs), so — unlike
    # apps/leave/serializers.py's tenant-scoped `leave_type` field — a plain
    # `.objects.all()` queryset here carries no import-time-baked-filter risk.
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.all())
    start_date = serializers.DateField()
    expiry_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["expiry_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"expiry_date": "expiry_date must be on or after start_date."}
            )
        return attrs
