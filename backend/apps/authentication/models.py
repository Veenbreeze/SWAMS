import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ORG_ADMIN = "ORG_ADMIN", "Organization Admin"
    MANAGER = "MANAGER", "Manager"
    EMPLOYEE = "EMPLOYEE", "Employee"


class UserAccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self.create_user(email, password, **extra_fields)


class UserAccount(AbstractBaseUser, PermissionsMixin):
    """Authentication identity — see docs/02-DATABASE-ERD.md for field
    rationale and docs/01-SYSTEM-ARCHITECTURE.md §6.1 for the auth flow.

    Schema-only for now: login endpoint, JWT issuance, lockout enforcement,
    and RBAC permission classes are Phase 2 work. Created ahead of schedule
    because Django requires AUTH_USER_MODEL to exist before the first
    migration — switching custom user models after initial migrations is
    heavily discouraged, so this cannot be deferred to Phase 2 itself.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Null for SUPER_ADMIN accounts, which are platform-wide, not tenant-scoped.",
    )
    email = models.EmailField()
    employee_number = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(
        default=False,
        help_text=(
            "Set on admin-issued temporary credentials; forces a password "
            "change before any other endpoint is reachable."
        ),
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                name="unique_email_per_organization",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(organization__isnull=True),
                name="unique_email_for_platform_users",
            ),
        ]

    def __str__(self):
        return self.email
