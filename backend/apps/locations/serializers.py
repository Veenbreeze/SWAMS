from rest_framework import serializers

from apps.locations.models import Branch


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "radius_meters",
            "gps_accuracy_limit_meters",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "latitude", "longitude", "created_at"]


class _GpsAccuracyMixin(serializers.Serializer):
    # Not persisted anywhere on Branch (the ERD has no such column) — its
    # only job is proving the caller actually read a device's Geolocation
    # API result (which always reports an accuracy alongside coordinates)
    # rather than typing coordinates in by hand. See docs/03-API-SPECIFICATION.md §5.
    #
    # `max_value` matters just as much as the `min_value` floor: this
    # reading becomes the *center* employees' phone GPS is measured
    # against on every check-in (see apps.attendance.application.services
    # ._validate_location). The browser Geolocation API on a desktop with
    # no GPS chip silently falls back to WiFi/IP-based positioning, which
    # can be off by hundreds of meters — accepting that as a branch's
    # permanent location would make every subsequent check-in fail no
    # matter how accurate the employee's own phone GPS is. Capped at the
    # same 50m ceiling apps.locations.models.Branch.gps_accuracy_limit_meters
    # defaults to for the check-in side, so "good enough to check in with"
    # and "good enough to set the center with" agree.
    gps_accuracy = serializers.FloatField(write_only=True, min_value=0.01, max_value=50)


class BranchCreateSerializer(_GpsAccuracyMixin, serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "name",
            "address",
            "latitude",
            "longitude",
            "radius_meters",
            "gps_accuracy_limit_meters",
            "gps_accuracy",
        ]


class BranchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["name", "address", "radius_meters", "gps_accuracy_limit_meters", "is_active"]
        extra_kwargs = {field: {"required": False} for field in fields}


class BranchCaptureLocationSerializer(_GpsAccuracyMixin, serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180
    )
