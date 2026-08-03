from django.contrib import admin

from apps.subscriptions.models import Subscription, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "monthly_price", "max_employees", "max_branches", "is_active")
    search_fields = ("code", "name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "start_date", "expiry_date")
    list_filter = ("status", "plan")
    search_fields = ("organization__code", "organization__name")

    def get_queryset(self, request):
        return Subscription.objects.all_tenants()
