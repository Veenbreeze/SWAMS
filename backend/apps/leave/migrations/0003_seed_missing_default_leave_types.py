from django.db import migrations

# Mirrors apps.leave.services.DEFAULT_LEAVE_TYPES at the time this
# migration was written — duplicated rather than imported, since data
# migrations must not depend on app code that can change out from under
# them later; only organizations/orgs created before that seeding step
# existed are missing these rows.
DEFAULT_LEAVE_TYPES = [
    {"name": "Annual Leave", "default_annual_days": 21, "requires_approval": True},
    {"name": "Sick Leave", "default_annual_days": 14, "requires_approval": True},
    {"name": "Unpaid Leave", "default_annual_days": 0, "requires_approval": True},
]


def seed_missing_leave_types(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    LeaveType = apps.get_model("leave", "LeaveType")

    orgs_with_types = set(
        LeaveType.objects.values_list("organization_id", flat=True).distinct()
    )
    for organization in Organization.objects.exclude(id__in=orgs_with_types):
        LeaveType.objects.bulk_create(
            [LeaveType(organization=organization, **defaults) for defaults in DEFAULT_LEAVE_TYPES]
        )


def noop_reverse(apps, schema_editor):
    # Deliberately not removing seeded rows on reverse — by the time this
    # would be reversed, real leave requests may already reference them
    # (LeaveRequest.leave_type is on_delete=RESTRICT), and an org admin
    # may have already renamed/edited them into real, in-use data.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("leave", "0002_enable_row_level_security"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_missing_leave_types, noop_reverse),
    ]
