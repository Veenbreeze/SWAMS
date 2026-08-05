import uuid

from django.db import models

from core.db.tenant import TenantModel


class SubscriptionPlan(models.Model):
    """Platform-wide pricing catalog (Basic/Standard/Premium, ...) — not
    tenant-scoped itself, managed only by Super Admin. See
    docs/02-DATABASE-ERD.md.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    max_employees = models.PositiveIntegerField()
    max_branches = models.PositiveIntegerField()
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    grace_period_days = models.PositiveIntegerField(
        default=7,
        help_text=(
            "Days an organization keeps login access after a subscription on this "
            "plan expires, before it is auto-suspended — see Phase 8's expiry job."
        ),
    )

    class Meta:
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name


class SubscriptionStatus(models.TextChoices):
    TRIAL = "TRIAL", "Trial"
    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    CANCELLED = "CANCELLED", "Cancelled"


class Subscription(TenantModel):
    """One organization's subscription term. See docs/02-DATABASE-ERD.md.

    There is no `Organization.current_subscription_id` field — the
    "current" one is simply the most recent row by `start_date`
    (`Organization.current_subscription` property below), which avoids a
    circular FK between Organization and Subscription for no real benefit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.RESTRICT, related_name="subscriptions"
    )
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIAL
    )
    start_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.organization.code} — {self.plan.code} ({self.status})"
