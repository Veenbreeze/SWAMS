import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.db.tenant import TenantModel


class Branch(TenantModel):
    """A physical workplace location employees check in/out against — see
    docs/02-DATABASE-ERD.md and docs/05-DEVELOPMENT-ROADMAP.md Phase 4/5.

    `latitude`/`longitude` are only ever written by
    `capture-location`-style flows fed from a device's Geolocation API
    (see apps/locations/serializers.py) — there is deliberately no plain
    numeric-entry path in the API, per the brief's requirement that manual
    lat/lng entry not exist at all, not just be discouraged in the UI.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    radius_meters = models.PositiveIntegerField(default=100)
    gps_accuracy_limit_meters = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["organization", "is_active"])]

    def __str__(self):
        return self.name
