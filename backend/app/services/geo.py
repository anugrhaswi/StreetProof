"""Geographic utilities for duplicate detection."""

from __future__ import annotations

import math


EARTH_RADIUS_METERS = 6_371_000.0


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in meters between two WGS84 points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def valid_coords(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    try:
        latf = float(lat)
        lngf = float(lng)
    except (TypeError, ValueError):
        return False
    return -90.0 <= latf <= 90.0 and -180.0 <= lngf <= 180.0 and not (math.isnan(latf) or math.isnan(lngf))
