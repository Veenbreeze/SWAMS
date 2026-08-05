from django.db import models


class PlatformSettings(models.Model):
    """Platform-wide configuration — a single row (pk always 1), created
    lazily on first access. Not tenant-scoped, so unlike most models here
    it isn't a `TenantModel` and carries no RLS policy.

    This only stores the flags; nothing else in the codebase reads them
    yet (e.g. `maintenance_mode` doesn't currently block logins). Wiring
    enforcement is a separate change once there's a concrete requirement
    for it.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    maintenance_mode = models.BooleanField(default=False)
    default_trial_days = models.PositiveIntegerField(default=14)
    support_email = models.EmailField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Platform settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Platform settings"
