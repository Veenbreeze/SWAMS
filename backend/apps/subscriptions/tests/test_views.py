import datetime

import pytest
from rest_framework.test import APIClient

from apps.authentication.models import Role
from apps.subscriptions.models import SubscriptionStatus
from tests.factories import (
    OrganizationFactory,
    SubscriptionFactory,
    SubscriptionPlanFactory,
    SuperAdminFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"
TODAY = datetime.date.today()


def _client_as(user):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login",
        {
            "organization_code": user.organization.code if user.organization else "",
            "identifier": user.email,
            "password": PASSWORD,
        },
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access_token']}")
    return client


def test_super_admin_can_create_plan():
    admin = SuperAdminFactory(password=PASSWORD)
    client = _client_as(admin)

    response = client.post(
        "/api/v1/platform/subscriptions/plans",
        {
            "code": "PREMIUM",
            "name": "Premium",
            "max_employees": 200,
            "max_branches": 10,
            "monthly_price": "500.00",
            "grace_period_days": 14,
        },
    )

    assert response.status_code == 201
    assert response.json()["code"] == "PREMIUM"
    assert response.json()["grace_period_days"] == 14


@pytest.mark.parametrize("role", [Role.ORG_ADMIN, Role.MANAGER, Role.EMPLOYEE])
def test_creating_plan_requires_super_admin(role):
    user = UserAccountFactory(password=PASSWORD, role=role)
    client = _client_as(user)

    response = client.post(
        "/api/v1/platform/subscriptions/plans",
        {
            "code": "PREMIUM",
            "name": "Premium",
            "max_employees": 200,
            "max_branches": 10,
            "monthly_price": "500.00",
        },
    )

    assert response.status_code == 403


def test_list_plans():
    admin = SuperAdminFactory(password=PASSWORD)
    SubscriptionPlanFactory(code="BASIC")
    SubscriptionPlanFactory(code="PREMIUM")
    client = _client_as(admin)

    response = client.get("/api/v1/platform/subscriptions/plans")

    assert response.status_code == 200
    codes = {plan["code"] for plan in response.json()["results"]}
    assert {"BASIC", "PREMIUM"} <= codes


def test_patch_plan():
    admin = SuperAdminFactory(password=PASSWORD)
    plan = SubscriptionPlanFactory(monthly_price="50.00")
    client = _client_as(admin)

    response = client.patch(
        f"/api/v1/platform/subscriptions/plans/{plan.id}", {"monthly_price": "60.00"}
    )

    assert response.status_code == 200
    assert response.json()["monthly_price"] == "60.00"


def test_super_admin_can_assign_subscription_to_organization():
    admin = SuperAdminFactory(password=PASSWORD)
    organization = OrganizationFactory()
    plan = SubscriptionPlanFactory()
    client = _client_as(admin)

    response = client.post(
        "/api/v1/platform/subscriptions",
        {
            "organization": str(organization.id),
            "plan": str(plan.id),
            "start_date": str(TODAY),
            "expiry_date": str(TODAY + datetime.timedelta(days=365)),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["organization_id"] == str(organization.id)
    assert body["plan_code"] == plan.code


def test_assign_subscription_rejects_expiry_before_start():
    admin = SuperAdminFactory(password=PASSWORD)
    organization = OrganizationFactory()
    plan = SubscriptionPlanFactory()
    client = _client_as(admin)

    response = client.post(
        "/api/v1/platform/subscriptions",
        {
            "organization": str(organization.id),
            "plan": str(plan.id),
            "start_date": str(TODAY),
            "expiry_date": str(TODAY - datetime.timedelta(days=1)),
        },
    )

    assert response.status_code == 400


def test_cancel_subscription():
    admin = SuperAdminFactory(password=PASSWORD)
    subscription = SubscriptionFactory()
    client = _client_as(admin)

    response = client.post(f"/api/v1/platform/subscriptions/{subscription.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == SubscriptionStatus.CANCELLED


def test_expiry_monitor_lists_only_expiring_or_expired_current_terms():
    admin = SuperAdminFactory(password=PASSWORD)
    soon_expiring = SubscriptionFactory(expiry_date=TODAY + datetime.timedelta(days=5))
    already_expired = SubscriptionFactory(
        expiry_date=TODAY - datetime.timedelta(days=1), status=SubscriptionStatus.EXPIRED
    )
    far_out = SubscriptionFactory(expiry_date=TODAY + datetime.timedelta(days=200))
    client = _client_as(admin)

    response = client.get("/api/v1/platform/subscriptions/expiry-monitor")

    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert str(soon_expiring.id) in ids
    assert str(already_expired.id) in ids
    assert str(far_out.id) not in ids


def test_expiry_monitor_uses_only_the_most_recent_term_per_organization():
    admin = SuperAdminFactory(password=PASSWORD)
    organization = OrganizationFactory()
    plan = SubscriptionPlanFactory()
    superseded = SubscriptionFactory(
        organization=organization,
        plan=plan,
        start_date=TODAY - datetime.timedelta(days=400),
        expiry_date=TODAY - datetime.timedelta(days=30),
    )
    current = SubscriptionFactory(
        organization=organization,
        plan=plan,
        start_date=TODAY - datetime.timedelta(days=30),
        expiry_date=TODAY + datetime.timedelta(days=335),
    )
    client = _client_as(admin)

    response = client.get("/api/v1/platform/subscriptions/expiry-monitor")

    ids = {row["id"] for row in response.json()["results"]}
    assert str(superseded.id) not in ids
    assert str(current.id) not in ids  # not within the 30-day horizon either


def test_subscription_endpoints_require_super_admin():
    user = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(user)

    assert client.get("/api/v1/platform/subscriptions").status_code == 403
    assert client.get("/api/v1/platform/subscriptions/expiry-monitor").status_code == 403
