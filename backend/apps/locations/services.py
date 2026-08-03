"""Org Admin branch management — see docs/03-API-SPECIFICATION.md §5 and
docs/05-DEVELOPMENT-ROADMAP.md Phase 4.
"""

from apps.audit_logs.services import AuditLogger
from apps.locations.models import Branch


def create_branch(*, organization, data, actor, request=None):
    data = dict(data)
    data.pop("gps_accuracy", None)  # validation-only, see serializers._GpsAccuracyMixin
    branch = Branch.objects.create(organization=organization, **data)

    AuditLogger.record(
        actor=actor,
        action="branch.created",
        organization=organization,
        description=f"Created branch {branch.name}.",
        request=request,
    )
    return branch


def update_branch(*, branch, data, actor, request=None):
    for field, value in data.items():
        setattr(branch, field, value)
    branch.save(update_fields=[*data.keys()])

    AuditLogger.record(
        actor=actor,
        action="branch.updated",
        organization=branch.organization,
        description=f"Updated fields: {', '.join(data.keys())}.",
        request=request,
    )
    return branch


def capture_branch_location(*, branch, data, actor, request=None):
    branch.latitude = data["latitude"]
    branch.longitude = data["longitude"]
    branch.save(update_fields=["latitude", "longitude"])

    AuditLogger.record(
        actor=actor,
        action="branch.location_captured",
        organization=branch.organization,
        description=f"Captured location for branch {branch.name}.",
        request=request,
    )
    return branch


def delete_branch(*, branch, actor, request=None):
    organization = branch.organization
    name = branch.name
    branch.delete()

    AuditLogger.record(
        actor=actor,
        action="branch.deleted",
        organization=organization,
        description=f"Deleted branch {name}.",
        request=request,
    )
