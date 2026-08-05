"""Leave submit -> approve/reject/cancel workflow — see
docs/03-API-SPECIFICATION.md §9 and docs/05-DEVELOPMENT-ROADMAP.md Phase 7.

Balance arithmetic only ever happens in two places: `approve` (decrement)
and `cancel` of an already-`APPROVED` request (restore) — `submit` and
`reject` never touch `LeaveBalance` at all, so there is exactly one code
path that can double-count or leak a balance change, not several.
"""

import datetime

from apps.audit_logs.services import AuditLogger
from apps.employees.services import approvers_for_employee
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveRequestStatus, LeaveType
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationDispatcher
from core.exceptions import ApiError

# Starter set every organization gets so employees have something to pick
# from immediately — an Org Admin can rename/add/remove types afterward
# (LeaveType is a per-org table precisely so they can); this just avoids
# a brand-new org's leave-request screen showing zero options on day one.
DEFAULT_LEAVE_TYPES = [
    {"name": "Annual Leave", "default_annual_days": 21, "requires_approval": True},
    {"name": "Sick Leave", "default_annual_days": 14, "requires_approval": True},
    {"name": "Unpaid Leave", "default_annual_days": 0, "requires_approval": True},
]


def seed_default_leave_types(*, organization):
    LeaveType.objects.bulk_create(
        [LeaveType(organization=organization, **defaults) for defaults in DEFAULT_LEAVE_TYPES]
    )


def create_leave_type(*, organization, data, actor, request=None):
    leave_type = LeaveType.objects.create(organization=organization, **data)
    AuditLogger.record(
        actor=actor,
        action="leave_type.created",
        organization=organization,
        description=f"Created leave type {leave_type.name}.",
        request=request,
    )
    return leave_type


def update_leave_type(*, leave_type, data, actor, request=None):
    for field, value in data.items():
        setattr(leave_type, field, value)
    leave_type.save(update_fields=[*data.keys()])
    AuditLogger.record(
        actor=actor,
        action="leave_type.updated",
        organization=leave_type.organization,
        description=f"Updated fields: {', '.join(data.keys())}.",
        request=request,
    )
    return leave_type


class InvalidDateRangeError(ApiError):
    code = "INVALID_DATE_RANGE"
    status_code = 400
    default_message = "end_date must be on or after start_date."


class LeaveRequestNotEditableError(ApiError):
    code = "LEAVE_REQUEST_NOT_EDITABLE"
    status_code = 400
    default_message = "This leave request can no longer be edited or withdrawn."


class LeaveRequestNotPendingError(ApiError):
    code = "LEAVE_REQUEST_NOT_PENDING"
    status_code = 400
    default_message = "This leave request has already been decided."


class LeaveRequestNotCancellableError(ApiError):
    code = "LEAVE_REQUEST_NOT_CANCELLABLE"
    status_code = 400
    default_message = "Only a pending or approved leave request can be cancelled."


def get_or_create_balance(*, employee, leave_type, year):
    balance, _ = LeaveBalance.objects.all_tenants().get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={
            "organization": employee.organization,
            "allocated_days": leave_type.default_annual_days,
        },
    )
    return balance


def _notify_submitted(leave_request):
    for approver in approvers_for_employee(employee=leave_request.employee):
        NotificationDispatcher.notify(
            user=approver,
            category=NotificationCategory.LEAVE,
            title="New leave request",
            message=(
                f"{leave_request.employee.full_name} requested "
                f"{leave_request.days_requested} day(s) of {leave_request.leave_type.name}."
            ),
        )


def _notify_decided(leave_request):
    # Leave *decisions* are one of the roadmap's explicit email-worthy
    # events (unlike the submission step above, which stays in-app + push
    # for the approver) — see apps/notifications/services/email.py.
    verb = "approved" if leave_request.status == LeaveRequestStatus.APPROVED else "rejected"
    NotificationDispatcher.notify(
        user=leave_request.employee.user,
        category=NotificationCategory.LEAVE,
        title=f"Leave request {verb}",
        message=f"Your {leave_request.leave_type.name} request was {verb}.",
        send_email=True,
    )


