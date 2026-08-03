import uuid

from django.db import models

from core.db.tenant import TenantModel


class LeaveType(TenantModel):
    """Org-configurable leave category — see docs/02-DATABASE-ERD.md.
    Modeled as a table (not a hardcoded enum) so an Org Admin can add
    org-specific types, per the ERD's own rationale.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="leave_types"
    )
    name = models.CharField(max_length=100)
    default_annual_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    requires_approval = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeaveRequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaveRequest(TenantModel):
    """One employee's leave request — see docs/02-DATABASE-ERD.md and
    docs/05-DEVELOPMENT-ROADMAP.md Phase 7. Balance is only touched on
    APPROVED (decremented) and on cancelling an already-APPROVED request
    (restored) — see apps/leave/services.py; a PENDING/REJECTED request
    never affects `LeaveBalance` at all.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="leave_requests"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.RESTRICT, related_name="leave_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=LeaveRequestStatus.choices, default=LeaveRequestStatus.PENDING
    )
    approved_by = models.ForeignKey(
        "authentication.UserAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decision_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "employee", "-created_at"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.employee} — {self.leave_type} ({self.status})"

    @property
    def days_requested(self):
        return (self.end_date - self.start_date).days + 1


class LeaveBalance(TenantModel):
    """One employee's allocated/used days for a leave type in a given
    year — see docs/02-DATABASE-ERD.md.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="leave_balances"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="leave_balances"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="leave_balances"
    )
    year = models.PositiveIntegerField()
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "year"],
                name="unique_balance_per_employee_type_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.employee} — {self.leave_type} {self.year}: "
            f"{self.used_days}/{self.allocated_days}"
        )

    @property
    def remaining_days(self):
        return self.allocated_days - self.used_days
