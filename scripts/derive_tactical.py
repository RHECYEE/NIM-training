#!/usr/bin/env python3
"""Turn drawn geometry into tactical Event features.

    python3 scripts/derive_tactical.py --fire Red
    python3 scripts/derive_tactical.py --all
    python3 scripts/derive_tactical.py --all --in data/fixtures --dry-run

You draw the perimeter, the helispots and the drop point locations in ArcGIS
Pro, and mark which trail and road segments are being held. This derives the
rest, per config/derivation.yml:

  * trail segments on the fire edge   -> Completed / Proposed Hand Line
  * road segments on the fire edge    -> Completed / Proposed Road as Line
  * the perimeter itself              -> Contained / Uncontrolled Fire Edge
  * drop point locations              -> numbered per the fire's block scheme

Runs on GeoJSON with no third-party geometry library, so it works on the
exported data anywhere. `scripts/arcpy/derive_tactical.py` does the same thing
in place inside the Event geodatabase.

The derived fire edge is a STARTING POINT, not an answer. Ops confirms it every
operational period — a stretch wrongly shown as contained is how people get hurt.

TRAINING EXERCISE — NOT AN ACTUAL INCIDENT.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import (  # noqa: E402
    densify_utm,
    distance_along_polyline,
    line_length_m,
    line_length_miles,
    ll_to_utm,
    point_to_polyline_distance,
    project_ring,
    runs_of_true,
    utm_to_ll,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "derivation.yml").read_text())
FIRES = yaml.safe_load((ROOT / "config" / "fires.yml").read_text())

SAMPLE_SPACING_M = 25.0


def load_geojson(path: pathlib.Path):
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("features", [])


def to_utm(coords):
    return project_ring(coords, 13)


def utm_to_lonlat(pts):
    out = []
    for x, y in pts:
        lat, lon = utm_to_ll(x, y)
        out.append([round(lon, 6), round(lat, 6)])
    return out


def first_attr(props, names):
    for n in names:
        v = props.get(n)
        if v not in (None, ""):
            return str(v)
    return None


# --------------------------------------------------------------------------
# perimeter
# --------------------------------------------------------------------------

def pick_perimeter(polygons):
    """The most recent daily perimeter — that is what 'the fire' means today."""
    cat = CFG["perimeter"]["source_category"]
    candidates = [f for f in polygons if f["properties"].get("FeatureCategory") == cat]
    if not candidates:
        return None
    key = CFG["perimeter"]["latest_by"]
    candidates.sort(key=lambda f: f["properties"].get(key) or "")
    return candidates[-1]


# --------------------------------------------------------------------------
# linear features on the fire edge
# --------------------------------------------------------------------------

def derive_line_features(features, perimeter_utm, rules, fire, kind):
    """Emit Event Lines for the stretches of a base-data linear layer that run
    along the fire edge."""
    if not rules.get("enabled", True):
        return [], []

    buffer_m = rules["buffer_m"]
    min_len = rules["min_segment_length_m"]
    override_field = rules.get("override_field")
    overrides = rules.get("override_values", {})
    out, notes = [], []
    seq = 0

    for feat in features:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        props = feat.get("properties", {})

        override = (props.get(override_field) or "").strip().lower() if override_field else ""
        if override in overrides:
            category = overrides[override]
            if category is None:
                notes.append(f"  {kind}: '{first_attr(props, rules['label_from']) or '?'}' "
                             f"forced to stay base data by {override_field}={override}")
                continue
            forced = True
        else:
            category, forced = rules["emit_as"], False

        pts = densify_utm(to_utm(geom["coordinates"]), SAMPLE_SPACING_M)
        if forced:
            runs = [(0, len(pts))]
        else:
            near = [point_to_polyline_distance(x, y, perimeter_utm) <= buffer_m for x, y in pts]
            runs = runs_of_true(near, min_run=2)

        base_label = first_attr(props, rules["label_from"]) or "Unnamed"
        for start, end in runs:
            chunk = pts[start:end]
            if len(chunk) < 2:
                continue
            length_m = line_length_m(utm_to_lonlat(chunk))
            if length_m < min_len and not forced:
                continue
            seq += 1
            coords = utm_to_lonlat(chunk)
            out.append({
                "type": "Feature",
                "properties": {
                    "FeatureCategory": category,
                    "Label": f"{rules['label_prefix']} {base_label}",
                    "IsVisible": "Yes",
                    "MapMethod": "Digitized-Other",
                    "GeometryID": f"{fire['color'][:2].upper()}-{kind[:2].upper()}-{seq:04d}",
                    "IncidentName": fire["incident_name"],
                    "IRWINID": None,
                    "CreateName": fire.get("giss", "TRAINEE, GISS"),
                    "CreateDate": fire["prepared"],
                    "DeleteThis": "No",
                    "Comments": (
                        f"Derived from {kind} '{base_label}'"
                        + (f" — forced by {override_field}={override}." if forced
                           else f" running within {buffer_m} m of the fire edge.")
                        + " Confirm with Ops before publishing."
                    ),
                    "LengthMiles": round(line_length_miles(coords), 3),
                    "DerivedFrom": kind,
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })

    return out, notes


# --------------------------------------------------------------------------
# fire edge
# --------------------------------------------------------------------------

def derive_fire_edge(perimeter_ring, held_lines_utm, fire):
    """Split the perimeter into contained and uncontrolled stretches."""
    rules = CFG["fire_edge"]
    if not rules.get("enabled", True):
        return []

    held_buffer = rules["held_buffer_m"]
    min_len = rules["min_segment_length_m"]
    pts = densify_utm(to_utm(perimeter_ring), SAMPLE_SPACING_M)

    def is_held(x, y):
        return any(point_to_polyline_distance(x, y, line) <= held_buffer for line in held_lines_utm)

    held = [is_held(x, y) for x, y in pts]

    out, seq = [], 0
    for category, flags in (
        (rules["contained_category"], held),
        (rules["uncontrolled_category"], [not h for h in held]),
    ):
        for start, end in runs_of_true(flags, min_run=2):
            chunk = pts[start:end]
            coords = utm_to_lonlat(chunk)
            if line_length_m(coords) < min_len:
                continue
            seq += 1
            out.append({
                "type": "Feature",
                "properties": {
                    "FeatureCategory": category,
                    "Label": category.replace(" Fire Edge", ""),
                    "IsVisible": "Yes",
                    "MapMethod": fire["map_method"],
                    "GeometryID": f"{fire['color'][:2].upper()}-ED-{seq:04d}",
                    "IncidentName": fire["incident_name"],
                    "IRWINID": None,
                    "CreateName": fire.get("giss", "TRAINEE, GISS"),
                    "CreateDate": fire["prepared"],
                    "DeleteThis": "No",
                    "Comments": "Derived from perimeter and held line. "
                                "OPS MUST CONFIRM before this is published.",
                    "LengthMiles": round(line_length_miles(coords), 3),
                    "DerivedFrom": "perimeter",
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return out


# --------------------------------------------------------------------------
# drop point numbering
# --------------------------------------------------------------------------

def number_drop_points(points, lines, fire):
    """Assign drop point numbers per the fire's block scheme, ordered the way a
    driver encounters them coming in on the access route."""
    rules = CFG["drop_point_numbering"]
    if not rules.get("enabled", True):
        return 0

    blocks = fire.get("drop_point_blocks") or {}
    step = fire.get("drop_point_step", 1)
    div_field = rules["division_field"]
    fallback = rules["fallback_division"]

    routes = [to_utm(f["geometry"]["coordinates"]) for f in lines
              if f["properties"].get("FeatureCategory") == rules["order_along"]
              and f["geometry"]["type"] == "LineString"]

    dps = [f for f in points if f["properties"].get("FeatureCategory") == "Drop Point"]
    if not dps:
        return 0

    by_division: dict[str, list] = {}
    for f in dps:
        div = (f["properties"].get(div_field) or fallback).strip().upper()
        by_division.setdefault(div, []).append(f)

    numbered = 0
    for div, feats in sorted(by_division.items()):
        def sort_key(f):
            lon, lat = f["geometry"]["coordinates"]
            x, y = ll_to_utm(lat, lon)
            if not routes:
                return (0.0, lat)
            along, dist = min(
                (distance_along_polyline(x, y, r) for r in routes), key=lambda t: t[1]
            )
            return (along, 0.0)

        feats.sort(key=sort_key)
        start = blocks.get(div)
        if start is None:
            start = max(blocks.values(), default=0) + 100
        for i, f in enumerate(feats):
            number = start + i * step
            f["properties"]["Label"] = rules["label_format"].format(number=number)
            f["properties"]["DropPointNumber"] = number
            f["properties"][div_field] = div
            numbered += 1

    return numbered


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def resolve_fire(entry):
    merged = dict(FIRES["defaults"])
    merged.update(entry)
    return merged


def process(fire, in_dir: pathlib.Path, out_dir: pathlib.Path, dry_run: bool):
    points = load_geojson(in_dir / "eventpoint.geojson")
    lines = load_geojson(in_dir / "eventline.geojson")
    polygons = load_geojson(in_dir / "eventpolygon.geojson")
    trails = load_geojson(in_dir / "trails.geojson")
    roads = load_geojson(in_dir / "roads.geojson")

    perimeter = pick_perimeter(polygons)
    if perimeter is None:
        return {"error": "no Wildfire Daily Fire Perimeter found — nothing to derive from"}

    ring = perimeter["geometry"]["coordinates"][0]
    perimeter_utm = densify_utm(to_utm(ring), SAMPLE_SPACING_M)

    notes = []
    hand, n1 = derive_line_features(trails, perimeter_utm, CFG["trails_to_hand_line"], fire, "trail")
    road, n2 = derive_line_features(roads, perimeter_utm, CFG["roads_to_line"], fire, "road")
    notes += n1 + n2

    # Everything being held, drawn or derived, decides what counts as contained.
    held_categories = {
        "Completed Hand Line", "Completed Dozer Line", "Completed Road as Line",
        "Completed Fuel Break", "Completed Mixed Construction Line",
    }
    held_utm = [to_utm(f["geometry"]["coordinates"]) for f in lines
                if f["properties"].get("FeatureCategory") in held_categories
                and f["geometry"]["type"] == "LineString"]
    held_utm += [to_utm(f["geometry"]["coordinates"]) for f in hand + road
                 if f["properties"]["FeatureCategory"] in held_categories]

    edges = derive_fire_edge(ring, held_utm, fire)

    # Replace any previously derived features; keep everything hand-drawn.
    kept = [f for f in lines if not f["properties"].get("DerivedFrom")]
    combined = kept + hand + road + edges

    numbered = number_drop_points(points, combined, fire)

    result = {
        "hand_line": len(hand),
        "road_as_line": len(road),
        "fire_edge": len(edges),
        "contained_mi": round(sum(f["properties"]["LengthMiles"] for f in edges
                                  if f["properties"]["FeatureCategory"] == "Contained Fire Edge"), 2),
        "uncontrolled_mi": round(sum(f["properties"]["LengthMiles"] for f in edges
                                     if f["properties"]["FeatureCategory"] == "Uncontrolled Fire Edge"), 2),
        "drop_points_numbered": numbered,
        "notes": notes,
    }

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, feats in (("eventline", combined), ("eventpoint", points)):
            path = out_dir / f"{name}.geojson"
            doc = json.loads(path.read_text()) if path.exists() else {
                "type": "FeatureCollection",
                "name": name.replace("event", "Event").title().replace("event", ""),
                "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            }
            doc["_warning"] = ("TRAINING EXERCISE — NOT AN ACTUAL INCIDENT. Fabricated data. "
                               "Never publish, never sync to NIFS or NIFC AGOL.")
            doc["_derived_by"] = "scripts/derive_tactical.py"
            doc["features"] = feats
            path.write_text(json.dumps(doc, indent=1) + "\n")

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", help="single colour")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--in", dest="in_root", default="data/drawn",
                    help="root holding <colour>/ folders exported from Pro")
    ap.add_argument("--out", dest="out_root", default=None, help="default: same as --in")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    in_root = ROOT / args.in_root
    out_root = ROOT / (args.out_root or args.in_root)

    fires = [resolve_fire(f) for f in FIRES["fires"]]
    if args.fire:
        fires = [f for f in fires if f["color"].lower() == args.fire.lower()]
    elif not args.all:
        print("pass --fire <colour> or --all", file=sys.stderr)
        return 2
    if not fires:
        print("no matching fire", file=sys.stderr)
        return 1

    print(f"deriving from {in_root.relative_to(ROOT)}/"
          + ("  (dry run)" if args.dry_run else ""))
    print(f"\n{'fire':<9} {'H/L':>4} {'road':>5} {'edge':>5} {'held mi':>8} {'open mi':>8} {'DPs':>5}")
    print("-" * 52)

    failures = 0
    for fire in fires:
        d = in_root / fire["color"].lower()
        if not d.exists():
            print(f"{fire['color']:<9} no folder at {d.relative_to(ROOT)} — nothing drawn yet")
            failures += 1
            continue
        r = process(fire, d, out_root / fire["color"].lower(), args.dry_run)
        if "error" in r:
            print(f"{fire['color']:<9} {r['error']}")
            failures += 1
            continue
        print(f"{fire['color']:<9} {r['hand_line']:>4} {r['road_as_line']:>5} {r['fire_edge']:>5} "
              f"{r['contained_mi']:>8.2f} {r['uncontrolled_mi']:>8.2f} {r['drop_points_numbered']:>5}")
        for n in r["notes"]:
            print(n)

    print("-" * 52)
    if CFG["fire_edge"].get("review_required"):
        print("\n" + " ".join(CFG["fire_edge"]["review_note"].split()))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
