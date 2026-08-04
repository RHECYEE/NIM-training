"""The template fire scenario, and the machinery to place it at a given fire.

Not run directly — ``scripts/make_fires.py`` drives this for each of the seven
fires in ``config/fires.yml``.

Everything here is invented. The geometry sits inside the real AOI so the
exercise rests on real terrain, real roads and real ownership, but no perimeter,
line or point below describes anything that ever happened.

Acreages and line mileages are computed from the geometry, never asserted, so
the number on the map and the number in the attribute table cannot drift apart.

The template
------------
Ignition on the west side of the AOI, wind-driven run to the northeast over
three burning periods, head pointed at the Storm Mountain Training Grounds.
That makes the camp a value at risk and makes the single winding access road the
constraint the exercise is actually about.

Each fire is this template rotated to its own run bearing, scaled to its own
size and translated to its own centre — so the internal relationships that make
a scenario briefable (line anchored to road, safety zones off the flanks, drop
points on the access route) survive, while every fire looks genuinely different
on the sheet.
"""

from __future__ import annotations

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import (  # noqa: E402
    Similarity,
    centroid,
    ll_to_utm,
    line_length_miles,
    ring_area_acres,
    utm_to_ll,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
NM_TO_M = 1852.0

# The template is drawn with its head running to the northeast.
TEMPLATE_BEARING = 45.0


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


# Evacuation zones, named the way a county sheriff names them. In South Dakota
# the sheriff owns the evacuation decision, not the IMT, so these are the
# county's zones and the labels have to match what the county broadcasts.
EVACUATION_ZONES = [
    ("Zone A — GO", [-103.3860, 43.9660], 1500.0,
     "Immediate evacuation. Structures inside the Management Action Point trigger."),
    ("Zone B — SET", [-103.3560, 43.9700], 2200.0,
     "Be ready. Sheriff will upgrade if the fire crosses the drainage."),
    ("Zone C — READY", [-103.3300, 43.9740], 2600.0, "Stay informed."),
]

# Ground suppression disturbed and what has to be put back. Built from the
# completed line, because that is what the dozer actually cut.
REPAIR_CORRIDORS = [
    ("Div Z Dozer Repair", "COMPLETED_DOZER_LINE", 60.0,
     "Waterbar, pull berm back, scatter slash. Two blades wide."),
    ("Div Z Road Repair", "COMPLETED_ROAD_AS_LINE", 40.0,
     "Blade back to template, reinstall drainage."),
]

# --------------------------------------------------------------------------
# stand-ins for the real base-data trail and road layers
# --------------------------------------------------------------------------
#
# NOT map data. These exist only so scripts/derive_tactical.py has something to
# run against before the real USFS TrailNFS_Publish and RoadCore layers are
# downloaded and the real perimeters are drawn. Some of them deliberately run
# along the perimeter so the "trail on the fire edge becomes hand line" rule has
# a positive case to find, and some deliberately do not so it has a negative one.

TEMPLATE_TRAILS = [
    # name, number, coords, LINE_STATUS override ("" = let proximity decide)
    ("Storm Mountain Loop", "9082", [
        [-103.4270, 43.9575], [-103.4230, 43.9645], [-103.4150, 43.9705],
        [-103.4060, 43.9740], [-103.3960, 43.9752],
    ], ""),
    ("Coon Hollow", "9083", [
        [-103.3845, 43.9655], [-103.3800, 43.9625], [-103.3785, 43.9690],
        [-103.3810, 43.9750],
    ], ""),
    ("Rockerville Flume", "9084", [
        [-103.3560, 43.9760], [-103.3640, 43.9720], [-103.3720, 43.9690],
        [-103.3810, 43.9665],
    ], ""),
    ("Spring Creek Spur", "9085", [
        [-103.3400, 43.9600], [-103.3350, 43.9560], [-103.3300, 43.9520],
    ], ""),
    ("Old Mine Trail", "9086", [
        [-103.4160, 43.9530], [-103.4110, 43.9560], [-103.4060, 43.9590],
    ], "none"),  # runs through the burn, but it is not line — nobody is on it
]

TEMPLATE_ROADS = [
    # name, coords, LINE_STATUS override
    ("Storm Mountain Rd", ACCESS_ROUTE_MAIN, ""),
    ("South Fork Rd", [
        [-103.3965, 43.9470], [-103.3900, 43.9515], [-103.3845, 43.9565],
    ], ""),
    ("FS 231", [
        [-103.4265, 43.9500], [-103.4205, 43.9440], [-103.4125, 43.9400],
    ], ""),
    ("US-16", [
        [-103.3200, 43.9800], [-103.3320, 43.9705], [-103.3420, 43.9560],
    ], ""),
]


def build_reference_layers(tf):
    """Trail and road stand-ins, transformed to this fire."""
    trails, roads = [], []
    for name, number, coords, status in TEMPLATE_TRAILS:
        trails.append({
            "type": "Feature",
            "properties": {"TRAIL_NAME": name, "TRAIL_NO": number, "LINE_STATUS": status},
            "geometry": {"type": "LineString", "coordinates": tf(coords)},
        })
    for name, coords, status in TEMPLATE_ROADS:
        roads.append({
            "type": "Feature",
            "properties": {"NAME": name, "LINE_STATUS": status},
            "geometry": {"type": "LineString", "coordinates": tf(coords)},
        })
    return trails, roads


TEMPLATE_CENTER = None  # computed on first use, from the operational-period perimeter


def template_center():
    """Centroid of the current perimeter — the anchor every transform pivots on."""
    global TEMPLATE_CENTER
    if TEMPLATE_CENTER is None:
        cx, cy = centroid(PERIMETER_TODAY)
        TEMPLATE_CENTER = utm_to_ll(cx, cy)
    return TEMPLATE_CENTER


def transform_for(fire: dict) -> Similarity:
    return Similarity(
        template_center(),
        (fire["center"]["lat"], fire["center"]["lon"]),
        fire["run_bearing"] - TEMPLATE_BEARING,
        fire["scale"],
    )


# --------------------------------------------------------------------------
# feature construction
# --------------------------------------------------------------------------

def base_props(fire, category, label, geometry_id, map_method, comments=""):
    return {
        "FeatureCategory": category,
        "Label": label,
        "IsVisible": "Yes",
        "MapMethod": map_method,
        "GeometryID": geometry_id,
        "IncidentName": fire["incident_name"],
        "IRWINID": None,
        "CreateName": fire["giss"],
        "CreateDate": fire["prepared"],
        "DeleteThis": "No",
        "Comments": comments,
    }


def build_points(fire, tf):
    prefix = fire["color"][:2].upper()
    features = []
    # Which division a drop point belongs to. On the real exercise this comes
    # from the division you drew it in; here it is fixed so the block-numbering
    # scheme has something to group on.
    dp_division = {"DP 1": "A", "DP 2": "A", "DP 3": "A", "DP 4": "A",
                   "DP 5": "Z", "DP 6": "Z", "DP 7": "M", "DP 8": "M"}
    for i, (cat, label, lon, lat, method, comment) in enumerate(POINTS, start=1):
        props = base_props(fire, cat, label, f"{prefix}-PT-{i:04d}", method, comment)
        if cat == "Drop Point":
            props["DIVISION"] = dp_division.get(label, "A")
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": tf.point(lon, lat)},
        })
    return features


