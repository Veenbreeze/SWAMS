import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.db.tenant import TenantModel


class Shift(TenantModel):
    """A named work schedule an `Employee` can be assigned to — see
    docs/02-DATABASE-ERD.md. `AttendanceRule`'s late/overtime thresholds
    are evaluated against whichever shift an employee is assigned, not
    stored redundantly here.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="shifts"
    )
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    crosses_midnight = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.start_time}–{self.end_time})"


def _default_working_days():
    # Monday=0 .. Sunday=6 (matches date.weekday()) — Mon-Fri by default.
    return [0, 1, 2, 3, 4]


class AttendanceRule(TenantModel):
    """One row per organization — the "Working days / late threshold /
    overtime threshold" settings described in the brief's §13, read by
    Phase 5's status-calculation logic. See docs/02-DATABASE-ERD.md.

    Deliberately has no `start_time`/`end_time` of its own: those live per
    `Shift`, since an org can have multiple shifts with different hours —
    this table only holds the threshold *minutes* applied relative to
    whichever shift an employee is assigned.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="attendance_rule"
    )
    working_days = models.JSONField(default=_default_working_days)
    late_threshold_minutes = models.PositiveIntegerField(default=0)
    early_departure_threshold_minutes = models.PositiveIntegerField(default=0)
    overtime_threshold_minutes = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attendance rule for {self.organization.code}"


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    LATE = "LATE", "Late"
    EARLY_DEPARTURE = "EARLY_DEPARTURE", "Early Departure"
    ABSENT = "ABSENT", "Absent"
    OVERTIME = "OVERTIME", "Overtime"


class Attendance(TenantModel):
    """One row per employee per calendar day — check-in and check-out both
    write to the same row (`UniqueConstraint` below). See
    docs/02-DATABASE-ERD.md and docs/01-SYSTEM-ARCHITECTURE.md §7.

    `early_departure_minutes` is additive beyond the brief's literal field
    list: the brief only lists `late_minutes`/`overtime_minutes`, but
    `status` includes `EARLY_DEPARTURE` as a value — without a
    corresponding minutes column that status would be unreportable
    (dashboards/exports in Phase 6 need a number, not just the label).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="attendance_records"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="attendance_records"
    )
    branch = models.ForeignKey(
        "locations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    attendance_date = models.DateField()

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    check_in_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    check_in_accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    check_in_device_id = models.CharField(max_length=255, blank=True)
    check_in_is_mock = models.BooleanField(default=False)

    check_out_time = models.DateTimeField(null=True, blank=True)
    check_out_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    check_out_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    check_out_accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    check_out_device_id = models.CharField(max_length=255, blank=True)
    check_out_is_mock = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    working_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    early_departure_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attendance_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "attendance_date"],
                name="unique_attendance_per_employee_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "employee", "-attendance_date"]),
            models.Index(fields=["organization", "branch", "attendance_date"]),
            models.Index(fields=["organization", "attendance_date", "status"]),
        ]

    def __str__(self):
        return f"{self.employee} — {self.attendance_date} ({self.status})"
