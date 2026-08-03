"""Org Admin staffing lifecycle — see docs/03-API-SPECIFICATION.md §4/§7
and docs/05-DEVELOPMENT-ROADMAP.md Phase 4.
"""

import secrets

from django.conf import settings
from django.db.models import Q

from apps.audit_logs.services import AuditLogger
from apps.authentication.models import Role, UserAccount
from apps.employees.models import Department, Employee, EmploymentStatus, ManagerAssignment
from core.exceptions import ApiError
from storage import supabase_client

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class DepartmentHasEmployeesError(ApiError):
    code = "DEPARTMENT_HAS_EMPLOYEES"
    status_code = 400
    default_message = "Reassign or remove this department's employees before deleting it."


class StorageUnavailableError(ApiError):
    code = "STORAGE_NOT_CONFIGURED"
    status_code = 503
    default_message = "File storage is not configured for this environment."


class EmployeeNumberTakenError(ApiError):
    code = "EMPLOYEE_NUMBER_TAKEN"
    status_code = 400
    default_message = "This employee number is already in use."


def _generate_temporary_password():
    return secrets.token_urlsafe(12)


# --- Departments ------------------------------------------------------------


def create_department(*, organization, data, actor, request=None):
    department = Department.objects.create(organization=organization, **data)
    AuditLogger.record(
        actor=actor,
        action="department.created",
        organization=organization,
        description=f"Created department {department.name}.",
        request=request,
    )
    return department


def update_department(*, department, data, actor, request=None):
    for field, value in data.items():
        setattr(department, field, value)
    department.save(update_fields=[*data.keys()])
    AuditLogger.record(
        actor=actor,
        action="department.updated",
        organization=department.organization,
        description=f"Updated fields: {', '.join(data.keys())}.",
        request=request,
    )
    return department


def delete_department(*, department, actor, request=None):
    if department.employees.exclude(employment_status=EmploymentStatus.TERMINATED).exists():
        raise DepartmentHasEmployeesError()

    organization = department.organization
    name = department.name
    department.delete()
    AuditLogger.record(
        actor=actor,
        action="department.deleted",
        organization=organization,
        description=f"Deleted department {name}.",
        request=request,
    )


# --- Employees ---------------------------------------------------------------


def create_employee(*, organization, data, actor, request=None):
    """Bootstraps the `UserAccount` + `Employee` pair in one call, mirroring
    `apps.organizations.services.create_organization`'s two-step shape.
    """
    data = dict(data)
    email = data.pop("email")
    role = data.pop("role", Role.EMPLOYEE)

    # Checked explicitly, before creating anything: the DB-level
    # UniqueConstraint(organization, employee_number) would otherwise
    # surface as a raw, uncaught IntegrityError (500) rather than a clean
    # 400, and — worse — would leave an orphaned UserAccount behind if the
    # violation were only discovered after `create_user()` below.
    if Employee.objects.all_tenants().filter(
        organization=organization, employee_number=data.get("employee_number")
    ).exists():
        raise EmployeeNumberTakenError()

    temporary_password = _generate_temporary_password()
    user = UserAccount.objects.create_user(
        email=email,
        password=temporary_password,
        organization=organization,
        role=role,
        employee_number=data.get("employee_number"),
        must_change_password=True,
    )

    employee = Employee.objects.create(organization=organization, user=user, **data)

    AuditLogger.record(
        actor=actor,
        action="employee.created",
        organization=organization,
        description=f"Created employee {employee.employee_number} ({email}).",
        request=request,
    )
    return employee, temporary_password


def update_employee(*, employee, data, actor, request=None):
    new_employee_number = data.get("employee_number")
    if new_employee_number and new_employee_number != employee.employee_number:
        if (
            Employee.objects.all_tenants()
            .filter(organization=employee.organization, employee_number=new_employee_number)
            .exclude(pk=employee.pk)
            .exists()
        ):
            raise EmployeeNumberTakenError()

    for field, value in data.items():
        setattr(employee, field, value)
    employee.save(update_fields=[*data.keys()])
    AuditLogger.record(
        actor=actor,
        action="employee.updated",
        organization=employee.organization,
        description=f"Updated fields: {', '.join(data.keys())}.",
        request=request,
    )
    return employee


