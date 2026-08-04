"""Build a blank Event geodatabase from config/event_schema.json.

    "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" ^
        scripts\\arcpy\\build_event_gdb.py --dest D:\\incidents\\2026_StormMountain\\incident_data

REQUIRES arcpy — run it from the ArcGIS Pro Python environment. It has NOT been
executed in this repo's CI; nothing here can be exercised without a Pro install.

PREFER THE OFFICIAL TEMPLATE. The blank Event GDB inside the GeoOps Incident
Directory Structure carries the current domains and is guaranteed to match the
.lyrx files. Use this script when you cannot get the template, when you want a
throwaway GDB for a classroom, or to see in one place what the schema is.

    https://www.nwcg.gov/page/geospatial-training-unit-tools
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

try:
    import arcpy
except ImportError:  # pragma: no cover - only meaningful inside Pro
    sys.exit(
        "arcpy not found. Run this with the ArcGIS Pro Python:\n"
        r'  "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"'
    )

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "config" / "event_schema.json").read_text())
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())

SR = arcpy.SpatialReference(AOI["crs"]["projected"]["epsg"])

TYPE_MAP = {"TEXT": "TEXT", "DOUBLE": "DOUBLE", "DATE": "DATE", "LONG": "LONG"}


def add_domains(gdb: str) -> None:
    existing = {d.name for d in arcpy.da.ListDomains(gdb)}

    for name, values in SCHEMA["coded_domains"].items():
        if name in existing:
            arcpy.AddMessage(f"domain {name} already present, skipping")
            continue
        arcpy.management.CreateDomain(gdb, name, name, "TEXT", "CODED")
        for v in values:
            arcpy.management.AddCodedValueToDomain(gdb, name, v, v)
        arcpy.AddMessage(f"domain {name}: {len(values)} values")

    for fc_name, spec in SCHEMA["feature_classes"].items():
        dom = spec["domain"]
        if dom in existing:
            continue
        arcpy.management.CreateDomain(gdb, dom, f"{fc_name} FeatureCategory", "TEXT", "CODED")
        for v in spec["categories"]:
            arcpy.management.AddCodedValueToDomain(gdb, dom, v, v)
        arcpy.AddMessage(f"domain {dom}: {len(spec['categories'])} values")


def add_fields(fc_path: str, fields: list[dict]) -> None:
    for f in fields:
        arcpy.management.AddField(
            fc_path,
            f["name"],
            TYPE_MAP[f["type"]],
            field_length=f.get("length"),
            field_alias=f["name"],
            field_is_nullable="NULLABLE" if f.get("nullable", True) else "NON_NULLABLE",
        )
        if f.get("domain") and f["domain"] in SCHEMA["coded_domains"]:
            arcpy.management.AssignDomainToField(fc_path, f["name"], f["domain"])
        if f.get("default") is not None:
            arcpy.management.AssignDefaultToField(fc_path, f["name"], f["default"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True, help="folder the geodatabase is created in")
    ap.add_argument("--name", default="event.gdb")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    gdb = os.path.join(args.dest, args.name)
    if arcpy.Exists(gdb):
        if not args.overwrite:
            arcpy.AddError(f"{gdb} exists. Pass --overwrite if you really mean it.")
            return 1
        arcpy.management.Delete(gdb)

    os.makedirs(args.dest, exist_ok=True)
    arcpy.management.CreateFileGDB(args.dest, args.name)
    arcpy.AddMessage(f"created {gdb}")

    add_domains(gdb)

    for fc_name, spec in SCHEMA["feature_classes"].items():
        arcpy.management.CreateFeatureclass(gdb, fc_name, spec["geometry"], spatial_reference=SR)
        fc_path = os.path.join(gdb, fc_name)

        add_fields(fc_path, SCHEMA["common_fields"])
        add_fields(fc_path, spec.get("extra_fields", []))
        arcpy.management.AssignDomainToField(fc_path, "FeatureCategory", spec["domain"])

        arcpy.AddMessage(f"{fc_name}: {spec['geometry']}, {len(spec['categories'])} categories")

    arcpy.AddMessage("\nNext:")
    arcpy.AddMessage("  1. Repair the Event .lyrx paths to point at this GDB so symbology comes through.")
    arcpy.AddMessage("  2. Draw the fires — see docs/10-digitizing-guide.md.")
    arcpy.AddMessage("  3. python scripts/arcpy/load_incident.py --gdb " + gdb + " --all")
    arcpy.AddMessage("\nTRAINING EXERCISE — NOT AN ACTUAL INCIDENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
