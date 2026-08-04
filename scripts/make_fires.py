#!/usr/bin/env python3
"""Generate the seven exercise fires from config/fires.yml.

    python3 scripts/make_fires.py
    python3 scripts/make_fires.py --fire Red      # just one

Writes data/fires/<color>/{eventpoint,eventline,eventpolygon}.geojson plus a
fire.json carrying the resolved metadata every layout's dynamic text binds to.

Each fire is the template scenario in scripts/scenario.py, rotated to its run
bearing, scaled to its size and translated to its centre.

TRAINING EXERCISE — NOT AN ACTUAL INCIDENT.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scenario  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "fixtures"
FIRES_CFG = yaml.safe_load((ROOT / "config" / "fires.yml").read_text())
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())
PRODUCTS = yaml.safe_load((ROOT / "config" / "map_products.yml").read_text())

WATERMARK = PRODUCTS["export"]["watermark"]


def resolve(fire: dict) -> dict:
    """Fire entry merged over the shared defaults."""
    merged = dict(FIRES_CFG["defaults"])
    merged.update(fire)
    return merged


def source_statement(fire: dict, acres: float) -> str:
    when = fire["collected"]
    display = f"{when[5:7]}/{when[8:10]}/{when[:4]} at {when[11:13]}{when[14:16]} {fire['timezone_abbr']}"
    return (
        f"{acres:,.0f} acres at {display}. {fire['collection_method']}. "
        f"{AOI['crs']['datum_statement']}"
    )


def write_collection(path: pathlib.Path, name: str, fire: dict, features: list) -> None:
    doc = {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "_warning": f"{WATERMARK}. Fabricated data. Never publish, never sync to NIFS or NIFC AGOL.",
        "_fire": fire["incident_name"],
        "_generated_by": "scripts/make_fires.py",
        "features": features,
    }
    path.write_text(json.dumps(doc, indent=1) + "\n")


def build_fire(fire: dict) -> dict:
    out_dir = OUT_ROOT / fire["color"].lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    collections = scenario.build(fire)
    reference = {k: collections.pop(k) for k in ("trails", "roads")}
    for fc_name, features in collections.items():
        write_collection(out_dir / f"{fc_name.lower()}.geojson", fc_name, fire, features)
    for name, features in reference.items():
        write_collection(out_dir / f"{name}.geojson", name, fire, features)

    perims = [f for f in collections["EventPolygon"]
              if f["properties"]["FeatureCategory"] == "Wildfire Daily Fire Perimeter"]
    perims.sort(key=lambda f: f["properties"]["PolygonDateTime"] or "")
    acres = perims[-1]["properties"]["GISAcres"]
    completed = sum(f["properties"]["LengthMiles"] for f in collections["EventLine"]
                    if f["properties"]["FeatureCategory"].startswith("Completed"))

    op = fire["op_period"]
    prepared = fire["prepared"]
    meta = {
        "_warning": WATERMARK,
        "color": fire["color"],
        "incident_name": fire["incident_name"],
        "incident_name_upper": fire["incident_name"].upper(),
        "local_incident_id": fire["local_incident_id"],
        "unit_id": fire["unit_id"],
        "unit_id_full": fire["unit_id_full"],
        "irwin_id": None,
        "administrative_unit": fire["administrative_unit"],
        "district": fire["district"],
        "county": fire["county"],
        "state": fire["state"],
        "protecting_agency": fire["protecting_agency"],
        "imt": fire["imt"],
        "giss": fire["giss"],
        "gisto": fire["gisto"],
        "center": fire["center"],
        "run_bearing": fire["run_bearing"],
        "scale": fire["scale"],
        "teaching_focus": " ".join(fire["teaching_focus"].split()),
        "operational_period": {
            "number": op["number"],
            "date": op["date"],
            "date_display": f"{op['date'][5:7]}/{op['date'][8:10]}/{op['date'][:4]}",
            "shift": op["shift"],
            "timezone": fire["timezone"],
            "timezone_abbr": fire["timezone_abbr"],
        },
        "prepared": {
            "iso": prepared,
            "display": f"{int(prepared[5:7])}/{int(prepared[8:10])}/{prepared[:4]} "
                       f"{prepared[11:13]}{prepared[14:16]}",
        },
        "perimeter_source": {
            "acres": acres,
            "collected": fire["collected"],
            "collection_method": fire["collection_method"],
            "map_method": fire["map_method"],
            "statement": source_statement(fire, acres),
        },
        "progression": [
            {"label": f["properties"]["Label"],
             "date": (f["properties"]["PolygonDateTime"] or "")[:10],
             "acres": f["properties"]["GISAcres"]}
            for f in perims
        ],
        "completed_line_miles": round(completed, 2),
        "feature_counts": {k: len(v) for k, v in collections.items()},
        "products": list(PRODUCTS["products"].keys()),
        "watermark": WATERMARK,
    }
    (out_dir / "fire.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fire", help="build only this colour")
    args = ap.parse_args()

    fires = [resolve(f) for f in FIRES_CFG["fires"]]
    if args.fire:
        fires = [f for f in fires if f["color"].lower() == args.fire.lower()]
        if not fires:
            print(f"no fire named {args.fire}", file=sys.stderr)
            return 1

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    n_products = len(PRODUCTS["products"])

    print(f"{'fire':<9} {'incident ID':<17} {'op':<12} {'acres':>9} {'line mi':>8}  features")
    print("-" * 74)
    total_features = 0
    for fire in fires:
        meta = build_fire(fire)
        counts = meta["feature_counts"]
        total_features += sum(counts.values())
        op = meta["operational_period"]
        print(
            f"{meta['color']:<9} {meta['local_incident_id']:<17} "
            f"{op['date'][5:]}{'/' + op['shift'][:1]:<3} "
            f"{meta['perimeter_source']['acres']:>9,.0f} "
            f"{meta['completed_line_miles']:>8.2f}  "
            f"{counts['EventPoint']}pt {counts['EventLine']}ln {counts['EventPolygon']}py"
        )

    print("-" * 74)
    print(f"{len(fires)} fire(s), {total_features} features, "
          f"{len(fires)} x {n_products} = {len(fires) * n_products} products to build")
    print(f"\n{WATERMARK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
