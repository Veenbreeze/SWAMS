import factory

from apps.authentication.models import Role, UserAccount
from apps.organizations.models import Organization, OrganizationStatus


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
