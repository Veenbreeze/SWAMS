import uuid

from django.db import models


class OrganizationStatus(models.TextChoices):
    TRIAL = "TRIAL", "Trial"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    CANCELLED = "CANCELLED", "Cancelled"


class Organization(models.Model):
    """Tenant root. See docs/02-DATABASE-ERD.md.

    Schema-only for now: full admin lifecycle (create/suspend/activate,
    subscription linkage) is Phase 3 work. Created ahead of schedule
    because UserAccount (Phase 1, required for AUTH_USER_MODEL to exist
    before the first migration) has a foreign key to it.

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
