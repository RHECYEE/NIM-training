"""Small pure-Python geodesy helpers.

No third-party dependencies on purpose: these scripts have to run on a plain
Python install (a GISS laptop, a CI box) before anyone has ArcGIS Pro open.
Anything that genuinely needs arcpy lives under ``scripts/arcpy/``.

Ellipsoid is GRS80, which is what NAD 1983 / EPSG:26913 uses.
"""

from __future__ import annotations

import math

A = 6378137.0                 # GRS80 semi-major axis (m)
F = 1.0 / 298.257222101       # GRS80 flattening
E2 = F * (2.0 - F)
EP2 = E2 / (1.0 - E2)
K0 = 0.9996                   # UTM scale factor
METERS_PER_MILE = 1609.344
SQM_PER_ACRE = 4046.8564224


def utm_zone_central_meridian(zone: int) -> float:
    return math.radians(zone * 6 - 183)


def ll_to_utm(lat: float, lon: float, zone: int = 13, northern: bool = True):
    """Geographic (decimal degrees, NAD83) -> UTM easting/northing in metres."""
    lon0 = utm_zone_central_meridian(zone)
    la, lo = math.radians(lat), math.radians(lon)

    n = A / math.sqrt(1.0 - E2 * math.sin(la) ** 2)
    t = math.tan(la) ** 2
    c = EP2 * math.cos(la) ** 2
    a_ = math.cos(la) * (lo - lon0)

    e4, e6 = E2 * E2, E2 * E2 * E2
    m = A * (
        (1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * la
        - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * la)
        + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * la)
        - (35 * e6 / 3072) * math.sin(6 * la)
    )

    easting = K0 * n * (
        a_
        + (1 - t + c) * a_ ** 3 / 6
        + (5 - 18 * t + t * t + 72 * c - 58 * EP2) * a_ ** 5 / 120
    ) + 500000.0

    northing = K0 * (
        m
        + n * math.tan(la) * (
            a_ * a_ / 2
            + (5 - t + 9 * c + 4 * c * c) * a_ ** 4 / 24
            + (61 - 58 * t + t * t + 600 * c - 330 * EP2) * a_ ** 6 / 720
        )
    )
    if not northern:
        northing += 10000000.0
    return easting, northing


def utm_to_ll(easting: float, northing: float, zone: int = 13, northern: bool = True):
    """Inverse of :func:`ll_to_utm`."""
    x = easting - 500000.0
    y = northing if northern else northing - 10000000.0

    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    m = y / K0
    mu = m / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))

    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
        + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
        + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
        + (1097 * e1 ** 4 / 512) * math.sin(8 * mu)
    )

    c1 = EP2 * math.cos(phi1) ** 2
    t1 = math.tan(phi1) ** 2
    n1 = A / math.sqrt(1 - E2 * math.sin(phi1) ** 2)
    r1 = A * (1 - E2) / (1 - E2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * K0)

    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d * d / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * EP2 - 3 * c1 * c1) * d ** 6 / 720
    )
    lon = utm_zone_central_meridian(zone) + (
        d
        - (1 + 2 * t1 + c1) * d ** 3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * EP2 + 24 * t1 * t1) * d ** 5 / 120
    ) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)


def project_ring(ring, zone: int = 13):
    """[[lon, lat], ...] -> [(easting, northing), ...]."""
    return [ll_to_utm(lat, lon, zone) for lon, lat in ring]


def ring_area_sqm(ring, zone: int = 13) -> float:
    """Planimetric area of a closed lon/lat ring, via the UTM shoelace."""
    pts = project_ring(ring, zone)
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def ring_area_acres(ring, zone: int = 13) -> float:
    return ring_area_sqm(ring, zone) / SQM_PER_ACRE


def line_length_m(coords, zone: int = 13) -> float:
    pts = project_ring(coords, zone)
    return sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:]))


def line_length_miles(coords, zone: int = 13) -> float:
    return line_length_m(coords, zone) / METERS_PER_MILE


def dd_to_dm(value: float, is_lat: bool) -> str:
    """Decimal degrees -> degrees/decimal-minutes, the form used on IAP grids."""
    hemi = ("N" if value >= 0 else "S") if is_lat else ("E" if value >= 0 else "W")
    value = abs(value)
    deg = int(value)
    minutes = (value - deg) * 60.0
    return f"{deg}°{minutes:06.3f}' {hemi}"


def dd_to_dms(value: float, is_lat: bool) -> str:
    """Decimal degrees -> degrees/minutes/seconds, the form used on air ops tables."""
    hemi = ("N" if value >= 0 else "S") if is_lat else ("E" if value >= 0 else "W")
    value = abs(value)
    deg = int(value)
    minutes_full = (value - deg) * 60.0
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60.0
    return f"{deg}°{minutes:02d}'{seconds:04.1f}\" {hemi}"
