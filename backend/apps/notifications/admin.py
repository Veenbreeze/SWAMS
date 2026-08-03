from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "is_read", "created_at")
    list_filter = ("category", "is_read")
    search_fields = ("title", "user__email")

    def get_queryset(self, request):
        return Notification.objects.all_tenants()
