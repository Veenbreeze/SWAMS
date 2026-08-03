import uuid

from django.db import models

from core.db.tenant import TenantModel


class SecurityEventType(models.TextChoices):
    MOCK_LOCATION_DETECTED = "MOCK_LOCATION_DETECTED", "Mock location detected"
    IMPLAUSIBLE_TRAVEL_SPEED = "IMPLAUSIBLE_TRAVEL_SPEED", "Implausible travel speed"
    CROSS_TENANT_ACCESS_ATTEMPT = "CROSS_TENANT_ACCESS_ATTEMPT", "Cross-tenant access attempt"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED", "Account locked"
    NEW_DEVICE_LOGIN = "NEW_DEVICE_LOGIN", "New device login"


class SecurityEvent(TenantModel):
    """System-detected anomalies — separate from `AuditLog`'s "a user did
    X" trail, matching the brief's distinct Super Admin permissions "View
    system audit logs" vs. "View security events". See
    docs/02-DATABASE-ERD.md and docs/01-SYSTEM-ARCHITECTURE.md §6.3/§6.6.

    `organization`/`user` are nullable for the same reason as `AuditLog`'s:
    some events (e.g. a cross-tenant probe from an unauthenticated-looking
    request) may not resolve to a single tenant or identity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="security_events",
    )
    user = models.ForeignKey(
        "authentication.UserAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_events",
    )
    event_type = models.CharField(max_length=40, choices=SecurityEventType.choices)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}"
