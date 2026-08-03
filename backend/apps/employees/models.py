import uuid

from django.db import models

from core.db.tenant import TenantModel


class Department(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=255)
    parent_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_departments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmploymentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ON_LEAVE = "ON_LEAVE", "On Leave"
    TERMINATED = "TERMINATED", "Terminated"


class Employee(TenantModel):
    """Staff profile — see docs/02-DATABASE-ERD.md.

    `employment_status` is how an employee is removed from the roster:
    `DELETE /employees/{id}` sets this to `TERMINATED` rather than issuing
    a SQL `DELETE`, so attendance/leave history (Phase 5+) always has a
    row to point at — see docs/05-DEVELOPMENT-ROADMAP.md Phase 4.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="employees"
    )
    user = models.OneToOneField(
        "authentication.UserAccount", on_delete=models.CASCADE, related_name="employee"
    )
    employee_number = models.CharField(max_length=50)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    profile_picture_url = models.URLField(blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )
    branch = models.ForeignKey(
        "locations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    shift = models.ForeignKey(
        "attendance.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    position = models.CharField(max_length=150, blank=True)
    joining_date = models.DateField()
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "employee_number"], name="unique_employee_number_per_org"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "employment_status"]),
            models.Index(fields=["organization", "department"]),
            models.Index(fields=["organization", "branch"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class ManagerAssignment(TenantModel):
    """Scopes a `MANAGER`-role employee to a department and/or specific
    employees — see docs/02-DATABASE-ERD.md and
    docs/01-SYSTEM-ARCHITECTURE.md §5. At least one of `department`/
    `employee` must be set (enforced in
    apps/employees/serializers.py — a row with both null would scope the
    manager to nothing, which is never a legitimate assignment).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="manager_assignments"
    )
    manager = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="manager_assignments"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="managed_by_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "manager"])]

    def __str__(self):
        target = self.department or self.employee
        return f"{self.manager.full_name} -> {target}"
