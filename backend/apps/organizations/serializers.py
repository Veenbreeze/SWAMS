from rest_framework import serializers

from apps.authentication.serializers import UserSummarySerializer
from apps.organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "code",
            "name",
            "registration_number",
            "email",
            "phone",
            "address",
            "logo_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class OrganizationCreateSerializer(serializers.ModelSerializer):
    # The Super Admin supplies the first Org Admin's sign-in email; the
    # account itself (and its temporary password) is created by
    # services.create_organization, not by this serializer — a serializer
    # validates shape, it doesn't perform side effects.
    admin_email = serializers.EmailField(write_only=True)

    class Meta:
        model = Organization
        fields = [
            "code",
            "name",
            "registration_number",
            "email",
            "phone",
            "address",
            "logo_url",
            "admin_email",
        ]


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "email", "phone", "address", "logo_url"]
        extra_kwargs = {field: {"required": False} for field in fields}


class OrganizationCreateResponseSerializer(serializers.Serializer):
    organization = OrganizationSerializer()
    admin = UserSummarySerializer()
    temporary_password = serializers.CharField()
