import uuid

from django.db import models

from core.db.tenant import TenantModel


class AuditLog(TenantModel):
    """Immutable "who did what" trail — see docs/02-DATABASE-ERD.md and
    docs/01-SYSTEM-ARCHITECTURE.md §6.7.

    `organization` is null for platform-level actions (e.g. Super Admin
    creating an organization) that don't belong to any single tenant.
    Application-level controls (no admin change/delete, no API
    update/delete endpoint) enforce append-only-ness for now; a hard
    Postgres-grant-level REVOKE (the stronger control described in the
    architecture doc) is a production-database provisioning step for
    whoever administers the live Supabase project — it can't be safely
    hardcoded into a migration here, since it depends on which DB role
    the app connects as, and would be a no-op (or an error) against a
    superuser connection.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        "authentication.UserAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Null if the action was system-initiated rather than performed by a user.",
    )
    action = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} @ {self.timestamp:%Y-%m-%d %H:%M}"
