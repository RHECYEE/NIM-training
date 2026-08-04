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


def point_segment_distance(px, py, ax, ay, bx, by):
    """Distance from a point to a line segment, and how far along the segment
    the closest approach falls (0..1). Planar — feed it UTM metres."""
    dx, dy = bx - ax, by - ay
    seg_sq = dx * dx + dy * dy
    if seg_sq == 0.0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_sq))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), t


def point_to_polyline_distance(px, py, polyline_utm):
    """Shortest distance from a point to any segment of a polyline."""
    best = float("inf")
    for (ax, ay), (bx, by) in zip(polyline_utm, polyline_utm[1:]):
        d, _ = point_segment_distance(px, py, ax, ay, bx, by)
        if d < best:
            best = d
    return best


def distance_along_polyline(px, py, polyline_utm):
    """How far along a polyline a point projects. Used to order drop points the
    way a driver encounters them, rather than the order they were drawn."""
    best_d, best_along = float("inf"), 0.0
    travelled = 0.0
    for (ax, ay), (bx, by) in zip(polyline_utm, polyline_utm[1:]):
        seg_len = math.hypot(bx - ax, by - ay)
        d, t = point_segment_distance(px, py, ax, ay, bx, by)
        if d < best_d:
            best_d, best_along = d, travelled + t * seg_len
        travelled += seg_len
    return best_along, best_d


def densify_utm(polyline_utm, spacing_m: float = 25.0):
    """Insert vertices so proximity tests do not step over a short approach.

    A two-vertex trail segment a kilometre long has no vertex near the fire even
    when its middle runs straight down the perimeter; without this, that segment
    is invisible to the buffer test.
    """
    if len(polyline_utm) < 2:
        return list(polyline_utm)
    out = [polyline_utm[0]]
    for (ax, ay), (bx, by) in zip(polyline_utm, polyline_utm[1:]):
        seg = math.hypot(bx - ax, by - ay)
        steps = max(1, int(seg // spacing_m))
        for i in range(1, steps):
            t = i / steps
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        out.append((bx, by))
    return out


def runs_of_true(flags, min_run: int = 1):
    """Maximal runs of True in a boolean list, as (start, end_exclusive)."""
    runs, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if i - start >= min_run:
                runs.append((start, i))
            start = None
    if start is not None and len(flags) - start >= min_run:
        runs.append((start, len(flags)))
    return runs


def centroid(coords, zone: int = 13):
    """Mean of the vertices, in UTM. Good enough to anchor a transform on."""
    pts = project_ring(coords, zone)
    return sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)


class Similarity:
    """Rotate + scale + translate, applied in UTM.

    Used to place one hand-built template scenario at seven different fires:
    rotate to the fire's run bearing, scale to its size, translate to its
    centre. Doing it in UTM rather than in lon/lat keeps the shape from
    shearing — a degree of longitude is not a degree of latitude.
    """

    def __init__(self, src_center_ll, dst_center_ll, rotation_deg, scale, zone: int = 13):
        self.zone = zone
        self.sx, self.sy = ll_to_utm(src_center_ll[0], src_center_ll[1], zone)
        self.dx, self.dy = ll_to_utm(dst_center_ll[0], dst_center_ll[1], zone)
        theta = math.radians(rotation_deg)
        self.cos_t, self.sin_t = math.cos(theta), math.sin(theta)
        self.scale = scale

    def point_utm(self, x: float, y: float):
        x, y = (x - self.sx) * self.scale, (y - self.sy) * self.scale
        return (
            self.dx + x * self.cos_t - y * self.sin_t,
            self.dy + x * self.sin_t + y * self.cos_t,
        )

    def __call__(self, coords):
        """[[lon, lat], ...] -> [[lon, lat], ...], rounded for output."""
        out = []
        for lon, lat in coords:
            x, y = ll_to_utm(lat, lon, self.zone)
            nlat, nlon = utm_to_ll(*self.point_utm(x, y), self.zone)
            out.append([round(nlon, 6), round(nlat, 6)])
        return out

    def point(self, lon: float, lat: float):
        return self([[lon, lat]])[0]


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
