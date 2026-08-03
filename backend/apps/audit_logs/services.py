from apps.audit_logs.models import AuditLog


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditLogger:
    @staticmethod
    def record(*, actor, action, organization=None, description="", request=None):
        """Writes one audit trail entry. Called explicitly from services/
        views on every state-changing action — never inferred implicitly
        from signals, so the trail only ever contains actions someone
        deliberately decided were worth recording.
        """
        ip_address = None
        device_info = ""
        if request is not None:
            ip_address = _client_ip(request)
            device_info = request.META.get("HTTP_USER_AGENT", "")[:255]

        user = actor if getattr(actor, "is_authenticated", False) else None
        resolved_organization = organization or getattr(user, "organization", None)

        AuditLog.objects.all_tenants().create(
            organization=resolved_organization,
            user=user,
            action=action,
            description=description,
            ip_address=ip_address,
            device_info=device_info,
        )
