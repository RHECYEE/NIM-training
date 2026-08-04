#!/usr/bin/env python3
"""Pull the AOI's vector base data from public ArcGIS REST services.

    python3 scripts/fetch_base_data.py
    python3 scripts/fetch_base_data.py --only trails roads
    python3 scripts/fetch_base_data.py --out base_data --force

Standard library only — no arcpy, no requests. Runs before ArcGIS Pro is open.

Every endpoint in config/services.yml was probed against this AOI and returns
real Black Hills data. Rasters (DEM, NAIP, LANDFIRE) are not here: they are bulk
downloads with interactive selection and you fetch them by hand. This script
prints what is still missing when it finishes.

Results are cached — a layer already on disk is skipped unless you pass --force.
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())
SERVICES = yaml.safe_load((ROOT / "config" / "services.yml").read_text())

DEFAULTS = SERVICES["defaults"]
RETRIES = 3


def aoi_envelope() -> str:
    """AOI plus the download buffer, as a lon/lat envelope."""
    e = AOI["extent_geographic_4269"]
    buf_mi = AOI["download_buffer_miles"]
    dlat = buf_mi / 69.0
    dlon = buf_mi / 50.0  # ~69 * cos(44 deg); generous on purpose
    return f"{e['xmin'] - dlon},{e['ymin'] - dlat},{e['xmax'] + dlon},{e['ymax'] + dlat}"


def query_url(base: str, envelope: str, offset: int, page: int) -> str:
    params = {
        "geometry": envelope,
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": DEFAULTS["out_sr"],
        "f": DEFAULTS["format"],
        "resultOffset": offset,
        "resultRecordCount": page,
    }
    return f"{base.rstrip('/')}/query?" + urllib.parse.urlencode(params)


def fetch_json(url: str, timeout: int):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "storm-mountain-training-map"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def fetch_layer(spec: dict, envelope: str) -> dict:
    """Page through a service until it stops handing back more."""
    page = DEFAULTS["page_size"]
    timeout = DEFAULTS["timeout_seconds"]
    features, offset = [], 0

    while True:
        doc = fetch_json(query_url(spec["url"], envelope, offset, page), timeout)
        if isinstance(doc, dict) and doc.get("error"):
            raise RuntimeError(str(doc["error"].get("message", doc["error"])))
        batch = doc.get("features", [])
        features.extend(batch)
        # Services signal more data with exceededTransferLimit; some just return
        # a full page. Treat either as "keep going".
        if len(batch) < page and not doc.get("exceededTransferLimit"):
            break
        offset += len(batch)
        if not batch:
            break
        if offset > 200000:  # a runaway page loop would silently eat the disk
            raise RuntimeError("aborting: over 200k features, check the envelope")

    return {
        "type": "FeatureCollection",
        "name": spec["id"],
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "_source": spec["url"],
        "_source_name": spec["name"],
        "_fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "_aoi": AOI["name"],
        "_note": "Public reference data about a real place. NOT incident data.",
        "features": features,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="base_data", help="output folder (default: base_data)")
    ap.add_argument("--only", nargs="*", help="subset of layer ids")
    ap.add_argument("--force", action="store_true", help="refetch layers already on disk")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    envelope = aoi_envelope()
    layers = SERVICES["layers"]
    if args.only:
        wanted = {s.lower() for s in args.only}
        layers = [l for l in layers if l["id"].lower() in wanted]
        if not layers:
            print(f"no layer ids matching {args.only}", file=sys.stderr)
            return 1

    print(f"AOI envelope: {envelope}")
    print(f"output:       {out_dir}\n")
    print(f"{'layer':<18} {'features':>9}  status")
    print("-" * 58)

    failures, skipped = [], 0
    for spec in layers:
        path = out_dir / spec["out"]
        if path.exists() and not args.force:
            n = len(json.loads(path.read_text()).get("features", []))
            print(f"{spec['id']:<18} {n:>9,}  cached (--force to refetch)")
            skipped += 1
            continue

        try:
            doc = fetch_layer(spec, envelope)
        except Exception as exc:  # noqa: BLE001 - one bad service must not stop the rest
            status = "FAILED" if spec.get("required") else "failed (optional)"
            print(f"{spec['id']:<18} {'-':>9}  {status}: {exc}")
            if spec.get("required"):
                failures.append(spec["id"])
            continue

        path.write_text(json.dumps(doc))
        n = len(doc["features"])
        warn = "  <- empty, check the endpoint" if n == 0 and spec.get("required") else ""
        print(f"{spec['id']:<18} {n:>9,}  written{warn}")

    print("-" * 58)
    if skipped:
        print(f"{skipped} layer(s) already on disk\n")

    manual = SERVICES["manual_downloads"]
    print("Still needed, by hand (cannot be queried from a REST endpoint):")
    for item in manual["items"]:
        print(f"  - {item['name']}")
        print(f"      {item['url']}")

    if failures:
        print(f"\nFAILED required layer(s): {', '.join(failures)}")
        return 1
    print("\nBase data ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
