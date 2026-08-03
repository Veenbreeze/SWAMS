import math

import pytest

from apps.locations.domain.geofence import haversine_distance_meters, is_within_geofence

DAR_ES_SALAAM = (-6.792354, 39.208328)


def test_distance_between_identical_points_is_zero():
    assert haversine_distance_meters(*DAR_ES_SALAAM, *DAR_ES_SALAAM) == 0


def test_distance_for_one_degree_of_latitude_matches_known_value():
    # One degree of latitude on a sphere of Earth's mean radius is exactly
    # R * (pi / 180) — a known, independently-computable value to check
    # the formula against, not just against itself.
    distance = haversine_distance_meters(0, 0, 1, 0)
    expected = 6_371_000 * math.pi / 180
    assert distance == pytest.approx(expected, rel=1e-9)


def test_distance_is_symmetric():
    lat1, lon1 = DAR_ES_SALAAM
    lat2, lon2 = -6.800000, 39.200000
    assert haversine_distance_meters(lat1, lon1, lat2, lon2) == pytest.approx(
        haversine_distance_meters(lat2, lon2, lat1, lon1)
    )


def test_accepts_decimal_and_string_inputs():
    from decimal import Decimal

    distance = haversine_distance_meters(Decimal("0"), Decimal("0"), "1", "0")
    assert distance == pytest.approx(6_371_000 * math.pi / 180, rel=1e-9)


def test_geofence_boundary_is_inclusive():
    lat1, lon1 = DAR_ES_SALAAM
    lat2, lon2 = -6.793000, 39.209000
    distance = haversine_distance_meters(lat1, lon1, lat2, lon2)

    kwargs = dict(lat=lat1, lon=lon1, branch_lat=lat2, branch_lon=lon2)
    assert is_within_geofence(**kwargs, radius_meters=distance) is True  # exactly at radius
    assert is_within_geofence(**kwargs, radius_meters=distance - 1) is False  # 1m outside
    assert is_within_geofence(**kwargs, radius_meters=distance + 1) is True  # 1m inside