def terminate_employee(*, employee, actor, request=None):
    employee.employment_status = EmploymentStatus.TERMINATED
    employee.save(update_fields=["employment_status"])
    employee.user.is_active = False
    employee.user.save(update_fields=["is_active"])

    AuditLogger.record(
        actor=actor,
        action="employee.terminated",
        organization=employee.organization,
        description=f"Terminated employee {employee.employee_number}.",
        request=request,
    )
    return employee


def reset_employee_password(*, employee, actor, request=None):
    temporary_password = _generate_temporary_password()
    user = employee.user
    user.set_password(temporary_password)
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(
        update_fields=["password", "must_change_password", "failed_login_attempts", "locked_until"]
    )

    AuditLogger.record(
        actor=actor,
        action="employee.password_reset",
        organization=employee.organization,
        description=f"Issued new temporary password for {employee.employee_number}.",
        request=request,
    )
    return temporary_password


def request_profile_picture_upload(*, employee, content_type, actor, request=None):
    extension = _CONTENT_TYPE_EXTENSIONS[content_type]
    bucket = settings.SUPABASE_STORAGE_BUCKET_PROFILE_PICTURES
    path_prefix = f"{employee.organization_id}/{employee.id}"

    try:
        upload_url, path = supabase_client.create_signed_upload_path(
            bucket=bucket, path_prefix=path_prefix, extension=extension
        )
    except supabase_client.StorageNotConfiguredError as exc:
        raise StorageUnavailableError() from exc
    except supabase_client.StorageRequestError as exc:
        raise ApiError(
            code="STORAGE_REQUEST_FAILED", status_code=502, message=str(exc)
        ) from exc

    # The final object doesn't exist until the client's direct PUT to
    # `upload_url` completes, but the path is server-generated and
    # deterministic, so it's safe to point the record at it now rather than
    # requiring a separate confirmation round-trip the API spec doesn't
    # define — a client that never uploads just leaves a 404ing image URL,
    # same as any presigned-upload flow.
    employee.profile_picture_url = supabase_client.public_url(bucket=bucket, path=path)
    employee.save(update_fields=["profile_picture_url"])

    AuditLogger.record(
        actor=actor,
        action="employee.profile_picture_requested",
        organization=employee.organization,
        description=f"Requested profile picture upload for {employee.employee_number}.",
        request=request,
    )
    return upload_url, employee.profile_picture_url


# --- Manager scoping ----------------------------------------------------------


def employees_visible_to(*, user):
    """Query filter implementing docs/01-SYSTEM-ARCHITECTURE.md §5's
    Manager scoping: Org Admin sees the whole (already tenant-filtered)
    queryset; a Manager sees only employees in an assigned department or
    directly assigned to them.
    """
    if user.role == Role.ORG_ADMIN:
        return Employee.objects.all()

    if user.role != Role.MANAGER:
        return Employee.objects.none()

    try:
        manager_employee = user.employee
    except Employee.DoesNotExist:
        return Employee.objects.none()

    assignments = ManagerAssignment.objects.filter(manager=manager_employee)
    department_ids = assignments.exclude(department=None).values_list("department_id", flat=True)
    employee_ids = assignments.exclude(employee=None).values_list("employee_id", flat=True)

    return Employee.objects.filter(Q(department_id__in=department_ids) | Q(id__in=employee_ids))


def employee_in_manager_scope(*, user, employee):
    return employees_visible_to(user=user).filter(pk=employee.pk).exists()


def approvers_for_employee(*, employee):
    """Who may approve this employee's leave requests — see
    docs/03-API-SPECIFICATION.md §9 ("Manager, Org Admin") and
    docs/05-DEVELOPMENT-ROADMAP.md Phase 7. Every Org Admin in the org,
    plus any Manager whose `ManagerAssignment` scope reaches this employee
    (by department or direct assignment) — the reverse of
    `employees_visible_to`, which goes the other way (user -> employees).
    """
    org_admins = list(
        UserAccount.objects.filter(organization=employee.organization, role=Role.ORG_ADMIN)
    )

    scope = Q(employee=employee)
    if employee.department_id:
        scope |= Q(department_id=employee.department_id)
    manager_employee_ids = ManagerAssignment.objects.filter(scope).values_list(
        "manager_id", flat=True
    )
    managers = list(
        UserAccount.objects.filter(
            organization=employee.organization,
            role=Role.MANAGER,
            employee__id__in=manager_employee_ids,
        )
    )
    return org_admins + managers
