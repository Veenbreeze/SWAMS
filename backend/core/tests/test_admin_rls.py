"""Confirms AdminSessionRlsMiddleware actually fixes what it claims to:
editing an existing tenant-scoped row via Django Admin. Skipped outside
Postgres for the same reason as core/tests/test_row_level_security.py —
RLS doesn't exist on SQLite, so there's nothing this test would catch
there (and it would trivially "pass" for the wrong reason).
"""

import pytest
from django.db import connection
from django.test import Client

from tests.factories import BranchFactory, SuperAdminFactory

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="RLS policies only exist on Postgres; local/CI default to SQLite.",
    ),
]


def _connected_as_superuser():
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        return cursor.fetchone()[0]


@pytest.fixture(autouse=True)
def _skip_if_superuser():
    if connection.vendor == "postgresql" and _connected_as_superuser():
        pytest.skip("Connected as a Postgres superuser — RLS is bypassed unconditionally.")


def test_admin_can_edit_an_existing_tenant_scoped_row():
    branch = BranchFactory(name="Old Name")
    admin = SuperAdminFactory(password="Sup3rSecret!Pass")

    client = Client()
    client.force_login(admin)

    response = client.post(
        f"/admin/locations/branch/{branch.id}/change/",
        {
            "organization": str(branch.organization_id),
            "name": "New Name",
            "address": branch.address,
            "latitude": branch.latitude,
            "longitude": branch.longitude,
            "radius_meters": branch.radius_meters,
            "gps_accuracy_limit_meters": branch.gps_accuracy_limit_meters,
            "is_active": "on",
            "_save": "Save",
        },
    )

    # A redirect (302) means the admin's save succeeded; a re-rendered
    # form (200) means validation or the RLS-blocked save failed.
    assert response.status_code == 302, response.content

    branch.refresh_from_db()
    assert branch.name == "New Name"
