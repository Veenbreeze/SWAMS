from rest_framework import serializers

from apps.feedback.models import Recommendation


class RecommendationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = Recommendation
        fields = ["id", "employee_name", "message", "created_at"]
        read_only_fields = fields


class RecommendationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ["message"]
        extra_kwargs = {"message": {"allow_blank": False}}
