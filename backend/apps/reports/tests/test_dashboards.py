import datetime

import pytest
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRule, AttendanceStatus
from apps.authentication.models import Role
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationDispatcher
from apps.organizations.models import OrganizationStatus
from apps.subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
from tests.factories import (
    AttendanceFactory,
    EmployeeFactory,
    OrganizationFactory,
    SuperAdminFactory,
    UserAccountFactory,
)

pytestmark = pytest.mark.django_db

PASSWORD = "Sup3rSecret!Pass"


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


def test_org_admin_dashboard_returns_cards_and_trend():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    AttendanceRule.objects.all_tenants().create(
        organization=admin.organization, working_days=[0, 1, 2, 3, 4, 5, 6]
    )
    employee = EmployeeFactory(user__organization=admin.organization)
    AttendanceFactory(
        employee=employee, attendance_date=datetime.date.today(), status=AttendanceStatus.PRESENT
    )
    client = _client_as(admin)

    response = client.get("/api/v1/dashboard/org-admin")

    assert response.status_code == 200
    body = response.json()
    assert body["cards"]["present"] == 1
    assert body["cards"]["on_leave"] == 0
    assert len(body["trend"]) == 7


def test_employee_cannot_access_org_admin_dashboard():
    employee = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    client = _client_as(employee)

    response = client.get("/api/v1/dashboard/org-admin")

    assert response.status_code == 403


def test_employee_dashboard_returns_today_status_and_unread_count():
    user = UserAccountFactory(password=PASSWORD, role=Role.EMPLOYEE)
    employee = EmployeeFactory(user=user)
    AttendanceFactory(
        employee=employee, attendance_date=datetime.date.today(), status=AttendanceStatus.LATE
    )
    NotificationDispatcher.notify(user=user, category=NotificationCategory.ATTENDANCE, title="Hi")
    client = _client_as(user)

    response = client.get("/api/v1/dashboard/employee")

    assert response.status_code == 200
    body = response.json()
    assert body["today"] == "LATE"
    assert body["unread_notifications"] == 1
    assert body["month_summary"]["days_present"] == 1


def test_employee_dashboard_handles_org_admin_with_no_employee_profile():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.get("/api/v1/dashboard/employee")

    assert response.status_code == 200
    assert response.json()["today"] is None


def test_super_admin_dashboard_returns_platform_stats():
    super_admin = SuperAdminFactory(password=PASSWORD)
    OrganizationFactory(status=OrganizationStatus.ACTIVE)
    OrganizationFactory(status=OrganizationStatus.SUSPENDED)
    expired_org = OrganizationFactory(status=OrganizationStatus.ACTIVE)
    plan = SubscriptionPlan.objects.create(
        code="BASIC", name="Basic", max_employees=10, max_branches=1, monthly_price="10.00"
    )
    Subscription.objects.all_tenants().create(
        organization=expired_org,
        plan=plan,
        status=SubscriptionStatus.EXPIRED,
        start_date="2025-01-01",
        expiry_date="2025-06-01",
    )
    client = _client_as(super_admin)

    response = client.get("/api/v1/dashboard/super-admin")

    assert response.status_code == 200
    body = response.json()
    assert body["total_organizations"] == 3
    assert body["active_organizations"] == 2
    assert body["suspended_organizations"] == 1
    assert body["expired_subscriptions"] == 1
    assert body["subscription_breakdown"]["EXPIRED"] == 1
    assert len(body["organization_growth"]) == 30
    assert sum(day["count"] for day in body["organization_growth"]) == 3
    assert len(body["system_activity"]) == 7


def test_subscription_breakdown_reflects_each_orgs_most_recent_subscription():
    super_admin = SuperAdminFactory(password=PASSWORD)
    org = OrganizationFactory()
    plan = SubscriptionPlan.objects.create(
        code="PRO", name="Pro", max_employees=50, max_branches=5, monthly_price="50.00"
    )
    # Older EXPIRED subscription, then a newer ACTIVE one for the same
    # org — the breakdown should reflect the org's *current* status only.
    Subscription.objects.all_tenants().create(
        organization=org,
        plan=plan,
        status=SubscriptionStatus.EXPIRED,
        start_date="2025-01-01",
        expiry_date="2025-06-01",
    )
    Subscription.objects.all_tenants().create(
        organization=org,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        start_date="2026-01-01",
        expiry_date="2026-12-31",
    )
    client = _client_as(super_admin)

    response = client.get("/api/v1/dashboard/super-admin")

    breakdown = response.json()["subscription_breakdown"]
    assert breakdown.get("ACTIVE", 0) == 1
    assert breakdown.get("EXPIRED", 0) == 0


def test_org_admin_cannot_access_super_admin_dashboard():
    admin = UserAccountFactory(password=PASSWORD, role=Role.ORG_ADMIN)
    client = _client_as(admin)

    response = client.get("/api/v1/dashboard/super-admin")

    assert response.status_code == 403
