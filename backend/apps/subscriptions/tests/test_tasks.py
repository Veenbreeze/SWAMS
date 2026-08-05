import datetime

import pytest

from apps.authentication.models import Role
from apps.notifications.models import Notification, NotificationCategory
from apps.organizations.models import OrganizationStatus
from apps.subscriptions.models import SubscriptionStatus
from apps.subscriptions.tasks import check_subscription_expiries
from core.db import rls
from core.middleware.tenant_context import current_organization_id
from tests.factories import (
    OrganizationFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


@pytest.fixture(autouse=True)
def _reset_tenant_context():
    yield
    current_organization_id.set(None)
    rls.reset()


def _org_admin_notifications(organization):
    current_organization_id.set(str(organization.id))
    rls.bind(organization_id=organization.id)
    try:
        return list(Notification.objects.filter(category=NotificationCategory.SUBSCRIPTION))
    finally:
        current_organization_id.set(None)
        rls.reset()


@pytest.mark.parametrize("days_out", [7, 3, 1])
def test_sends_warning_at_each_threshold(days_out):
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    org_admin = UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    SubscriptionFactory(
        organization=organization,
        expiry_date=TODAY + datetime.timedelta(days=days_out),
        status=SubscriptionStatus.ACTIVE,
    )

    check_subscription_expiries()

    notifications = _org_admin_notifications(organization)
    assert len(notifications) == 1
    assert notifications[0].user_id == org_admin.id
    assert "expires in" in notifications[0].message


def test_does_not_warn_outside_threshold_days():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    SubscriptionFactory(
        organization=organization,
        expiry_date=TODAY + datetime.timedelta(days=10),
        status=SubscriptionStatus.ACTIVE,
    )

    check_subscription_expiries()

    assert _org_admin_notifications(organization) == []


def test_flips_to_expired_and_notifies_on_lapse_day():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    subscription = SubscriptionFactory(
        organization=organization, expiry_date=TODAY, status=SubscriptionStatus.ACTIVE
    )

    check_subscription_expiries()

    # `check_subscription_expiries` resets RLS to unbound in its own
    # `finally` block once done (mirroring apps/reports/tasks.py) — reading
    # the row back here needs its own fresh bind, same as
    # apps/reports/tests/test_export.py's `_get_job()`.
    rls.bind(platform_wide=True)
    try:
        subscription.refresh_from_db()
    finally:
        rls.reset()
    assert subscription.status == SubscriptionStatus.EXPIRED
    notifications = _org_admin_notifications(organization)
    assert len(notifications) == 1
    assert "expired" in notifications[0].title.lower()


def test_organization_still_active_within_grace_period():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    plan = SubscriptionPlanFactory(grace_period_days=7)
    SubscriptionFactory(
        organization=organization,
        plan=plan,
        expiry_date=TODAY - datetime.timedelta(days=3),
        status=SubscriptionStatus.EXPIRED,
    )

    check_subscription_expiries()

    organization.refresh_from_db()
    assert organization.status == OrganizationStatus.ACTIVE


def test_organization_suspended_once_grace_period_elapses():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    plan = SubscriptionPlanFactory(grace_period_days=7)
    SubscriptionFactory(
        organization=organization,
        plan=plan,
        expiry_date=TODAY - datetime.timedelta(days=8),
        status=SubscriptionStatus.EXPIRED,
    )

    check_subscription_expiries()

    organization.refresh_from_db()
    assert organization.status == OrganizationStatus.SUSPENDED
    notifications = _org_admin_notifications(organization)
    assert any("suspended" in n.title.lower() for n in notifications)


def test_suspension_is_idempotent_across_repeated_runs():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    plan = SubscriptionPlanFactory(grace_period_days=7)
    SubscriptionFactory(
        organization=organization,
        plan=plan,
        expiry_date=TODAY - datetime.timedelta(days=8),
        status=SubscriptionStatus.EXPIRED,
    )

    check_subscription_expiries()
    check_subscription_expiries()

    notifications = _org_admin_notifications(organization)
    suspension_notifications = [n for n in notifications if "suspended" in n.title.lower()]
    assert len(suspension_notifications) == 1


def test_cancelled_subscription_is_left_alone():
    organization = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    UserAccountFactory(organization=organization, role=Role.ORG_ADMIN)
    SubscriptionFactory(
        organization=organization,
        expiry_date=TODAY - datetime.timedelta(days=100),
        status=SubscriptionStatus.CANCELLED,
    )

    check_subscription_expiries()

    organization.refresh_from_db()
    assert organization.status == OrganizationStatus.ACTIVE
    assert _org_admin_notifications(organization) == []


def test_organization_without_any_subscription_is_skipped():
    OrganizationFactory(status=OrganizationStatus.ACTIVE)

    check_subscription_expiries()  # must not raise
