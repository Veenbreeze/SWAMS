import uuid

from django.db import models

from core.db.tenant import TenantModel


class Recommendation(TenantModel):
    """A free-text suggestion an employee submits from the mobile app's
    Settings screen — see docs/05-DEVELOPMENT-ROADMAP.md. Deliberately no
    status/reply workflow (unlike LeaveRequest): this is a one-way
    employee-to-Org-Admin suggestion box, not a ticketing system.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="recommendations"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="recommendations"
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "-created_at"])]

    def __str__(self):
        return f"{self.employee} — {self.created_at:%Y-%m-%d}"