def build_lines(fire, tf):
    prefix = fire["color"][:2].upper()
    features = []
    for i, (cat, label, coords, method, comment) in enumerate(LINES, start=1):
        moved = tf(coords)
        props = base_props(fire, cat, label, f"{prefix}-LN-{i:04d}", method, comment)
        props["LengthMiles"] = round(line_length_miles(moved), 3)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "LineString", "coordinates": moved},
        })
    return features


LINE_BY_NAME = {
    "COMPLETED_DOZER_LINE": COMPLETED_DOZER_LINE,
    "COMPLETED_ROAD_AS_LINE": COMPLETED_ROAD_AS_LINE,
}


def build_polygons(fire, tf):
    """Rings that describe the fire get transformed. Rings that describe a fixed
    real-world distance — the 5 NM TFR, a 300 m retardant buffer — are rebuilt at
    the moved location so the radius stays physically true rather than scaled."""
    prefix = fire["color"][:2].upper()
    op = fire["op_period"]
    method = fire["map_method"]
    fire_ll = (fire["center"]["lat"], fire["center"]["lon"])

    specs = []

    # Three daily perimeters, oldest first, ending on the operational period.
    for offset, ring in ((2, PERIMETER_DAY_ONE), (1, PERIMETER_YESTERDAY), (0, PERIMETER_TODAY)):
        day = day_offset(op["date"], -offset)
        label = f"{fire['incident_name']} {day[5:7]}/{day[8:10]}"
        specs.append((
            "Wildfire Daily Fire Perimeter", label, tf(ring),
            method if offset == 0 else "Infrared Image",
            f"{day}T02:14:00-06:00",
            f"Operational period {op['number'] - offset} perimeter."
            if op["number"] - offset > 0 else "Earlier perimeter.",
        ))

    specs.append((
        "Temporary Flight Restriction", "TFR 5 NM",
        circle_ring(*fire_ll, 5 * NM_TO_M), "Digitized-Other", None,
        "5 NM radius, surface to 8500 ft MSL. Exercise only — no real TFR exists. "
        "Wider than the AOI, which is why air ops needs a wider extent than ops.",
    ))
    specs.append((
        "Aerial Hazard Area", "Powerline Corridor",
        buffer_line_ring(tf(POWERLINE), 400.0), "Digitized-Other", None,
        "Distribution line. No low-level flight.",
    ))
    specs.append((
        "Retardant Avoidance Area", "Spring Creek",
        buffer_line_ring(tf(SPRING_CREEK_CORRIDOR), 300.0), "Digitized-Other", None,
        "300 m each side of the creek. Exercise buffer.",
    ))
    specs.append((
        "Closure Area", f"{fire['incident_name']} Closure",
        circle_ring(*fire_ll, 4200.0 * fire["scale"]), "Digitized-Other", None,
        "Public closure. Roads and trails inside are closed.",
    ))

    sz = tf.point(-103.3862, 43.9612)
    specs.append((
        "Safety Zone", "SZ-1 Area", circle_ring(sz[1], sz[0], 130.0),
        "GPS-Walked", None, "Meadow. Measured, not eyeballed.",
    ))
    sg = tf.point(-103.3768, 43.9648)
    specs.append((
        "Structure Group", "Training Grounds Structures", circle_ring(sg[1], sg[0], 350.0),
        "GPS-Walked", None,
        "Lodge, dining hall, cabin row, tank. Structure protection group assigned.",
    ))
    mp = tf.point(-103.3700, 43.9655)
    specs.append((
        "Management Action Point Area", "MAP 1 — Access Road", circle_ring(mp[1], mp[0], 500.0),
        "Digitized-Topo", None,
        "Trigger: fire crosses the drainage west of DP 3 — evacuate the training grounds.",
    ))

    for label, center, radius, comment in EVACUATION_ZONES:
        moved = tf.point(*center)
        specs.append((
            "Evacuation Area", label, circle_ring(moved[1], moved[0], radius),
            "Digitized-Other", None, comment,
        ))

    for label, line_key, radius, comment in REPAIR_CORRIDORS:
        specs.append((
            "Repair Area", label, buffer_line_ring(tf(LINE_BY_NAME[line_key]), radius),
            "GPS-Walked", None, comment,
        ))

    features = []
    for i, (cat, label, ring, mm, dt, comment) in enumerate(specs, start=1):
        props = base_props(fire, cat, label, f"{prefix}-PY-{i:04d}", mm, comment)
        props["GISAcres"] = round(ring_area_acres(ring), 1)
        props["PolygonDateTime"] = dt
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return features


def day_offset(date_str: str, days: int) -> str:
    import datetime as _dt
    d = _dt.date.fromisoformat(date_str) + _dt.timedelta(days=days)
    return d.isoformat()


def build(fire: dict) -> dict:
    """All three feature classes for one fire, plus the trail/road stand-ins."""
    tf = transform_for(fire)
    trails, roads = build_reference_layers(tf)
    return {
        "EventPoint": build_points(fire, tf),
        "EventLine": build_lines(fire, tf),
        "EventPolygon": build_polygons(fire, tf),
        "trails": trails,
        "roads": roads,
    }
