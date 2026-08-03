from apps.security.models import SecurityEvent


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class SecurityEventLogger:
    @staticmethod
    def record(
        *, event_type, organization=None, user=None, description="", metadata=None, request=None
    ):
        """Writes one security event. Called explicitly, same rationale as
        `apps.audit_logs.services.AuditLogger.record` — never inferred
        implicitly, always a deliberate call from the code path that
        detected the anomaly.
        """
        ip_address = _client_ip(request)
        resolved_user = user if getattr(user, "is_authenticated", True) else None

        SecurityEvent.objects.all_tenants().create(
            organization=organization or getattr(resolved_user, "organization", None),
            user=resolved_user,
            event_type=event_type,
            description=description,
            ip_address=ip_address,
            metadata=metadata or {},
        )
