"""Daily subscription expiry sweep — see docs/05-DEVELOPMENT-ROADMAP.md
Phase 8. Runs entirely outside any HTTP request (Celery Beat), so it must
bind the tenant contextvar/RLS session itself before touching any
tenant-scoped model — see apps/reports/tasks.py for the same pattern.

Warnings are keyed on an exact day match (`days_until_expiry in (7, 3, 1)`)
rather than a "warned" flag on the row: the task runs once a day, so each
threshold is naturally crossed exactly once per subscription term with no
extra state to keep in sync. The tradeoff is that a subscription created
*after* one of its own warning days has already passed (e.g. assigned with
only 2 days left on it) silently skips that specific warning — acceptable
here since Super Admin just set the date deliberately.
"""

import datetime

from celery import shared_task

from apps.authentication.models import Role, UserAccount
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationDispatcher
from apps.organizations.models import Organization, OrganizationStatus
from apps.subscriptions.models import SubscriptionStatus
from core.db import rls

_WARNING_DAYS = (7, 3, 1)


def _org_admins(organization):
    return UserAccount.objects.filter(organization=organization, role=Role.ORG_ADMIN)


def _notify_org_admins(*, organization, title, message):
    for admin in _org_admins(organization):
        NotificationDispatcher.notify(
            user=admin,
            category=NotificationCategory.SUBSCRIPTION,
            title=title,
            message=message,
            send_email=True,
        )


def _process_subscription(*, subscription, today):
    organization = subscription.organization
    days_until_expiry = (subscription.expiry_date - today).days

    if subscription.status in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE):
        if days_until_expiry in _WARNING_DAYS:
            _notify_org_admins(
                organization=organization,
                title="Subscription expiring soon",
                message=(
                    f"Your {subscription.plan.name} subscription expires in "
                    f"{days_until_expiry} day(s), on {subscription.expiry_date}."
                ),
            )
        elif today >= subscription.expiry_date:
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.save(update_fields=["status"])
            _notify_org_admins(
                organization=organization,
                title="Subscription expired",
                message=(
                    f"Your {subscription.plan.name} subscription expired on "
                    f"{subscription.expiry_date}. Renew to avoid losing access."
                ),
            )

    if subscription.status == SubscriptionStatus.EXPIRED:
        grace_deadline = subscription.expiry_date + datetime.timedelta(
            days=subscription.plan.grace_period_days
        )
        if today >= grace_deadline and organization.status != OrganizationStatus.SUSPENDED:
            organization.status = OrganizationStatus.SUSPENDED
            organization.save(update_fields=["status", "updated_at"])
            _notify_org_admins(
                organization=organization,
                title="Access suspended",
                message=(
                    f"Your {subscription.plan.name} subscription's grace period has "
                    "ended. Sign-in is suspended until it is renewed."
                ),
            )


@shared_task
def check_subscription_expiries():
    rls.bind(platform_wide=True)
    try:
        today = datetime.date.today()
        for organization in Organization.objects.exclude(status=OrganizationStatus.CANCELLED):
            subscription = organization.current_subscription
            if subscription is None:
                continue
            _process_subscription(subscription=subscription, today=today)
    finally:
        rls.reset()