def submit_leave_request(*, employee, leave_type, start_date, end_date, reason):
    if end_date < start_date:
        raise InvalidDateRangeError()

    leave_request = LeaveRequest.objects.create(
        organization=employee.organization,
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )

    _notify_submitted(leave_request)
    return leave_request


def update_leave_request(*, leave_request, data):
    if leave_request.status != LeaveRequestStatus.PENDING:
        raise LeaveRequestNotEditableError()

    for field, value in data.items():
        setattr(leave_request, field, value)
    if leave_request.end_date < leave_request.start_date:
        raise InvalidDateRangeError()
    leave_request.save(update_fields=[*data.keys()])
    return leave_request


def approve_leave_request(*, leave_request, actor, request=None):
    if leave_request.status != LeaveRequestStatus.PENDING:
        raise LeaveRequestNotPendingError()

    balance = get_or_create_balance(
        employee=leave_request.employee,
        leave_type=leave_request.leave_type,
        year=leave_request.start_date.year,
    )
    balance.used_days += leave_request.days_requested
    balance.save(update_fields=["used_days"])

    leave_request.status = LeaveRequestStatus.APPROVED
    leave_request.approved_by = actor
    leave_request.decided_at = datetime.datetime.now(datetime.timezone.utc)
    leave_request.save(update_fields=["status", "approved_by", "decided_at"])

    AuditLogger.record(
        actor=actor,
        action="leave_request.approved",
        organization=leave_request.organization,
        description=(
            f"Approved {leave_request.leave_type.name} for "
            f"{leave_request.employee.full_name}."
        ),
        request=request,
    )
    _notify_decided(leave_request)
    return leave_request


def reject_leave_request(*, leave_request, actor, reason, request=None):
    if leave_request.status != LeaveRequestStatus.PENDING:
        raise LeaveRequestNotPendingError()

    leave_request.status = LeaveRequestStatus.REJECTED
    leave_request.approved_by = actor
    leave_request.decision_reason = reason
    leave_request.decided_at = datetime.datetime.now(datetime.timezone.utc)
    leave_request.save(
        update_fields=["status", "approved_by", "decision_reason", "decided_at"]
    )

    AuditLogger.record(
        actor=actor,
        action="leave_request.rejected",
        organization=leave_request.organization,
        description=(
            f"Rejected {leave_request.leave_type.name} for "
            f"{leave_request.employee.full_name}: {reason}"
        ),
        request=request,
    )
    _notify_decided(leave_request)
    return leave_request


def cancel_leave_request(*, leave_request, actor, request=None):
    """PENDING -> CANCELLED never touches the balance (nothing was ever
    decremented). APPROVED -> CANCELLED restores the days it had consumed
    — see docs/05-DEVELOPMENT-ROADMAP.md's "restored on later cancellation
    if applicable".
    """
    if leave_request.status not in (LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED):
        raise LeaveRequestNotCancellableError()

    was_approved = leave_request.status == LeaveRequestStatus.APPROVED
    if was_approved:
        balance = get_or_create_balance(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
        )
        balance.used_days -= leave_request.days_requested
        balance.save(update_fields=["used_days"])

    leave_request.status = LeaveRequestStatus.CANCELLED
    leave_request.save(update_fields=["status"])

    if was_approved and actor.id != leave_request.employee.user_id:
        # Only audit-logged (as an admin action) when someone other than
        # the employee cancels an already-approved request — the
        # employee withdrawing their own still-PENDING request is routine
        # self-service, same as submitting it in the first place.
        AuditLogger.record(
            actor=actor,
            action="leave_request.cancelled",
            organization=leave_request.organization,
            description=(
                f"Cancelled approved {leave_request.leave_type.name} for "
                f"{leave_request.employee.full_name}."
            ),
            request=request,
        )
    return leave_request
