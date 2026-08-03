"""Notification fan-out mechanism — see docs/01-SYSTEM-ARCHITECTURE.md §8
and docs/05-DEVELOPMENT-ROADMAP.md Phase 7.

Deliberately domain-agnostic: this knows *how* to reach a user (an in-app
row + push, optionally email) but not *who* to notify for a given business
event or whether that event warrants email — that policy decision belongs
to the calling service (apps/leave/services.py,
apps/authentication/services.py, apps/attendance/application/services.py,
...). Keeping it that way avoids an apps.leave <-> apps.notifications
import cycle and means adding a new notification-worthy event never
requires touching this file.
"""

from apps.notifications.models import Notification
from apps.notifications.services import email as email_service
from apps.notifications.services import push as push_service


class NotificationDispatcher:
    @staticmethod
    def notify(*, user, category, title, message="", organization=None, send_email=False):
        notification = Notification.objects.all_tenants().create(
            organization=organization or getattr(user, "organization", None),
            user=user,
            category=category,
            title=title,
            message=message,
        )
        push_service.send_push(user=user, title=title, message=message)
        if send_email:
            email_service.send_notification_email(user=user, subject=title, message=message)
        return notification
