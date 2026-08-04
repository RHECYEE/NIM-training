#!/usr/bin/env python3
"""Build the lat/long coordinate table that goes on the air ops and pilot sheets.

    python3 scripts/make_coordinate_table.py            # markdown to stdout
    python3 scripts/make_coordinate_table.py --csv      # CSV, for a Pro table frame

Generated from the geometry, never typed. A coordinate table that disagrees
with the symbol on the map is worse than no table at all — the pilot flies the
table.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import dd_to_dm, dd_to_dms, ll_to_utm  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "data" / "fixtures"
PRODUCTS = ROOT / "config" / "map_products.yml"

DEFAULT_CATEGORIES = ["Helibase", "Helispot", "Dip Site", "Draft Site", "Medivac Site"]
ORDER = {c: i for i, c in enumerate(DEFAULT_CATEGORIES)}


def load_rows(categories, points_path):
    doc = json.loads(points_path.read_text())
    rows = []
    for feat in doc["features"]:
        p = feat["properties"]
        if p["FeatureCategory"] not in categories:
            continue
        if p.get("IsVisible") != "Yes" or p.get("DeleteThis") == "Yes":
            continue
        lon, lat = feat["geometry"]["coordinates"]
        easting, northing = ll_to_utm(lat, lon)
        rows.append({
            "Type": p["FeatureCategory"],
            "Label": p["Label"],
            "Latitude (DMS)": dd_to_dms(lat, True),
            "Longitude (DMS)": dd_to_dms(lon, False),
            "Latitude (DM)": dd_to_dm(lat, True),
            "Longitude (DM)": dd_to_dm(lon, False),
            "UTM 13N E": f"{easting:.0f}",
            "UTM 13N N": f"{northing:.0f}",
            "Notes": p.get("Comments", ""),
        })
    rows.sort(key=lambda r: (ORDER.get(r["Type"], 99), r["Label"]))
    return rows


COLUMNS_SHEET = ["Type", "Label", "Latitude (DMS)", "Longitude (DMS)", "Notes"]
COLUMNS_FULL = ["Type", "Label", "Latitude (DMS)", "Longitude (DMS)",
                "Latitude (DM)", "Longitude (DM)", "UTM 13N E", "UTM 13N N", "Notes"]


def to_markdown(rows, columns):
    out = io.StringIO()
    out.write("| " + " | ".join(columns) + " |\n")
    out.write("|" + "|".join("---" for _ in columns) + "|\n")
    for r in rows:
        out.write("| " + " | ".join(str(r[c]) for c in columns) + " |\n")
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true", help="emit CSV instead of markdown")
    ap.add_argument("--full", action="store_true", help="include DM and UTM columns")
    ap.add_argument("--out", type=pathlib.Path, help="write to a file instead of stdout")
    ap.add_argument("--fire", required=True, help="which colour")
    ap.add_argument("--root", default=None, help="default: data/fixtures")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root else DEFAULT_ROOT
    if not root.is_absolute():
        root = ROOT / root
    points_path = root / args.fire.lower() / "eventpoint.geojson"
    if not points_path.exists():
        print(f"no point data at {points_path}", file=sys.stderr)
        return 1

    rows = load_rows(DEFAULT_CATEGORIES, points_path)
    columns = COLUMNS_FULL if args.full else COLUMNS_SHEET

    if args.csv:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        text = buf.getvalue()
    else:
        text = to_markdown(rows, columns)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"wrote {args.out} ({len(rows)} rows)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
