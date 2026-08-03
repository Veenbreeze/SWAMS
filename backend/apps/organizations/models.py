import uuid

from django.db import models


class OrganizationStatus(models.TextChoices):
    TRIAL = "TRIAL", "Trial"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    CANCELLED = "CANCELLED", "Cancelled"


class Organization(models.Model):
    """Tenant root. See docs/02-DATABASE-ERD.md.

    `code` is the short login identifier (e.g. "ABC001") used in the
    organization_code + email/employee_number + password login triple —
    distinct from `registration_number`, which is the organization's legal
    registration number. Not in the brief's original field list; added
    here and reflected back into the ERD doc for consistency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20, choices=OrganizationStatus.choices, default=OrganizationStatus.TRIAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def current_subscription(self):
        """Most recent subscription row by start_date — see
        apps/subscriptions/models.py's Subscription docstring for why this
        is a computed property rather than a stored FK.

        Deliberately goes through `Subscription.objects.all_tenants()`
        rather than the reverse accessor `self.subscriptions`: the reverse
        related manager is dynamically generated as a *subclass* of
        TenantManager, and `.all_tenants()`'s `super().get_queryset()`
        walks the MRO from TenantManager upward — past `Manager`, but
        never back down into the related manager's own
        `.filter(organization=self)` override. So
        `self.subscriptions.all_tenants()` silently returns every
        Subscription row for *every* organization, not just this one.
        Calling `.all_tenants()` on the base manager and filtering
        explicitly avoids that trap entirely.
        """
        from apps.subscriptions.models import Subscription

        return (
            Subscription.objects.all_tenants()
            .filter(organization=self)
            .order_by("-start_date")
            .first()
        )
