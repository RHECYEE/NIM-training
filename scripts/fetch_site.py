#!/usr/bin/env python3
"""Fetch the leased property's parcels from the Pennington County parcel service.

    python3 scripts/fetch_site.py
    python3 scripts/fetch_site.py --force

Writes data/site/leased_parcels.geojson and data/site/leased_extent.geojson.

The leased property is 12 contiguous patented mining claims — Mineral Survey
2049 — not a single parcel. The claim boundaries are real surveyed lines and
they matter operationally: they are what "the property" means on the ground, and
several of them carry mine workings.

The fetched attributes also answer a question the exercise cannot invent:
initial-attack jurisdiction and EMS response for this address.

Standard library only. Committed output means the pipeline works offline.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from geoutil import dd_to_dms, ll_to_utm, ring_area_acres  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text())
OUT_DIR = ROOT / "data" / "site"

SERVICE = SITE["parcel_service"]["url"]
WHERE = SITE["parcel_service"]["where"]


def fetch(url: str, timeout: int = 90):
    req = urllib.request.Request(url, headers={"User-Agent": "storm-mountain-training-map"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            # Some proxies prepend a status line to the body.
            return json.loads(raw[raw.find("{"):])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def convex_hull(points):
    """Andrew's monotone chain. Used for a map EXTENT, never for a boundary."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def outer_ring(geom):
    ring = geom["coordinates"][0]
    if ring and isinstance(ring[0][0], list):
        ring = ring[0]
    return ring


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parcels_path = OUT_DIR / "leased_parcels.geojson"
    extent_path = OUT_DIR / "leased_extent.geojson"

    if parcels_path.exists() and not args.force:
        n = len(json.loads(parcels_path.read_text())["features"])
        print(f"cached: {parcels_path.relative_to(ROOT)} ({n} parcels). --force to refetch.")
        return 0

    params = {
        "where": WHERE,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "geojson",
    }
    url = f"{SERVICE.rstrip('/')}/query?" + urllib.parse.urlencode(params)
    print(f"querying {SERVICE}\n  where {WHERE}\n")

    doc = fetch(url)
    features = doc.get("features", [])
    if not features:
        print("no parcels returned — the county may have changed the schema or the "
              "ownership record. Check config/site.yml -> parcel_service.where",
              file=sys.stderr)
        return 1

    all_pts, stated, measured = [], 0.0, 0.0
    print(f"{'claim':<26} {'PIN':<12} {'stated':>8} {'geometry':>9}")
    print("-" * 60)
    for f in sorted(features, key=lambda f: str(f["properties"].get("Subdivisio"))):
        p = f["properties"]
        ring = outer_ring(f["geometry"])
        acres = ring_area_acres(ring)
        stated += p.get("Acres") or 0.0
        measured += acres
        all_pts.extend((round(x, 6), round(y, 6)) for x, y in ring)
        print(f"  {str(p.get('Subdivisio')):<24} {p.get('PIN'):<12} "
              f"{p.get('Acres') or 0:>8.2f} {acres:>9.2f}")
    print("-" * 60)
    print(f"  {'TOTAL':<24} {len(features):<12} {stated:>8.2f} {measured:>9.2f} acres")

    doc["_source"] = SERVICE
    doc["_where"] = WHERE
    doc["_fetched"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    doc["_note"] = (
        "Leased property parcels, from the county assessor. Public record about a "
        "real place — NOT incident data, and not to be published on a PIO product."
    )
    doc["_acres_stated"] = round(stated, 2)
    doc["_acres_from_geometry"] = round(measured, 2)
    parcels_path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"\nwrote {parcels_path.relative_to(ROOT)}")

    hull = convex_hull(all_pts)
    hull.append(hull[0])
    lons = [x for x, _ in hull]
    lats = [y for _, y in hull]
    clat, clon = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
    easting, northing = ll_to_utm(clat, clon)

    extent = {
        "type": "FeatureCollection",
        "name": "leased_extent",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "_warning": (
            "CONVEX HULL of the leased parcels, for setting a map extent ONLY. "
            "This is NOT the legal property boundary — it cuts corners the actual "
            "claim block does not. Use leased_parcels.geojson for anything that "
            "matters."
        ),
        "features": [{
            "type": "Feature",
            "properties": {
                "Name": SITE["property"]["name"],
                "Parcels": len(features),
                "AcresStated": round(stated, 2),
                "Purpose": "map extent only, not a boundary",
            },
            "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in hull]]},
        }],
    }
    extent_path.write_text(json.dumps(extent, indent=1) + "\n")
    print(f"wrote {extent_path.relative_to(ROOT)}")

    print(f"\n  centre  {dd_to_dms(clat, True)}  {dd_to_dms(clon, False)}")
    print(f"  UTM 13N {easting:,.1f} E  {northing:,.1f} N")
    print(f"  bbox    {min(lons):.6f},{min(lats):.6f} -> {max(lons):.6f},{max(lats):.6f}")

    # Report jurisdiction ACROSS the parcels, not off the first one. This block
    # is split between two fire districts, and reading a single parcel would
    # hide that — which is the kind of mistake that puts the wrong district on
    # the map and the wrong IC in the first hour.
    from collections import Counter
    print("\n  Jurisdiction on record, by parcel:")
    for label, key in (("Fire", "Fire"), ("Ambulance", "Ambulance"),
                       ("Water", "Water"), ("School", "School")):
        counts = Counter((f["properties"].get(key) or "").strip() or "(blank)"
                         for f in features)
        rendered = ", ".join(f"{v} ({n})" for v, n in counts.most_common())
        flag = "   <- SPLIT" if len(counts) > 1 else ""
        print(f"    {label:<10} {rendered}{flag}")
    if len({(f["properties"].get("Fire") or "").strip() for f in features}) > 1:
        print("\n  The fire district boundary runs THROUGH the leased property.")
        print("  Which side a fire starts on decides who is IC for the first hour.")
    print("\n  Stated acreage is the legal figure; the geometry figure is the polygon.")
    print("  They differ by a few percent, as parcel data always does. Use the stated")
    print("  figure when the number has legal weight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
