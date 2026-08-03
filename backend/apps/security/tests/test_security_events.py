import pytest

from apps.security.models import SecurityEvent, SecurityEventType
from apps.security.services import SecurityEventLogger
from core.db import rls
from tests.factories import UserAccountFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_rls_after():
    # `SecurityEventLogger.record()` is called directly here, outside any
    # authenticated request — on Postgres, reading the row back via
    # `.all_tenants()` still requires the RLS session to be bound (`INSERT`
    # is permissive, but `SELECT`/`get()` is not); a real request would
    # have bound this via `TenantAwareJWTAuthentication`. See
    # core/tests/test_row_level_security.py for the same pattern.
    yield
    rls.reset()


def test_record_creates_event_scoped_to_actors_organization():
    user = UserAccountFactory()

    SecurityEventLogger.record(
        event_type=SecurityEventType.MOCK_LOCATION_DETECTED,
        user=user,
        description="Mock location flagged during check-in.",
        metadata={"device_id": "abc123"},
    )

    rls.bind(platform_wide=True)
    event = SecurityEvent.objects.all_tenants().get()
    assert event.organization_id == user.organization_id
    assert event.user_id == user.id
    assert event.event_type == SecurityEventType.MOCK_LOCATION_DETECTED
    assert event.metadata == {"device_id": "abc123"}


def test_record_accepts_explicit_organization_override():
    user = UserAccountFactory()

    SecurityEventLogger.record(
        event_type=SecurityEventType.IMPLAUSIBLE_TRAVEL_SPEED,
        organization=user.organization,
        user=None,
        description="System-detected, no single user attributable.",
    )

    rls.bind(platform_wide=True)
    event = SecurityEvent.objects.all_tenants().get()
    assert event.organization_id == user.organization_id
    assert event.user is None
