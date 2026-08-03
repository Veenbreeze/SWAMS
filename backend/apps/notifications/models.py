import uuid

from django.db import models

from core.db.tenant import TenantModel


class NotificationCategory(models.TextChoices):
    ATTENDANCE = "ATTENDANCE", "Attendance"
    LEAVE = "LEAVE", "Leave"
    SECURITY = "SECURITY", "Security"
    SYSTEM = "SYSTEM", "System"


class Notification(TenantModel):
    """In-app notification — see docs/02-DATABASE-ERD.md. Phase 5 wires
    only the ATTENDANCE category (check-in/check-out success); LEAVE/
    SECURITY/SYSTEM fan-out is Phase 7 (`docs/05-DEVELOPMENT-ROADMAP.md`).

    `organization` is nullable for platform-level notifications (e.g. a
    future Super-Admin-to-Org-Admin system message) — no Phase 5 code path
    creates one yet, but the column exists so that doesn't require a
    migration later, mirroring `AuditLog.organization`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    user = models.ForeignKey(
        "authentication.UserAccount", on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]

    def __str__(self):
        return self.title
