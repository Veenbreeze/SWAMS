import pytest

from apps.audit_logs.models import AuditLog
from apps.subscriptions import services
from apps.subscriptions.models import SubscriptionStatus
from core.db import rls
from core.middleware.tenant_context import current_organization_id
from tests.factories import (
    OrganizationFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
    SuperAdminFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _bind_platform_wide():
    """Every service in this module is a Super-Admin/platform operation —
    in production, `TenantAwareJWTAuthentication` already binds WILDCARD
    before the view (and therefore the service call) ever runs. A direct,
    non-request unit test has to replicate that itself: without it,
    Postgres RLS's SELECT policy has nothing to key on, and even a
    `USING (true)` UPDATE policy can't target a row it can't first see —
    see apps/leave/tests/test_services.py's `_bind()` for the equivalent
    per-organization version of this same requirement.
    """
    rls.bind(platform_wide=True)
    yield
    current_organization_id.set(None)
    rls.reset()


def test_create_plan():
    plan = services.create_plan(
        data={
            "code": "BASIC",
            "name": "Basic",
            "max_employees": 10,
            "max_branches": 1,
            "monthly_price": "50.00",
        }
    )
    assert plan.code == "BASIC"
    assert plan.grace_period_days == 7


def test_create_plan_rejects_duplicate_code():
    SubscriptionPlanFactory(code="BASIC")

    with pytest.raises(services.PlanCodeTakenError):
        services.create_plan(
            data={
                "code": "basic",
                "name": "Basic Again",
                "max_employees": 10,
                "max_branches": 1,
                "monthly_price": "50.00",
            }
        )


def test_update_plan():
    plan = SubscriptionPlanFactory(monthly_price="50.00")

    services.update_plan(plan=plan, data={"monthly_price": "75.00", "is_active": False})

    plan.refresh_from_db()
    assert str(plan.monthly_price) == "75.00"
    assert plan.is_active is False


def test_assign_subscription_creates_row_and_audit_log():
    admin = SuperAdminFactory()
    organization = OrganizationFactory()
    plan = SubscriptionPlanFactory()

    subscription = services.assign_subscription(
        organization=organization,
        plan=plan,
        start_date="2026-01-01",
        expiry_date="2026-12-31",
        actor=admin,
    )

    assert subscription.organization == organization
    assert subscription.plan == plan
    assert subscription.status == SubscriptionStatus.TRIAL
    assert AuditLog.objects.all_tenants().filter(action="subscription.assigned").exists()


def test_assign_subscription_does_not_touch_organization_status():
    from apps.organizations.models import OrganizationStatus

    admin = SuperAdminFactory()
    organization = OrganizationFactory(status=OrganizationStatus.SUSPENDED)
    plan = SubscriptionPlanFactory()

    services.assign_subscription(
        organization=organization,
        plan=plan,
        start_date="2026-01-01",
        expiry_date="2026-12-31",
        actor=admin,
    )

    organization.refresh_from_db()
    assert organization.status == OrganizationStatus.SUSPENDED


def test_cancel_subscription():
    admin = SuperAdminFactory()
    subscription = SubscriptionFactory()

    services.cancel_subscription(subscription=subscription, actor=admin)

    subscription.refresh_from_db()
    assert subscription.status == SubscriptionStatus.CANCELLED
    assert AuditLog.objects.all_tenants().filter(action="subscription.cancelled").exists()
