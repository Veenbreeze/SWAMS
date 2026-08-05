"""Super Admin subscription plan/term management — see
docs/03-API-SPECIFICATION.md and docs/05-DEVELOPMENT-ROADMAP.md Phase 8.

Subscription rows are never edited in place to change their term — see
`Subscription`'s docstring on why "current" is computed from `start_date`
rather than stored as a pointer. Renewing/upgrading an organization always
means creating a new row here, in `assign_subscription`.
"""

from apps.audit_logs.services import AuditLogger
from apps.subscriptions.models import Subscription, SubscriptionPlan
from core.exceptions import ApiError


class PlanCodeTakenError(ApiError):
    code = "PLAN_CODE_TAKEN"
    status_code = 400
    default_message = "A subscription plan with this code already exists."


def create_plan(*, data):
    if SubscriptionPlan.objects.filter(code__iexact=data["code"]).exists():
        raise PlanCodeTakenError()
    return SubscriptionPlan.objects.create(**data)


def update_plan(*, plan, data):
    for field, value in data.items():
        setattr(plan, field, value)
    plan.save(update_fields=[*data.keys()])
    return plan


def assign_subscription(*, organization, plan, start_date, expiry_date, actor, request=None):
    """Creates a new subscription term for `organization`.

    Deliberately does not touch `Organization.status` — an organization
    auto-suspended by `check_subscription_expiries` for running out its
    grace period stays suspended even after a fresh term is assigned here;
    reactivating it is a separate, explicit `OrganizationActivateView` call.
    Folding that into this endpoint would mean a status flip a Super Admin
    didn't ask for, and would be indistinguishable from silently undoing a
    *manual* suspension that has nothing to do with billing.
    """
    subscription = Subscription.objects.all_tenants().create(
        organization=organization,
        plan=plan,
        start_date=start_date,
        expiry_date=expiry_date,
    )

    AuditLogger.record(
        actor=actor,
        action="subscription.assigned",
        organization=organization,
        description=f"Assigned {plan.code} subscription ({start_date} to {expiry_date}).",
        request=request,
    )
    return subscription


def cancel_subscription(*, subscription, actor, request=None):
    from apps.subscriptions.models import SubscriptionStatus

    subscription.status = SubscriptionStatus.CANCELLED
    subscription.save(update_fields=["status"])

    AuditLogger.record(
        actor=actor,
        action="subscription.cancelled",
        organization=subscription.organization,
        description=f"Cancelled {subscription.plan.code} subscription.",
        request=request,
    )
    return subscription
