"""Derive tactical Event features in place, inside the Event geodatabase.

    python scripts\\arcpy\\derive_tactical.py --gdb <...>\\event.gdb --fire Red ^
        --trails <...>\\base_data\\transportation\\trails ^
        --roads  <...>\\base_data\\transportation\\roads

REQUIRES arcpy. NOT executed in CI.

Same rules as scripts/derive_tactical.py — that one works on exported GeoJSON
anywhere, this one works on the live geodatabase so you can keep editing in Pro.
Both read config/derivation.yml, so they cannot drift apart.

What it does, per config/derivation.yml:
  * trail segments on the fire edge -> Completed / Proposed Hand Line
  * road segments on the fire edge  -> Completed / Proposed Road as Line
  * the perimeter                   -> Contained / Uncontrolled Fire Edge
  * drop point locations            -> numbered per the fire's block scheme

Re-runnable. Every feature it creates carries DerivedFrom, and the first thing
it does is delete the ones it made last time — so your hand-drawn line is never
touched, and re-running after an edit does not accumulate duplicates.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

try:
    import arcpy
except ImportError:  # pragma: no cover
    sys.exit("arcpy not found. Run this from the ArcGIS Pro Python environment.")

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml not found. Clone the arcgispro-py3 environment and install it there.")

ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "config" / "derivation.yml").read_text())
FIRES = yaml.safe_load((ROOT / "config" / "fires.yml").read_text())

HELD_CATEGORIES = (
    "Completed Hand Line", "Completed Dozer Line", "Completed Road as Line",
    "Completed Fuel Break", "Completed Mixed Construction Line",
)


def fire_config(color: str) -> dict:
    for f in FIRES["fires"]:
        if f["color"].lower() == color.lower():
            merged = dict(FIRES["defaults"])
            merged.update(f)
            return merged
    raise SystemExit(f"no fire named {color} in config/fires.yml")


def ensure_field(fc, name, ftype="TEXT", length=50):
    if name not in {f.name for f in arcpy.ListFields(fc)}:
        arcpy.management.AddField(fc, name, ftype, field_length=length)


def scratch(name):
    return arcpy.CreateUniqueName(name, arcpy.env.scratchGDB)


def latest_perimeter(event_polygon, incident_name):
    """The most recent daily perimeter for this fire."""
    cat = CFG["perimeter"]["source_category"]
    where = (f"FeatureCategory = '{cat}' AND IncidentName = '{incident_name}' "
             f"AND IsVisible = 'Yes' AND DeleteThis = 'No'")
    rows = []
    with arcpy.da.SearchCursor(event_polygon, ["SHAPE@", CFG["perimeter"]["latest_by"]], where) as cur:
        rows = [(shape, when) for shape, when in cur]
    if not rows:
        raise SystemExit(f"no '{cat}' found for {incident_name} — draw the perimeter first")
    rows.sort(key=lambda r: (r[1] is not None, r[1]))
    return rows[-1][0]


def clear_previous(event_line, incident_name):
    """Remove only what this tool made last time."""
    ensure_field(event_line, "DerivedFrom", "TEXT", 30)
    where = f"DerivedFrom IS NOT NULL AND IncidentName = '{incident_name}'"
    layer = arcpy.management.MakeFeatureLayer(event_line, "el_prev", where)[0]
    n = int(arcpy.management.GetCount(layer)[0])
    if n:
        arcpy.management.DeleteFeatures(layer)
    arcpy.management.Delete(layer)
    return n


def derive_linear(source_fc, perimeter, rules, fire, kind, event_line):
    """Clip a base-data linear layer to a buffer around the fire edge and write
    the surviving pieces into EventLine."""
    if not rules.get("enabled", True) or not source_fc:
        return 0

    edge = scratch("edge")
    arcpy.management.PolygonToLine(
        arcpy.management.CopyFeatures(perimeter, scratch("perim"))[0], edge
    )
    band = scratch("band")
    arcpy.analysis.Buffer(edge, band, f"{rules['buffer_m']} Meters", dissolve_option="ALL")

    override_field = rules.get("override_field")
    overrides = rules.get("override_values", {})

    near = scratch("near")
    arcpy.analysis.Clip(source_fc, band, near)

    insert_fields = ["SHAPE@", "FeatureCategory", "Label", "IsVisible", "MapMethod",
                     "GeometryID", "IncidentName", "CreateName", "CreateDate",
                     "DeleteThis", "Comments", "LengthMiles", "DerivedFrom"]
    available = {f.name for f in arcpy.ListFields(event_line)}
    insert_fields = [f for f in insert_fields if f == "SHAPE@" or f in available]

    src_names = {f.name for f in arcpy.ListFields(source_fc)}
    label_fields = [f for f in rules["label_from"] if f in src_names]
    read_fields = ["SHAPE@"] + label_fields + (
        [override_field] if override_field in src_names else []
    )

    prefix = fire["color"][:2].upper()
    min_len_m = rules["min_segment_length_m"]
    count = 0

    with arcpy.da.InsertCursor(event_line, insert_fields) as ins:
        with arcpy.da.SearchCursor(near, read_fields) as cur:
            for row in cur:
                shape = row[0]
                if shape is None or shape.length < min_len_m:
                    continue
                label = next((str(v) for v in row[1:1 + len(label_fields)] if v), "Unnamed")
                override = ""
                if override_field in src_names:
                    override = (row[-1] or "").strip().lower()

                if override in overrides:
                    category = overrides[override]
                    if category is None:
                        arcpy.AddMessage(f"  {kind} '{label}': held out by {override_field}={override}")
                        continue
                else:
                    category = rules["emit_as"]

                count += 1
                values = {
                    "SHAPE@": shape,
                    "FeatureCategory": category,
                    "Label": f"{rules['label_prefix']} {label}",
                    "IsVisible": "Yes",
                    "MapMethod": "Digitized-Other",
                    "GeometryID": f"{prefix}-{kind[:2].upper()}-{count:04d}",
                    "IncidentName": fire["incident_name"],
                    "CreateName": fire["giss"],
                    "CreateDate": fire["prepared"],
                    "DeleteThis": "No",
                    "Comments": f"Derived from {kind} '{label}'. Confirm with Ops before publishing.",
                    "LengthMiles": shape.getLength("GEODESIC", "MILES"),
                    "DerivedFrom": kind,
                }
                ins.insertRow([values[f] for f in insert_fields])

    arcpy.AddMessage(f"  {kind}: {count} segment(s) -> {rules['emit_as']}")
    return count


def derive_fire_edge(perimeter, fire, event_line):
    """Split the perimeter into contained and uncontrolled stretches."""
    rules = CFG["fire_edge"]
    if not rules.get("enabled", True):
        return 0

    edge = scratch("edge_full")
    arcpy.management.PolygonToLine(
        arcpy.management.CopyFeatures(perimeter, scratch("perim2"))[0], edge
    )

    held_where = (
        "FeatureCategory IN ("
        + ", ".join(f"'{c}'" for c in HELD_CATEGORIES)
        + f") AND IncidentName = '{fire['incident_name']}' AND IsVisible = 'Yes'"
    )
    held_layer = arcpy.management.MakeFeatureLayer(event_line, "held", held_where)[0]
    if int(arcpy.management.GetCount(held_layer)[0]) == 0:
        arcpy.AddWarning(
            "  no completed line for this fire — the entire perimeter will read as "
            "uncontrolled. That is the safe direction, but check it is what you meant."
        )

    held_band = scratch("held_band")
    arcpy.analysis.Buffer(held_layer, held_band, f"{rules['held_buffer_m']} Meters",
                          dissolve_option="ALL")

    contained = scratch("contained")
    uncontrolled = scratch("uncontrolled")
    arcpy.analysis.Clip(edge, held_band, contained)
    arcpy.analysis.Erase(edge, held_band, uncontrolled)

    insert_fields = ["SHAPE@", "FeatureCategory", "Label", "IsVisible", "MapMethod",
                     "GeometryID", "IncidentName", "CreateName", "CreateDate",
                     "DeleteThis", "Comments", "LengthMiles", "DerivedFrom"]
    available = {f.name for f in arcpy.ListFields(event_line)}
    insert_fields = [f for f in insert_fields if f == "SHAPE@" or f in available]

    prefix = fire["color"][:2].upper()
    seq, totals = 0, {}
    with arcpy.da.InsertCursor(event_line, insert_fields) as ins:
        for fc, category in ((contained, rules["contained_category"]),
                             (uncontrolled, rules["uncontrolled_category"])):
            miles = 0.0
            with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cur:
                for (shape,) in cur:
                    if shape is None or shape.length < rules["min_segment_length_m"]:
                        continue
                    seq += 1
                    length = shape.getLength("GEODESIC", "MILES")
                    miles += length
                    values = {
                        "SHAPE@": shape,
                        "FeatureCategory": category,
                        "Label": category.replace(" Fire Edge", ""),
                        "IsVisible": "Yes",
                        "MapMethod": fire["map_method"],
                        "GeometryID": f"{prefix}-ED-{seq:04d}",
                        "IncidentName": fire["incident_name"],
                        "CreateName": fire["giss"],
                        "CreateDate": fire["prepared"],
                        "DeleteThis": "No",
                        "Comments": "Derived from perimeter and held line. "
                                    "OPS MUST CONFIRM before this is published.",
                        "LengthMiles": length,
                        "DerivedFrom": "perimeter",
                    }
                    ins.insertRow([values[f] for f in insert_fields])
            totals[category] = miles

    arcpy.management.Delete(held_layer)
    for cat, miles in totals.items():
        arcpy.AddMessage(f"  {cat}: {miles:.2f} mi")
    return seq


def number_drop_points(event_point, event_line, fire):
    """Assign drop point numbers per the fire's block scheme, ordered along the
    access route rather than by draw order."""
    rules = CFG["drop_point_numbering"]
    if not rules.get("enabled", True):
        return 0

    ensure_field(event_point, rules["division_field"], "TEXT", 10)
    ensure_field(event_point, "DropPointNumber", "LONG")

    routes = []
    with arcpy.da.SearchCursor(
        event_line, ["SHAPE@"],
        f"FeatureCategory = '{rules['order_along']}' AND IncidentName = '{fire['incident_name']}'"
    ) as cur:
        routes = [s for (s,) in cur if s is not None]
    if not routes:
        arcpy.AddWarning(
            "  no Access Route for this fire — drop points will be numbered in draw "
            "order, which is not useful over a radio. Draw one."
        )

    where = (f"FeatureCategory = 'Drop Point' AND IncidentName = '{fire['incident_name']}' "
             f"AND DeleteThis = 'No'")
    fields = ["OID@", "SHAPE@", rules["division_field"], "Label", "DropPointNumber"]

    rows = []
    with arcpy.da.SearchCursor(event_point, fields, where) as cur:
        for oid, shape, div, label, _ in cur:
            along = 0.0
            if routes:
                along = min(r.measureOnLine(shape, False) for r in routes)
            rows.append({"oid": oid, "div": (div or rules["fallback_division"]).strip().upper(),
                         "along": along})
    if not rows:
        return 0

    blocks = fire.get("drop_point_blocks") or {}
    step = fire.get("drop_point_step", 1)
    assignment = {}
    by_div: dict[str, list] = {}
    for r in rows:
        by_div.setdefault(r["div"], []).append(r)
    for div, items in sorted(by_div.items()):
        items.sort(key=lambda r: r["along"])
        start = blocks.get(div, max(blocks.values(), default=0) + 100)
        for i, r in enumerate(items):
            assignment[r["oid"]] = (start + i * step, div)

    with arcpy.da.UpdateCursor(event_point, fields, where) as cur:
        for row in cur:
            oid = row[0]
            if oid in assignment:
                number, div = assignment[oid]
                row[2] = div
                row[3] = rules["label_format"].format(number=number)
                row[4] = number
                cur.updateRow(row)

    arcpy.AddMessage(f"  drop points: {len(assignment)} numbered "
                     + ", ".join(f"{d} from {blocks.get(d, '?')}" for d in sorted(by_div)))
    return len(assignment)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb", required=True)
    ap.add_argument("--fire", required=True)
    ap.add_argument("--trails", help="base-data trails feature class")
    ap.add_argument("--roads", help="base-data roads feature class")
    args = ap.parse_args()

    arcpy.env.overwriteOutput = True
    fire = fire_config(args.fire)
    event_point = os.path.join(args.gdb, "EventPoint")
    event_line = os.path.join(args.gdb, "EventLine")
    event_polygon = os.path.join(args.gdb, "EventPolygon")
    for fc in (event_point, event_line, event_polygon):
        if not arcpy.Exists(fc):
            raise SystemExit(f"{fc} does not exist. Run build_event_gdb.py first.")

    arcpy.AddMessage(f"{fire['incident_name']} ({fire['local_incident_id']})")

    removed = clear_previous(event_line, fire["incident_name"])
    if removed:
        arcpy.AddMessage(f"  cleared {removed} previously derived feature(s)")

    perimeter = latest_perimeter(event_polygon, fire["incident_name"])
    arcpy.AddMessage(f"  perimeter: {perimeter.getArea('GEODESIC', 'ACRES'):,.1f} acres")

    derive_linear(args.trails, perimeter, CFG["trails_to_hand_line"], fire, "trail", event_line)
    derive_linear(args.roads, perimeter, CFG["roads_to_line"], fire, "road", event_line)
    derive_fire_edge(perimeter, fire, event_line)
    number_drop_points(event_point, event_line, fire)

    if CFG["perimeter"].get("recalculate_acres"):
        arcpy.management.CalculateGeometryAttributes(
            event_polygon, [["GISAcres", "AREA_GEODESIC"]], area_unit="ACRES")
        arcpy.management.CalculateGeometryAttributes(
            event_line, [["LengthMiles", "LENGTH_GEODESIC"]], length_unit="MILES")
        arcpy.AddMessage("  recalculated GISAcres and LengthMiles")

    arcpy.AddWarning("\n" + " ".join(CFG["fire_edge"]["review_note"].split()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
