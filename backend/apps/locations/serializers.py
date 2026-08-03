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
    gps_accuracy = serializers.FloatField(write_only=True, min_value=0.01)


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
