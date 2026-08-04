#!/usr/bin/env python3
"""Create a GeoOps-style incident directory tree for the exercise.

    python3 scripts/make_folder_structure.py --dest ~/incidents

This is a FALLBACK. If you have the official GeoOps Incident Directory
Structure from the NWCG Geospatial Training Unit, extract that instead — it
ships the blank Event geodatabase, the current .lyrx symbology and the .aprx
layout templates, none of which this script can conjure. Use this when you need
the tree on a machine that has not downloaded the template yet, or to see the
shape of it before you commit.

    https://www.nwcg.gov/page/geospatial-training-unit-tools
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
INCIDENT = json.loads((ROOT / "config" / "incident.json").read_text())

TREE = [
    "base_data/elevation",
    "base_data/imagery",
    "base_data/transportation",
    "base_data/hydrography",
    "base_data/ownership",
    "base_data/fuels",
    "base_data/structures",
    "base_data/reference",
    "documents",
    "incident_data/backup",
    "incident_data/exports",
    "incident_data/field_collection",
    "incident_data/gps",
    "incident_data/infrared",
    "products/pdf",
    "products/jpg",
    "products/archive",
    "projects",
    "tools/layer_files",
    "tools/scripts",
    "tools/templates",
]

READMES = {
    "base_data": (
        "Reference data about the place. Nothing incident-specific.\n"
        "Everything here is clipped to the AOI + 2 mi buffer and projected to "
        "EPSG:26913 on ingest.\n"
        "See config/sources.yml for what goes where and where it came from.\n"
    ),
    "incident_data": (
        "The Event geodatabase and everything that feeds it.\n"
        "backup/  — dated copies of the Event GDB. Back up before every edit session.\n"
        "exports/ — shapefile/GeoJSON handoffs to other units.\n"
        "field_collection/ — Field Maps downloads, raw.\n"
        "gps/ — raw GPS tracks and waypoints as received, unedited.\n"
        "infrared/ — IR interpretation products.\n"
    ),
    "products": (
        "Finished map products.\n"
        "pdf/ — geospatial PDFs, named per config/map_products.yml -> naming.pattern.\n"
        "archive/ — every operational period's products, kept. Do not overwrite yesterday.\n"
    ),
    "projects": "ArcGIS Pro projects (.aprx). One edit project, one product project.\n",
    "tools": "Layer files (.lyrx), scripts, layout templates.\n",
    "documents": "IAP packets, 209s, delegation, briefing notes.\n",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=pathlib.Path, required=True,
                    help="parent directory the incident folder is created in")
    ap.add_argument("--name", default=None,
                    help="incident folder name (default: <year>_<IncidentName>)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    year = INCIDENT["operational_period"]["date"][:4]
    folder = args.name or f"{year}_{INCIDENT['incident_name'].replace(' ', '')}"
    base = args.dest.expanduser() / folder

    if base.exists() and not args.dry_run:
        print(f"refusing to write: {base} already exists", file=sys.stderr)
        return 1

    print(f"{'would create' if args.dry_run else 'creating'} {base}")
    for rel in TREE:
        path = base / rel
        print(f"  {rel}/")
        if not args.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        for top, text in READMES.items():
            (base / top / "README.txt").write_text(text)
        (base / "README.txt").write_text(
            f"{INCIDENT['watermark']}\n\n"
            f"Incident      : {INCIDENT['incident_name']}\n"
            f"Local ID      : {INCIDENT['local_incident_id']}\n"
            f"Unit          : {INCIDENT['unit_id_full']}\n"
            f"Admin unit    : {INCIDENT['administrative_unit']}\n"
            f"IRWIN ID      : none, and none is ever to be assigned\n\n"
            "This is a training exercise. Do not sync any of it to the National "
            "Incident Feature Service or to NIFC AGOL, and do not publish any "
            "perimeter from it to a public-facing service.\n"
        )
        print(f"\nwrote README.txt at the root and in {len(READMES)} subfolders")

    print("\nNext: extract the official GeoOps template over this tree if you have it,")
    print("      then drop base data in per config/sources.yml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
