#!/usr/bin/env python3
"""Lint the exercise Event data against config/event_schema.json.

    python3 scripts/validate_event_data.py

Runs with no third-party dependencies so it can go in a pre-commit hook or a
CI job. Catches the failures that actually happen on an incident:

  * a FeatureCategory that is not in the domain — the feature draws as a grey
    dot and nobody notices until the briefing
  * a stale GISAcres or LengthMiles that no longer matches the geometry
  * an IRWINID on exercise data, which is the one thing §7 says must never happen
  * unclosed polygon rings, duplicate GeometryIDs, features outside the AOI

Exit code is non-zero if anything is an ERROR, so it can gate an export.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import line_length_miles, ring_area_acres  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "mock_incident"
SCHEMA = json.loads((ROOT / "config" / "event_schema.json").read_text())
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())

# Acreage/mileage tolerance. Tight enough to catch a hand-typed number, loose
# enough to absorb the rounding in the stored value.
AREA_TOLERANCE_PCT = 0.5
LENGTH_TOLERANCE_PCT = 0.5

FILES = {
    "EventPoint": "eventpoint.geojson",
    "EventLine": "eventline.geojson",
    "EventPolygon": "eventpolygon.geojson",
}


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def iter_coords(geom):
    t = geom["type"]
    if t == "Point":
        yield geom["coordinates"]
    elif t == "LineString":
        yield from geom["coordinates"]
    elif t == "Polygon":
        for ring in geom["coordinates"]:
            yield from ring
    else:
        raise ValueError(f"unsupported geometry {t}")


def check_extent(lon, lat) -> bool:
    """AOI plus a generous margin. The TFR legitimately spills out, so this is
    a sanity check for typo-scale mistakes, not a hard clip."""
    e = AOI["extent_geographic_4269"]
    margin = 0.15
    return (e["xmin"] - margin) <= lon <= (e["xmax"] + margin) and \
           (e["ymin"] - margin) <= lat <= (e["ymax"] + margin)


def validate_fc(fc_name: str, path: pathlib.Path, rep: Report) -> int:
    if not path.exists():
        rep.error(f"{fc_name}: missing file {path.relative_to(ROOT)} — run scripts/make_mock_incident.py")
        return 0

    doc = json.loads(path.read_text())
    spec = SCHEMA["feature_classes"][fc_name]
    domain = set(spec["categories"])
    required = [f["name"] for f in SCHEMA["common_fields"] if not f.get("nullable", True)]
    map_methods = set(SCHEMA["coded_domains"]["MapMethod"])

    seen_ids: dict[str, int] = {}
    features = doc.get("features", [])

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        where = f"{fc_name}[{idx}] {props.get('Label') or props.get('GeometryID') or '<unlabeled>'}"

        for field in required:
            if props.get(field) in (None, ""):
                rep.error(f"{where}: required field {field} is empty")

        cat = props.get("FeatureCategory")
        if cat and cat not in domain:
            rep.error(
                f"{where}: FeatureCategory '{cat}' is not in the {fc_name} domain — "
                f"this feature will not symbolize"
            )

        method = props.get("MapMethod")
        if method and method not in map_methods:
            rep.warn(f"{where}: MapMethod '{method}' is not in the MapMethod domain")

        if props.get("IRWINID"):
            rep.error(
                f"{where}: IRWINID is populated on exercise data. "
                f"Clear it — see docs/07-guardrails.md"
            )

        gid = props.get("GeometryID")
        if gid:
            if gid in seen_ids:
                rep.error(f"{where}: duplicate GeometryID '{gid}' (also at index {seen_ids[gid]})")
            seen_ids[gid] = idx

        expected_geom = {"EventPoint": "Point", "EventLine": "LineString", "EventPolygon": "Polygon"}[fc_name]
        if geom.get("type") != expected_geom:
            rep.error(f"{where}: geometry is {geom.get('type')}, expected {expected_geom}")
            continue

        for lon, lat in iter_coords(geom):
            if not check_extent(lon, lat):
                rep.warn(f"{where}: vertex {lon:.5f}, {lat:.5f} is well outside the AOI")
                break

        if fc_name == "EventPolygon":
            ring = geom["coordinates"][0]
            if ring[0] != ring[-1]:
                rep.error(f"{where}: polygon ring is not closed")
            if len(ring) < 4:
                rep.error(f"{where}: polygon ring has only {len(ring)} vertices")
            stored = props.get("GISAcres")
            if stored in (None, ""):
                rep.error(f"{where}: GISAcres is empty")
            else:
                actual = ring_area_acres(ring)
                if actual > 0 and abs(actual - stored) / actual * 100 > AREA_TOLERANCE_PCT:
                    rep.error(
                        f"{where}: GISAcres {stored:,.1f} does not match the geometry "
                        f"({actual:,.1f} acres). Recalculate before export."
                    )

        if fc_name == "EventLine":
            coords = geom["coordinates"]
            if len(coords) < 2:
                rep.error(f"{where}: line has {len(coords)} vertices")
                continue
            stored = props.get("LengthMiles")
            if stored in (None, ""):
                rep.error(f"{where}: LengthMiles is empty")
            else:
                actual = line_length_miles(coords)
                if actual > 0 and abs(actual - stored) / actual * 100 > LENGTH_TOLERANCE_PCT:
                    rep.error(
                        f"{where}: LengthMiles {stored:.3f} does not match the geometry "
                        f"({actual:.3f} mi). Recalculate before export."
                    )

    return len(features)


def check_scenario_completeness(rep: Report) -> None:
    """A perimeter with no active edge, or line with no division breaks, is a
    map that cannot brief. Warn, do not fail."""
    expectations = [
        ("EventPolygon", "Wildfire Daily Fire Perimeter", "no fire perimeter"),
        ("EventLine", "Uncontrolled Fire Edge", "no active fire edge — Ops cannot assign to it"),
        ("EventLine", "Division Break", "no division breaks — the IAP map cannot be divided"),
        ("EventPoint", "Drop Point", "no drop points"),
        ("EventPoint", "Safety Zone", "no safety zones — LCES is incomplete"),
        ("EventPoint", "Helispot", "no helispots — air ops has nowhere to land"),
    ]
    present: dict[str, set] = {}
    for fc, fname in FILES.items():
        p = DATA_DIR / fname
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        present[fc] = {f["properties"].get("FeatureCategory") for f in doc.get("features", [])}

    for fc, cat, msg in expectations:
        if fc in present and cat not in present[fc]:
            rep.warn(f"scenario: {msg}")


def main() -> int:
    rep = Report()
    total = 0
    print(f"validating {DATA_DIR.relative_to(ROOT)}/ against config/event_schema.json\n")
    for fc, fname in FILES.items():
        n = validate_fc(fc, DATA_DIR / fname, rep)
        total += n
        print(f"  {fc:<14} {n:>3} features")
    check_scenario_completeness(rep)

    print()
    for w in rep.warnings:
        print(f"  WARN  {w}")
    for e in rep.errors:
        print(f"  ERROR {e}")

    print()
    if rep.errors:
        print(f"FAILED — {len(rep.errors)} error(s), {len(rep.warnings)} warning(s), {total} features")
        return 1
    print(f"OK — {total} features, {len(rep.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
