"""Load data/mock_incident/*.geojson into the Event geodatabase.

    python scripts\\arcpy\\load_mock_incident.py --gdb D:\\...\\incident_data\\event.gdb

REQUIRES arcpy and a Spatial-Analyst-free Pro install. NOT executed in CI.

Refuses to run against a geodatabase that looks like it is connected to the
National Incident Feature Service. Exercise data belongs in a local copy and
nowhere else — see docs/07-guardrails.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

try:
    import arcpy
except ImportError:  # pragma: no cover
    sys.exit("arcpy not found. Run this from the ArcGIS Pro Python environment.")

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "mock_incident"
SCHEMA = json.loads((ROOT / "config" / "event_schema.json").read_text())
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())
INCIDENT = json.loads((ROOT / "config" / "incident.json").read_text())

WGS84 = arcpy.SpatialReference(4326)
TARGET_SR = arcpy.SpatialReference(AOI["crs"]["projected"]["epsg"])

FILES = {
    "EventPoint": "eventpoint.geojson",
    "EventLine": "eventline.geojson",
    "EventPolygon": "eventpolygon.geojson",
}

FORBIDDEN_GDB_MARKERS = ("nifs", "agol", "arcgis.com", "national_incident", "featureserver")


def guard(gdb: str) -> None:
    lowered = gdb.lower()
    for marker in FORBIDDEN_GDB_MARKERS:
        if marker in lowered:
            raise SystemExit(
                f"Refusing to write exercise data to '{gdb}' — the path contains "
                f"'{marker}', which looks like a live incident service.\n"
                "Training data never goes to NIFS or NIFC AGOL. See docs/07-guardrails.md."
            )
    if gdb.lower().endswith(".sde"):
        raise SystemExit(
            "Refusing to write exercise data to an enterprise geodatabase connection. "
            "Use a local file geodatabase."
        )


def parse_date(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def geometry_for(fc_name, geom):
    coords = geom["coordinates"]
    if fc_name == "EventPoint":
        shape = arcpy.PointGeometry(arcpy.Point(*coords), WGS84)
    elif fc_name == "EventLine":
        shape = arcpy.Polyline(arcpy.Array([arcpy.Point(x, y) for x, y in coords]), WGS84)
    else:
        rings = arcpy.Array([arcpy.Array([arcpy.Point(x, y) for x, y in ring]) for ring in coords])
        shape = arcpy.Polygon(rings, WGS84)
    return shape.projectAs(TARGET_SR)


def load(gdb: str, fc_name: str, path: pathlib.Path, truncate: bool) -> int:
    fc_path = os.path.join(gdb, fc_name)
    if not arcpy.Exists(fc_path):
        raise SystemExit(f"{fc_path} does not exist. Run build_event_gdb.py first.")

    if truncate:
        arcpy.management.TruncateTable(fc_path)

    doc = json.loads(path.read_text())
    spec = SCHEMA["feature_classes"][fc_name]
    field_defs = SCHEMA["common_fields"] + spec.get("extra_fields", [])
    existing = {f.name for f in arcpy.ListFields(fc_path)}
    fields = [f["name"] for f in field_defs if f["name"] in existing]
    types = {f["name"]: f["type"] for f in field_defs}

    domain = set(spec["categories"])
    count = 0
    with arcpy.da.InsertCursor(fc_path, ["SHAPE@"] + fields) as cur:
        for feat in doc["features"]:
            props = feat["properties"]
            cat = props.get("FeatureCategory")
            if cat not in domain:
                arcpy.AddWarning(f"skipping {props.get('Label')}: '{cat}' not in the {fc_name} domain")
                continue
            row = [geometry_for(fc_name, feat["geometry"])]
            for name in fields:
                value = props.get(name)
                if types[name] == "DATE":
                    value = parse_date(value)
                row.append(value)
            cur.insertRow(row)
            count += 1

    arcpy.AddMessage(f"{fc_name}: loaded {count} features")
    return count


def recalculate(gdb: str) -> None:
    """Never trust the numbers that came in the file — recompute in the map's CRS."""
    poly = os.path.join(gdb, "EventPolygon")
    line = os.path.join(gdb, "EventLine")
    if arcpy.Exists(poly):
        arcpy.management.CalculateGeometryAttributes(
            poly, [["GISAcres", "AREA_GEODESIC"]], area_unit="ACRES", coordinate_system=TARGET_SR
        )
        arcpy.AddMessage("recalculated GISAcres")
    if arcpy.Exists(line):
        arcpy.management.CalculateGeometryAttributes(
            line, [["LengthMiles", "LENGTH_GEODESIC"]], length_unit="MILES", coordinate_system=TARGET_SR
        )
        arcpy.AddMessage("recalculated LengthMiles")


def report_acres(gdb: str) -> None:
    poly = os.path.join(gdb, "EventPolygon")
    where = "FeatureCategory = 'Wildfire Daily Fire Perimeter'"
    with arcpy.da.SearchCursor(poly, ["Label", "GISAcres", "PolygonDateTime"], where) as cur:
        rows = sorted(cur, key=lambda r: (r[2] or dt.datetime.min))
    arcpy.AddMessage("\nDaily perimeters:")
    for label, acres, when in rows:
        arcpy.AddMessage(f"  {label:<28} {acres:>10,.1f} acres   {when}")
    if rows:
        arcpy.AddMessage(
            f"\nSource statement acreage: {rows[-1][1]:,.0f} acres "
            f"({INCIDENT['perimeter_source']['collected_display']})"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb", required=True)
    ap.add_argument("--append", action="store_true", help="keep existing rows instead of truncating")
    args = ap.parse_args()

    guard(args.gdb)
    arcpy.env.overwriteOutput = True

    total = 0
    for fc_name, fname in FILES.items():
        total += load(args.gdb, fc_name, DATA / fname, truncate=not args.append)

    recalculate(args.gdb)
    report_acres(args.gdb)

    arcpy.AddMessage(f"\n{total} features loaded")
    arcpy.AddMessage(INCIDENT["watermark"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
