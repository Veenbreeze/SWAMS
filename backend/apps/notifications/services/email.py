"""Email channel — see docs/01-SYSTEM-ARCHITECTURE.md §8. Reserved for the
categories the roadmap calls out explicitly (password changes, leave
decisions, security alerts) — routine attendance/leave-submission events
stay in-app + push only, so email doesn't become another per-check-in
interruption. Callers opt in per-event via `NotificationDispatcher.notify
(..., send_email=True)`, not per-category here, since e.g. LEAVE covers
both "submitted" (in-app + push only) and "decided" (also email).
"""

from django.conf import settings
from django.core.mail import send_mail


def send_notification_email(*, user, subject, message):
    if not user.email:
        return
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
