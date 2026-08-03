"""Dashboard cards — see docs/03-API-SPECIFICATION.md §13 and
docs/05-DEVELOPMENT-ROADMAP.md Phase 6. Kept separate from views.py (the
`/reports/...` endpoints) since these are a distinct, smaller surface
reusing the same aggregation services.
"""

import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.organizations.models import Organization, OrganizationStatus
from apps.reports.services import aggregations
from core.permissions.roles import IsOrgAdmin, IsSuperAdmin
from core.permissions.security import NotBlockedByPasswordChange

_TREND_DAYS = 7


class OrgAdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange, IsOrgAdmin]

    def get(self, request):
        organization = request.user.organization
        today = datetime.date.today()

        cards = aggregations.daily_summary(organization=organization, date=today)
        # LeaveRequest doesn't exist yet (Phase 7) — reported as 0 rather
        # than omitted, since the brief's dashboard card list includes it
        # and a missing key would break a client rendering a fixed set of
        # cards ahead of that phase landing.
        cards["on_leave"] = 0

        trend = [
            aggregations.daily_summary(
                organization=organization, date=today - datetime.timedelta(days=offset)
            )
            for offset in range(_TREND_DAYS - 1, -1, -1)
        ]

        return Response({"cards": cards, "trend": trend})


class EmployeeDashboardView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange]

    def get(self, request):
        employee = getattr(request.user, "employee", None)
        if employee is None:
            return Response({"today": None, "month_summary": None, "unread_notifications": 0})

        today = datetime.date.today()
        today_record = aggregations.employee_report(
            employee=employee, start_date=today, end_date=today
        )
        month_summary = aggregations.employee_report(
            employee=employee, start_date=today.replace(day=1), end_date=today
        )
        unread = Notification.objects.filter(user=request.user, is_read=False).count()

        return Response(
            {
                "today": today_record["records"][0].status if today_record["records"] else None,
                "month_summary": month_summary["totals"],
                "unread_notifications": unread,
            }
        )


class SuperAdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, NotBlockedByPasswordChange, IsSuperAdmin]

    def get(self, request):
        organizations = Organization.objects.all()
        today = datetime.date.today()
        thirty_days_ago = today - datetime.timedelta(days=30)

        return Response(
            {
                "total_organizations": organizations.count(),
                "active_organizations": organizations.filter(
                    status=OrganizationStatus.ACTIVE
                ).count(),
                "trial_organizations": organizations.filter(
                    status=OrganizationStatus.TRIAL
                ).count(),
                "suspended_organizations": organizations.filter(
                    status=OrganizationStatus.SUSPENDED
                ).count(),
                "expired_subscriptions": _subscription_status_breakdown().get("EXPIRED", 0),
                "total_users": _total_user_count(),
                "new_organizations_last_30_days": organizations.filter(
                    created_at__date__gte=thirty_days_ago
                ).count(),
                "organization_growth": _organization_growth(days=30),
                "subscription_breakdown": _subscription_status_breakdown(),
                "system_activity": _system_activity(days=7),
            }
        )


def _expired_subscription_count():
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    return Subscription.objects.all_tenants().filter(status=SubscriptionStatus.EXPIRED).count()


def _total_user_count():
    from apps.authentication.models import UserAccount

    return UserAccount.objects.count()


def _organization_growth(*, days):
    """New organizations created per day over the trailing window — the
    "org growth" chart per docs/05-DEVELOPMENT-ROADMAP.md Phase 6's Super
    Admin Web bullet.
    """
    from django.db.models import Count

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    counts_by_date = dict(
        Organization.objects.filter(created_at__date__gte=start)
        .values_list("created_at__date")
        .annotate(count=Count("id"))
    )
    return [
        {
            "date": (start + datetime.timedelta(days=offset)).isoformat(),
            "count": counts_by_date.get(start + datetime.timedelta(days=offset), 0),
        }
        for offset in range(days)
    ]


def _subscription_status_breakdown():
    """Each organization's *current* (most recent by `start_date`)
    subscription status, counted — not a raw count of `Subscription` rows
    (an org can have several over its lifetime), via a correlated
    subquery so this stays one query regardless of organization count.
    """
    from django.db.models import Count, OuterRef, Subquery

    from apps.subscriptions.models import Subscription

    latest_status = (
        Subscription.objects.all_tenants()
        .filter(organization=OuterRef("pk"))
        .order_by("-start_date")
        .values("status")[:1]
    )
    rows = (
        Organization.objects.annotate(current_sub_status=Subquery(latest_status))
        .values("current_sub_status")
        .annotate(count=Count("id"))
    )
    # `None` covers organizations with no Subscription row at all yet.
    return {(row["current_sub_status"] or "NONE"): row["count"] for row in rows}


def _system_activity(*, days):
    """Platform-wide `AuditLog` volume per day — the "system activity"
    chart. Read via `.all_tenants()` since this deliberately spans every
    organization, not just the (nonexistent, for a Super Admin) caller's
    own tenant.
    """
    from django.db.models import Count
    from django.db.models.functions import TruncDate

    from apps.audit_logs.models import AuditLog

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    counts_by_date = dict(
        AuditLog.objects.all_tenants()
        .filter(timestamp__date__gte=start)
        .annotate(day=TruncDate("timestamp"))
        .values_list("day")
        .annotate(count=Count("id"))
    )
    return [
        {
            "date": (start + datetime.timedelta(days=offset)).isoformat(),
            "count": counts_by_date.get(start + datetime.timedelta(days=offset), 0),
        }
        for offset in range(days)
    ]
