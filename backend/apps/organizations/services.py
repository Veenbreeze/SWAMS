"""Super Admin organization lifecycle — see docs/03-API-SPECIFICATION.md §2
and docs/05-DEVELOPMENT-ROADMAP.md Phase 3.
"""

from apps.audit_logs.services import AuditLogger
from apps.authentication.models import Role, UserAccount
from apps.leave.services import seed_default_leave_types
from apps.organizations.models import Organization, OrganizationStatus
from core.exceptions import ApiError
from core.validation import validate_password_strength


class OrganizationStatusUnchangedError(ApiError):
    code = "ORGANIZATION_STATUS_UNCHANGED"
    status_code = 400
    default_message = "The organization already has this status."


def create_organization(*, data, admin_email, admin_password, actor, request=None):
    """Creates the organization and bootstraps its first Org Admin in one
    transaction-free two-step (Organization has no FK dependency on the
    admin user, so partial failure only orphans an org, never a user).

    The Super Admin chooses `admin_password` directly (rather than the
    system generating one) — `must_change_password` still forces the Org
    Admin to set their own on first login, since a password someone else
    picked for them shouldn't stay the permanent one.
    """
    validate_password_strength(admin_password, field="admin_password")
    organization = Organization.objects.create(**data)
    seed_default_leave_types(organization=organization)

    admin = UserAccount.objects.create_user(
        email=admin_email,
        password=admin_password,
        organization=organization,
        role=Role.ORG_ADMIN,
        must_change_password=True,
    )

    AuditLogger.record(
        actor=actor,
        action="organization.created",
        organization=organization,
        description=f"Created organization {organization.code} with admin {admin.email}.",
        request=request,
    )

    return organization, admin


def update_organization(*, organization, data, actor, request=None):
    for field, value in data.items():
        setattr(organization, field, value)
    organization.save(update_fields=[*data.keys(), "updated_at"])

    AuditLogger.record(
        actor=actor,
        action="organization.updated",
        organization=organization,
        description=f"Updated fields: {', '.join(data.keys())}.",
        request=request,
    )
    return organization


def _set_status(*, organization, target_status, action, actor, request):
    if organization.status == target_status:
        raise OrganizationStatusUnchangedError()

    organization.status = target_status
    organization.save(update_fields=["status", "updated_at"])

    AuditLogger.record(
        actor=actor,
        action=action,
        organization=organization,
        description=f"Status changed to {target_status}.",
        request=request,
    )
    return organization


def suspend_organization(*, organization, actor, request=None):
    return _set_status(
        organization=organization,
        target_status=OrganizationStatus.SUSPENDED,
        action="organization.suspended",
        actor=actor,
        request=request,
    )


def activate_organization(*, organization, actor, request=None):
    return _set_status(
        organization=organization,
        target_status=OrganizationStatus.ACTIVE,
        action="organization.activated",
        actor=actor,
        request=request,
    )
