"""Plain value objects for the attendance domain — no Django/ORM imports,
see apps/locations/domain/geofence.py for the same rationale.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GpsReading:
    latitude: float
    longitude: float
    accuracy: float
    is_mock_location: bool
