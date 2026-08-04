"""Apply per-product definition queries and export geospatial PDFs.

    python scripts\\arcpy\\export_products.py --aprx D:\\...\\projects\\StormMountain.aprx ^
        --out D:\\...\\products\\pdf
    python scripts\\arcpy\\export_products.py --aprx ... --out ... --products iap pio

REQUIRES arcpy. NOT executed in CI.

Each product in config/map_products.yml maps to a layout of the same name. The
definition queries are applied here, from config, every time — not saved into
the .aprx and trusted. That matters most for the `pio` product, whose queries
are the mechanism that keeps tactical data off a public sheet; a query someone
turned off last week in the project file would not survive this script.

Filenames follow config/map_products.yml -> naming.pattern, which was decoded
from the Burnt Creek exports.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

try:
    import arcpy
except ImportError:  # pragma: no cover
    sys.exit("arcpy not found. Run this from the ArcGIS Pro Python environment.")

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml not found. `conda install pyyaml` in a cloned arcgispro-py3 environment.")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PRODUCTS = yaml.safe_load((ROOT / "config" / "map_products.yml").read_text())
INCIDENT = json.loads((ROOT / "config" / "incident.json").read_text())

EVENT_LAYERS = ("EventPoint", "EventLine", "EventPolygon")


def camel(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[\s_-]+", name.strip()))


def output_name(product_key: str, product: dict) -> str:
    op = INCIDENT["operational_period"]
    prepared = INCIDENT["map_prepared"]["prepared_iso"]
    date_part, time_part = prepared.split("T")
    return PRODUCTS["naming"]["pattern"].format(
        product=product_key,
        page_size=product["page_size"],
        orientation=product["orientation"],
        prepared_yyyymmdd=date_part.replace("-", ""),
        prepared_hhmm=time_part[:5].replace(":", ""),
        IncidentName=camel(INCIDENT["incident_name"]),
        UnitID=INCIDENT["unit_id_full"].replace("-", ""),
        op_mmdd=op["date"][5:].replace("-", ""),
        shift=op["shift"],
    )


def combine(global_q: str, product_q: str) -> str:
    product_q = " ".join(product_q.split())
    if product_q in ("1=0",):
        return product_q
    if product_q in ("1=1", ""):
        return global_q
    return f"({global_q}) AND ({product_q})"


def apply_queries(layout, product: dict, report: list) -> None:
    queries = product.get("definition_query", {})
    global_q = PRODUCTS["global_definition_query"]

    for map_frame in layout.listElements("MAPFRAME_ELEMENT"):
        m = map_frame.map
        if m is None:
            continue
        for layer in m.listLayers():
            if layer.name not in EVENT_LAYERS or not layer.supports("DEFINITIONQUERY"):
                continue
            product_q = queries.get(layer.name)
            if product_q is None:
                report.append(f"    {layer.name}: no query in config — LEFT AS-IS, check this")
                continue
            final = combine(global_q[layer.name], product_q)
            layer.definitionQuery = final
            report.append(f"    {layer.name}: {final}")


def verify_pio(layout, report: list) -> bool:
    """Belt and braces on the one product where a mistake is a safety issue."""
    ok = True
    for map_frame in layout.listElements("MAPFRAME_ELEMENT"):
        m = map_frame.map
        if m is None:
            continue
        for layer in m.listLayers():
            if layer.name in ("EventPoint", "EventLine"):
                if layer.definitionQuery.strip() != "1=0":
                    report.append(f"    REFUSING: {layer.name} query is not 1=0 on the public product")
                    ok = False
    return ok


def export(layout, path: str, dpi: int) -> None:
    layout.exportToPDF(
        path,
        resolution=dpi,
        image_quality="BEST",
        compress_vector_graphics=True,
        embed_fonts=True,
        layers_attributes="LAYERS_AND_ATTRIBUTES",
        georef_info=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aprx", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--products", nargs="*", default=None,
                    help="subset of product keys; default is all of them")
    ap.add_argument("--dry-run", action="store_true", help="apply queries and report, do not export")
    args = ap.parse_args()

    aprx = arcpy.mp.ArcGISProject(args.aprx)
    layouts = {lyt.name.lower(): lyt for lyt in aprx.listLayouts()}
    wanted = args.products or list(PRODUCTS["products"].keys())
    os.makedirs(args.out, exist_ok=True)
    dpi = PRODUCTS["export"]["dpi"]

    exported, skipped = 0, []
    for key in wanted:
        product = PRODUCTS["products"].get(key)
        if product is None:
            arcpy.AddWarning(f"{key}: not in config/map_products.yml, skipping")
            continue
        layout = layouts.get(key.lower())
        if layout is None:
            arcpy.AddWarning(f"{key}: no layout named '{key}' in the project, skipping")
            skipped.append(key)
            continue

        report: list[str] = []
        arcpy.AddMessage(f"\n{key} — {product['title']}")
        apply_queries(layout, product, report)

        if product.get("safety_critical") and not verify_pio(layout, report):
            for line in report:
                arcpy.AddMessage(line)
            arcpy.AddError(f"{key}: refusing to export a public product with tactical layers visible")
            return 1

        for line in report:
            arcpy.AddMessage(line)

        name = output_name(key, product)
        path = os.path.join(args.out, name)
        if args.dry_run:
            arcpy.AddMessage(f"    would export -> {name}")
        else:
            export(layout, path, dpi)
            arcpy.AddMessage(f"    exported -> {name}")
            exported += 1

    aprx.save()

    arcpy.AddMessage(f"\n{exported} product(s) exported to {args.out}")
    if skipped:
        arcpy.AddWarning(f"missing layouts: {', '.join(skipped)}")
    arcpy.AddMessage(
        "\nBefore these leave the ICP:\n"
        "  - every sheet carries the watermark: " + INCIDENT["watermark"] + "\n"
        "  - open one in Avenza and confirm the georeferencing took\n"
        "  - photocopy the IAP sheet in black and white and confirm it still reads\n"
        "  - a second person confirms the public sheet has no tactical data on it"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
