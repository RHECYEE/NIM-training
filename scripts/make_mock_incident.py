#!/usr/bin/env python3
"""Generate the fabricated Storm Mountain incident as three GeoJSON files.

    python3 scripts/make_mock_incident.py

Output lands in ``data/mock_incident/`` and is the input to
``scripts/arcpy/load_mock_incident.py``, which pushes it into the Event GDB.

Everything here is invented. The geometry is placed inside the real AOI so the
exercise sits on real terrain, real roads and real ownership, but no perimeter,
line or point below describes anything that ever happened.

Acreages and line mileages are computed from the geometry, never asserted, so
the number on the map and the number in the attribute table cannot drift apart.

Scenario
--------
Ignition on the west side of the AOI, wind-driven run to the northeast over two
burning periods. The head is pointed at the Storm Mountain Training Grounds,
which makes the camp a value at risk and makes the single winding access road
the constraint the exercise is actually about.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import (  # noqa: E402
    ll_to_utm,
    line_length_miles,
    ring_area_acres,
    utm_to_ll,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "mock_incident"
INCIDENT = json.loads((ROOT / "config" / "incident.json").read_text())
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())

INCIDENT_NAME = INCIDENT["incident_name"]
CREATE_NAME = INCIDENT["giss"]
CREATE_DATE = INCIDENT["map_prepared"]["prepared_iso"]
NM_TO_M = 1852.0


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

# Today's perimeter (op 3). Head to the northeast.
PERIMETER_TODAY = [
    [-103.4180, 43.9430],
    [-103.4230, 43.9490],
    [-103.4245, 43.9560],
    [-103.4210, 43.9625],
    [-103.4130, 43.9680],
    [-103.4040, 43.9715],
    [-103.3950, 43.9730],
    [-103.3880, 43.9705],
    [-103.3845, 43.9655],
    [-103.3860, 43.9590],
    [-103.3915, 43.9540],
    [-103.3980, 43.9495],
    [-103.4050, 43.9455],
    [-103.4120, 43.9425],
    [-103.4180, 43.9430],
]

# Yesterday's perimeter (op 2) — same origin, shorter run. Drives the
# progression product.
PERIMETER_YESTERDAY = [
    [-103.4165, 43.9455],
    [-103.4200, 43.9500],
    [-103.4205, 43.9555],
    [-103.4170, 43.9600],
    [-103.4105, 43.9635],
    [-103.4035, 43.9650],
    [-103.3975, 43.9635],
    [-103.3945, 43.9595],
    [-103.3960, 43.9550],
    [-103.4010, 43.9505],
    [-103.4075, 43.9470],
    [-103.4130, 43.9450],
    [-103.4165, 43.9455],
]

# Day one (op 1).
PERIMETER_DAY_ONE = [
    [-103.4150, 43.9480],
    [-103.4170, 43.9515],
    [-103.4160, 43.9550],
    [-103.4120, 43.9575],
    [-103.4070, 43.9580],
    [-103.4030, 43.9560],
    [-103.4025, 43.9525],
    [-103.4060, 43.9495],
    [-103.4110, 43.9478],
    [-103.4150, 43.9480],
]

# The active edge: the northeast third of today's perimeter, running clockwise
# from the north shoulder around the head to the east shoulder.
UNCONTROLLED_EDGE = [
    [-103.4130, 43.9680],
    [-103.4040, 43.9715],
    [-103.3950, 43.9730],
    [-103.3880, 43.9705],
    [-103.3845, 43.9655],
    [-103.3860, 43.9590],
]

# Everything else is held.
CONTAINED_EDGE = [
    [-103.3860, 43.9590],
    [-103.3915, 43.9540],
    [-103.3980, 43.9495],
    [-103.4050, 43.9455],
    [-103.4120, 43.9425],
    [-103.4180, 43.9430],
    [-103.4230, 43.9490],
    [-103.4245, 43.9560],
    [-103.4210, 43.9625],
    [-103.4130, 43.9680],
]

COMPLETED_DOZER_LINE = [
    [-103.4270, 43.9575],
    [-103.4265, 43.9500],
    [-103.4205, 43.9440],
    [-103.4125, 43.9400],
    [-103.4040, 43.9430],
    [-103.3965, 43.9470],
]

COMPLETED_HAND_LINE = [
    [-103.4270, 43.9575],
    [-103.4230, 43.9645],
    [-103.4150, 43.9705],
]

COMPLETED_ROAD_AS_LINE = [
    [-103.3965, 43.9470],
    [-103.3900, 43.9515],
    [-103.3845, 43.9565],
]

PROPOSED_DOZER_LINE = [
    [-103.3845, 43.9565],
    [-103.3800, 43.9625],
    [-103.3785, 43.9690],
    [-103.3810, 43.9750],
]

PROPOSED_HAND_LINE = [
    [-103.3810, 43.9750],
    [-103.3880, 43.9790],
    [-103.3960, 43.9805],
    [-103.4050, 43.9790],
]

CONTINGENCY_ROAD_AS_LINE = [
    [-103.4050, 43.9790],
    [-103.4150, 43.9760],
    [-103.4230, 43.9700],
]

# Primary ingress from US-16 at Rockerville, west up Storm Mountain Rd.
ACCESS_ROUTE_MAIN = [
    [-103.3320, 43.9705],
    [-103.3420, 43.9690],
    [-103.3520, 43.9660],
    [-103.3610, 43.9640],
    [-103.3700, 43.9648],
    [-103.3770, 43.9655],
    [-103.3810, 43.9690],
]

ACCESS_ROUTE_SOUTH = [
    [-103.3320, 43.9705],
    [-103.3400, 43.9560],
    [-103.3520, 43.9470],
    [-103.3680, 43.9440],
    [-103.3830, 43.9450],
    [-103.3940, 43.9465],
]

ESCAPE_ROUTE_NORTH = [
    [-103.3810, 43.9690],
    [-103.3760, 43.9760],
    [-103.3700, 43.9820],
]

ESCAPE_ROUTE_SOUTH = [
    [-103.3965, 43.9470],
    [-103.3900, 43.9420],
    [-103.3820, 43.9385],
]

DIVISION_BREAK_A_Z = [
    [-103.4290, 43.9600],
    [-103.4180, 43.9575],
    [-103.4060, 43.9560],
    [-103.3940, 43.9552],
    [-103.3820, 43.9548],
]

DIVISION_BREAK_Z_M = [
    [-103.3980, 43.9370],
    [-103.3990, 43.9470],
    [-103.3985, 43.9552],
]

BRANCH_BREAK = [
    [-103.4300, 43.9720],
    [-103.4100, 43.9745],
    [-103.3900, 43.9770],
]

PUMP_AND_HOSE_LAY = [
    [-103.3608, 43.9702],
    [-103.3680, 43.9690],
    [-103.3750, 43.9672],
    [-103.3800, 43.9660],
]

FIRE_SPREAD_DIRECTION = [
    [-103.4100, 43.9560],
    [-103.3980, 43.9640],
    [-103.3900, 43.9700],
]


def circle_ring(lat: float, lon: float, radius_m: float, vertices: int = 72):
    """Circle of ``radius_m`` about a point, built in UTM and returned as lon/lat."""
    cx, cy = ll_to_utm(lat, lon)
    ring = []
    for i in range(vertices):
        theta = 2.0 * math.pi * i / vertices
        x = cx + radius_m * math.cos(theta)
        y = cy + radius_m * math.sin(theta)
        plat, plon = utm_to_ll(x, y)
        ring.append([round(plon, 6), round(plat, 6)])
    ring.append(ring[0])
    return ring


def buffer_line_ring(coords, radius_m: float, vertices_per_cap: int = 12):
    """Rounded buffer around a polyline, built in UTM. Good enough for a
    retardant-avoidance corridor or a powerline hazard envelope."""
    pts = [ll_to_utm(lat, lon) for lon, lat in coords]
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == len(pts) - 1:
            dx, dy = x - pts[-2][0], y - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        norm = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / norm, dx / norm
        left.append((x + nx * radius_m, y + ny * radius_m))
        right.append((x - nx * radius_m, y - ny * radius_m))

    def cap(center, start_angle, end_angle):
        out = []
        for i in range(vertices_per_cap + 1):
            t = start_angle + (end_angle - start_angle) * i / vertices_per_cap
            out.append((center[0] + radius_m * math.cos(t), center[1] + radius_m * math.sin(t)))
        return out

    end_dir = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
    start_dir = math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0])
    ring_utm = (
        left
        + cap(pts[-1], end_dir + math.pi / 2, end_dir - math.pi / 2)
        + list(reversed(right))
        + cap(pts[0], start_dir - math.pi / 2, start_dir - 3 * math.pi / 2)
    )
    ring = [[round(lon, 6), round(lat, 6)] for lat, lon in (utm_to_ll(x, y) for x, y in ring_utm)]
    ring.append(ring[0])
    return ring


SPRING_CREEK_CORRIDOR = [
    [-103.3560, 43.9760],
    [-103.3640, 43.9720],
    [-103.3720, 43.9690],
    [-103.3810, 43.9665],
    [-103.3900, 43.9650],
    [-103.3990, 43.9645],
]

POWERLINE = [
    [-103.4400, 43.9880],
    [-103.4200, 43.9840],
    [-103.4000, 43.9820],
    [-103.3800, 43.9830],
    [-103.3600, 43.9860],
]


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------

def base_props(category, label, geometry_id, map_method, comments=""):
    return {
        "FeatureCategory": category,
        "Label": label,
        "IsVisible": "Yes",
        "MapMethod": map_method,
        "GeometryID": geometry_id,
        "IncidentName": INCIDENT_NAME,
        "IRWINID": None,
        "CreateName": CREATE_NAME,
        "CreateDate": CREATE_DATE,
        "DeleteThis": "No",
        "Comments": comments,
    }


POINTS = [
    # category, label, lon, lat, map method, comment
    ("Incident Command Post", "ICP", -103.3405, 43.9748, "GPS-Driven",
     "Rockerville staging field. Exercise ICP."),
    ("Camp", "Camp 1", -103.3372, 43.9762, "GPS-Driven", "Spike camp, 120 person capacity."),
    ("Staging Area", "Staging 1", -103.3455, 43.9712, "GPS-Driven", "Engine staging off US-16."),
    ("Helibase", "Helibase", -103.3348, 43.9548, "GPS-Driven", "Exercise helibase."),
    ("Helispot", "H-1", -103.4062, 43.9762, "GPS-Flight", "Ridgetop. One ship at a time."),
    ("Helispot", "H-2", -103.3802, 43.9452, "GPS-Flight", "Old landing. Dusty, needs water."),
    ("Helispot", "H-3", -103.3688, 43.9622, "GPS-Flight", "Saddle. Short-haul capable."),
    ("Drop Point", "DP 1", -103.3462, 43.9698, "GPS-Driven", "US-16 turnout."),
    ("Drop Point", "DP 2", -103.3585, 43.9655, "GPS-Driven", "Storm Mountain Rd junction."),
    ("Drop Point", "DP 3", -103.3702, 43.9650, "GPS-Driven", "Turnaround, type 6 and smaller past here."),
    ("Drop Point", "DP 4", -103.3808, 43.9688, "GPS-Driven", "Div A anchor."),
    ("Drop Point", "DP 5", -103.3948, 43.9468, "GPS-Driven", "Div Z anchor, south road."),
    ("Drop Point", "DP 6", -103.4128, 43.9402, "GPS-Driven", "Dozer line tie-in, south flank."),
    ("Drop Point", "DP 7", -103.4268, 43.9578, "GPS-Walked", "West end of completed line. Foot access only."),
    ("Drop Point", "DP 8", -103.4055, 43.9788, "GPS-Driven", "Contingency line, north."),
    ("Dip Site", "Dip 1", -103.4302, 43.9842, "GPS-Flight", "Stock pond. Verify depth each morning."),
    ("Dip Site", "Dip 2", -103.3355, 43.9600, "GPS-Flight", "Adjacent to helibase."),
    ("Draft Site", "Draft 1", -103.3608, 43.9702, "GPS-Driven", "Spring Creek. Screened intake required."),
    ("Hydrant", "Hydrant 1", -103.3380, 43.9755, "GPS-Driven", "Camp supply."),
    ("Water Tank", "Tank 1", -103.3772, 43.9642, "GPS-Walked", "Training grounds 10,000 gal tank."),
    ("Safety Zone", "SZ-1", -103.3862, 43.9612, "GPS-Walked", "Meadow, 4 acres. Div A."),
    ("Safety Zone", "SZ-2", -103.4048, 43.9418, "GPS-Walked", "Old burn scar. Div Z."),
    ("Lookout", "LO-1", -103.3925, 43.9782, "GPS-Walked", "North rim. Sees the head."),
    ("Lookout", "LO-2", -103.4212, 43.9382, "GPS-Walked", "South, covers the dozer line."),
    ("Repeater", "RPT Storm", -103.3648, 43.9808, "GPS-Walked",
     "Sited to cover the Coon Hollow dead zone."),
    ("Mobile Weather Unit", "IRAWS 1", -103.3888, 43.9752, "GPS-Driven", "Exercise IRAWS."),
    ("Access Point", "AP-1", -103.3318, 43.9708, "GPS-Driven", "US-16 at Storm Mountain Rd."),
    ("Gate", "Gate 1", -103.3562, 43.9662, "GPS-Driven", "FS gate. Combination with Div A."),
    ("Gate", "Gate 2", -103.3925, 43.9452, "GPS-Driven", "Locked, south road."),
    ("Closure", "Closure 1", -103.3492, 43.9682, "GPS-Driven", "Storm Mountain Rd closed to public."),
    ("Closure", "Closure 2", -103.3680, 43.9432, "GPS-Driven", "South road closed."),
    ("Hazard", "Mine 1", -103.4108, 43.9598, "GPS-Walked",
     "Abandoned shaft, open. Uncovered, do not anchor line here."),
    ("Hazard", "Mine 2", -103.4162, 43.9532, "GPS-Walked", "Abandoned adit and tailings."),
    ("Hazard", "Powerline", -103.4002, 43.9820, "Digitized-Other", "Distribution line crossing."),
    ("Hazard", "Snags", -103.3968, 43.9678, "GPS-Walked", "Heavy beetle-kill, standing dead."),
    ("Medical Site", "MED 1", -103.3712, 43.9645, "GPS-Driven",
     "Line medic at DP 3. Ambulance interception point."),
    ("Medivac Site", "MEDIVAC 1", -103.3688, 43.9622, "GPS-Flight", "Co-located with H-3."),
    ("Value at Risk", "Training Grounds", -103.3768, 43.9648, "GPS-Walked",
     "Storm Mountain Training Grounds — lodge, cabins, dining hall."),
    ("Structure", "Lodge", -103.3766, 43.9651, "GPS-Walked", "Main lodge."),
    ("Structure", "Dining Hall", -103.3774, 43.9645, "GPS-Walked", ""),
    ("Structure", "Cabin Row", -103.3758, 43.9643, "GPS-Walked", "Six cabins."),
    ("Spot Fire", "Spot 1", -103.3822, 43.9742, "GPS-Walked", "Quarter acre, north of the head. Held."),
    ("Point of Origin", "Origin", -103.4118, 43.9518, "GPS-Walked", "Exercise origin. Secured."),
    ("Sign", "Sign 1", -103.3465, 43.9700, "GPS-Driven", "Fire traffic sign, US-16."),
    ("Internet Access", "Starlink 1", -103.3402, 43.9750, "GPS-Driven", "ICP."),
]


LINES = [
    ("Completed Dozer Line", "Div Z Dozer", COMPLETED_DOZER_LINE, "GPS-Driven",
     "Completed 0730 op 2. Two blades."),
    ("Completed Hand Line", "Div A Hand", COMPLETED_HAND_LINE, "GPS-Walked",
     "Completed op 2. Type 1 crew."),
    ("Completed Road as Line", "Div Z Road", COMPLETED_ROAD_AS_LINE, "GPS-Driven",
     "Existing road brushed and used as line."),
    ("Proposed Dozer Line", "Div A Proposed Dozer", PROPOSED_DOZER_LINE, "Digitized-Topo",
     "Op 3 objective. Tie DP 4 to the north contingency."),
    ("Proposed Hand Line", "North Contingency Hand", PROPOSED_HAND_LINE, "Digitized-Topo",
     "Contingency only. Do not construct without Ops approval."),
    ("Proposed Road as Line", "North Contingency Road", CONTINGENCY_ROAD_AS_LINE, "Digitized-Topo",
     "Contingency."),
    ("Uncontrolled Fire Edge", "Active Edge", UNCONTROLLED_EDGE, "Infrared Image",
     "Active at 0214 MDT 7/28."),
    ("Contained Fire Edge", "Held Edge", CONTAINED_EDGE, "Infrared Image", "Held at 0214 MDT 7/28."),
    ("Access Route", "Storm Mountain Rd", ACCESS_ROUTE_MAIN, "GPS-Driven",
     "1.7 mi of winding FS road. Single lane with turnouts. THE access constraint — "
     "brief every resource on it."),
    ("Access Route", "South Access", ACCESS_ROUTE_SOUTH, "GPS-Driven", "Longer, wider, slower."),
    ("Escape Route", "ER North", ESCAPE_ROUTE_NORTH, "GPS-Walked", "DP 4 to the north ridge."),
    ("Escape Route", "ER South", ESCAPE_ROUTE_SOUTH, "GPS-Walked", "DP 5 to SZ-2."),
    ("Division Break", "Div A / Div Z", DIVISION_BREAK_A_Z, "Digitized-Topo", ""),
    ("Division Break", "Div Z / Div M", DIVISION_BREAK_Z_M, "Digitized-Topo", ""),
    ("Branch Break", "Branch I / Branch II", BRANCH_BREAK, "Digitized-Topo", ""),
    ("Pump and Hose Lay", "Draft 1 Lay", PUMP_AND_HOSE_LAY, "GPS-Walked",
     "From Draft 1 to the structure group. Two portable pumps."),
    ("Fire Spread Direction", "Predicted Spread", FIRE_SPREAD_DIRECTION, "Digitized-Other",
     "Predicted op 3 spread, northeast."),
]


def build_points():
    features = []
    for i, (cat, label, lon, lat, method, comment) in enumerate(POINTS, start=1):
        props = base_props(cat, label, f"SMTG-PT-{i:04d}", method, comment)
        lat_r, lon_r = round(lat, 6), round(lon, 6)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": [lon_r, lat_r]},
        })
    return features


def build_lines():
    features = []
    for i, (cat, label, coords, method, comment) in enumerate(LINES, start=1):
        props = base_props(cat, label, f"SMTG-LN-{i:04d}", method, comment)
        props["LengthMiles"] = round(line_length_miles(coords), 3)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in coords]},
        })
    return features


def build_polygons():
    fire_center_lat, fire_center_lon = 43.9580, -103.4045
    specs = [
        ("Wildfire Daily Fire Perimeter", "Storm Mountain 07/28", PERIMETER_TODAY,
         "Infrared Image", "2026-07-28T02:14:00-06:00", "Operational period 3 perimeter."),
        ("Wildfire Daily Fire Perimeter", "Storm Mountain 07/27", PERIMETER_YESTERDAY,
         "Infrared Image", "2026-07-27T02:20:00-06:00", "Operational period 2 perimeter."),
        ("Wildfire Daily Fire Perimeter", "Storm Mountain 07/26", PERIMETER_DAY_ONE,
         "GPS-Flight", "2026-07-26T03:05:00-06:00", "Operational period 1 perimeter."),
        ("Temporary Flight Restriction", "TFR 5 NM",
         circle_ring(fire_center_lat, fire_center_lon, 5 * NM_TO_M),
         "Digitized-Other", None,
         "5 NM radius, surface to 8500 ft MSL. Exercise only — no real TFR exists. "
         "Extends past the AOI, which is why the air ops layout needs a wider extent than ops."),
        ("Aerial Hazard Area", "Powerline Corridor", buffer_line_ring(POWERLINE, 400.0),
         "Digitized-Other", None, "Distribution line. No low-level flight."),
        ("Retardant Avoidance Area", "Spring Creek", buffer_line_ring(SPRING_CREEK_CORRIDOR, 300.0),
         "Digitized-Other", None, "300 m each side of the creek. Exercise buffer."),
        ("Closure Area", "Storm Mountain Closure",
         circle_ring(43.9640, -103.3900, 4200.0), "Digitized-Other", None,
         "Public closure. Roads and trails inside are closed."),
        ("Safety Zone", "SZ-1 Area", circle_ring(43.9612, -103.3862, 130.0),
         "GPS-Walked", None, "Approximately 13 acres of meadow."),
        ("Structure Group", "Training Grounds Structures",
         circle_ring(43.9648, -103.3768, 350.0), "GPS-Walked", None,
         "Lodge, dining hall, cabin row, tank. Structure protection group assigned."),
        ("Management Action Point Area", "MAP 1 — Storm Mountain Rd",
         circle_ring(43.9655, -103.3700, 500.0), "Digitized-Topo", None,
         "Trigger: fire crosses the drainage west of DP 3 — evacuate the training grounds."),
    ]

    features = []
    for i, (cat, label, ring, method, dt, comment) in enumerate(specs, start=1):
        props = base_props(cat, label, f"SMTG-PY-{i:04d}", method, comment)
        props["GISAcres"] = round(ring_area_acres(ring), 1)
        props["PolygonDateTime"] = dt
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return features


def write(name, features):
    fc = {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "_warning": "TRAINING EXERCISE — NOT AN ACTUAL INCIDENT. Fabricated data. "
                    "Never publish, never sync to NIFS or NIFC AGOL.",
        "_generated_by": "scripts/make_mock_incident.py",
        "features": features,
    }
    path = OUT_DIR / f"{name.lower()}.geojson"
    path.write_text(json.dumps(fc, indent=1) + "\n")
    return path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    points, lines, polygons = build_points(), build_lines(), build_polygons()
    for name, feats in (("EventPoint", points), ("EventLine", lines), ("EventPolygon", polygons)):
        path = write(name, feats)
        print(f"wrote {path.relative_to(ROOT)}  ({len(feats)} features)")

    today = next(f for f in polygons if f["properties"]["Label"] == "Storm Mountain 07/28")
    acres = today["properties"]["GISAcres"]
    print()
    print(f"  daily perimeter 07/28 : {acres:,.1f} acres")
    for label in ("Storm Mountain 07/27", "Storm Mountain 07/26"):
        f = next(f for f in polygons if f["properties"]["Label"] == label)
        print(f"  daily perimeter {label[-5:]} : {f['properties']['GISAcres']:,.1f} acres")
    total_line = sum(f["properties"]["LengthMiles"] for f in lines
                     if f["properties"]["FeatureCategory"].startswith("Completed"))
    print(f"  completed line        : {total_line:.2f} mi")
    print()
    print("  Put this acreage in the source statement:")
    stmt = INCIDENT["perimeter_source"]["source_statement_template"].format(
        acres=f"{acres:,.0f}",
        collected_display=INCIDENT["perimeter_source"]["collected_display"],
        collection_method=INCIDENT["perimeter_source"]["collection_method"],
        datum_statement=AOI["crs"]["datum_statement"],
    )
    print(f"    {stmt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
