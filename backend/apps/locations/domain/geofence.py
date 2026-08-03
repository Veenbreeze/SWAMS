"""Pure geofencing math — see docs/01-SYSTEM-ARCHITECTURE.md §7.

No Django/ORM imports on purpose: this is the one piece of real,
test-worthy domain logic in this app (per docs/04-PROJECT-STRUCTURE.md's
rationale for why `locations` gets a `domain/` layer and plain CRUD apps
don't), and it needs to be unit-testable against known coordinate pairs
independent of the database.
"""

import math

EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in meters."""
    lat1, lon1, lat2, lon2 = (float(lat1), float(lon1), float(lat2), float(lon2))
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def is_within_geofence(*, lat, lon, branch_lat, branch_lon, radius_meters):
    """Inclusive boundary: exactly-at-radius counts as inside — see
    docs/05-DEVELOPMENT-ROADMAP.md Phase 5's boundary-case test requirement
    ("exactly at radius, 1m inside/outside"), which only makes sense against
    a documented, deliberate `<=`.
    """
    return haversine_distance_meters(lat, lon, branch_lat, branch_lon) <= radius_meters
