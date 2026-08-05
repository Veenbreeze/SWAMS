import datetime

import factory

from apps.attendance.models import Attendance, AttendanceStatus, Shift
from apps.authentication.models import Role, UserAccount
from apps.employees.models import Department, Employee, ManagerAssignment
from apps.leave.models import LeaveRequest, LeaveType
from apps.locations.models import Branch
from apps.organizations.models import Organization, OrganizationStatus
from apps.subscriptions.models import Subscription, SubscriptionPlan


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    code = factory.Sequence(lambda n: f"ORG{n:04d}")
    name = factory.Faker("company")
    registration_number = factory.Sequence(lambda n: f"REG{n:06d}")
    email = factory.Faker("company_email")
    phone = factory.Faker("phone_number")
    status = OrganizationStatus.ACTIVE


class UserAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserAccount
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = Role.EMPLOYEE
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "Sup3rSecret!Pass")
        if create:
            self.save(update_fields=["password"])


class SuperAdminFactory(UserAccountFactory):
    organization = None
    role = Role.SUPER_ADMIN
    is_staff = True
    is_superuser = True


class BranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Branch

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Branch {n}")
    address = factory.Faker("address")
    latitude = "-6.792354"
    longitude = "39.208328"
    radius_meters = 100
    gps_accuracy_limit_meters = 50


class DepartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Department

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Department {n}")


class ShiftFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shift

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Shift {n}")
    start_time = datetime.time(8, 0)
    end_time = datetime.time(17, 0)


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    organization = factory.SelfAttribute("user.organization")
    user = factory.SubFactory(UserAccountFactory)
    employee_number = factory.Sequence(lambda n: f"EMP{n:04d}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    joining_date = factory.LazyFunction(datetime.date.today)


class ManagerAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ManagerAssignment

    organization = factory.SelfAttribute("manager.organization")
    manager = factory.SubFactory(EmployeeFactory)


class AttendanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attendance

    organization = factory.SelfAttribute("employee.organization")
    employee = factory.SubFactory(EmployeeFactory)
    attendance_date = factory.LazyFunction(datetime.date.today)
    status = AttendanceStatus.PRESENT
    working_minutes = 480

    @factory.lazy_attribute
    def check_in_time(self):
        return datetime.datetime.combine(
            self.attendance_date, datetime.time(8, 0), tzinfo=datetime.timezone.utc
        )


class LeaveTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeaveType

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Leave Type {n}")
    default_annual_days = 20


class LeaveRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeaveRequest

    organization = factory.SelfAttribute("employee.organization")
    employee = factory.SubFactory(EmployeeFactory)
    # Must match `employee.organization`, not a fresh unrelated org — a
    # real request could never produce this mismatch (the serializer's
    # `leave_type` field is tenant-scoped), but an untethered SubFactory
    # here would silently create one anyway on SQLite (no RLS to catch a
    # forward-FK read across a phantom tenant boundary), only surfacing as
    # `LeaveType.DoesNotExist` under real Postgres RLS.
    leave_type = factory.SubFactory(
        LeaveTypeFactory, organization=factory.SelfAttribute("..employee.organization")
    )
    start_date = factory.LazyFunction(datetime.date.today)
    end_date = factory.LazyFunction(datetime.date.today)
    reason = "Personal"


class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubscriptionPlan

    code = factory.Sequence(lambda n: f"PLAN{n:04d}")
    name = factory.Sequence(lambda n: f"Plan {n}")
    max_employees = 50
    max_branches = 5
    monthly_price = "100.00"
    grace_period_days = 7


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    organization = factory.SubFactory(OrganizationFactory)
    plan = factory.SubFactory(SubscriptionPlanFactory)
    start_date = factory.LazyFunction(datetime.date.today)
    expiry_date = factory.LazyFunction(
        lambda: datetime.date.today() + datetime.timedelta(days=30)
    )
