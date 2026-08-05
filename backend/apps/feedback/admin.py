from django.contrib import admin

from apps.feedback.models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "created_at")

    def get_queryset(self, request):
        return Recommendation.objects.all_tenants()
