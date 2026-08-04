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
FIXTURE_ROOT = ROOT / "data" / "fixtures"

EVENT_LAYERS = ("EventPoint", "EventLine", "EventPolygon")


def camel(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[\s_-]+", name.strip()))


def load_fire(root: pathlib.Path, color: str) -> dict:
    path = root / color.lower() / "fire.json"
    if not path.exists():
        raise SystemExit(f"{path} not found — run scripts/make_fires.py, or point --root "
                         f"at the folder holding your drawn fires")
    return json.loads(path.read_text())


def output_name(product_key: str, product: dict, fire: dict) -> str:
    op = fire["operational_period"]
    prepared = fire["prepared"]["iso"]
    date_part, time_part = prepared.split("T")
    return PRODUCTS["naming"]["pattern"].format(
        product=product_key,
        page_size=product["page_size"],
        orientation=product["orientation"],
        prepared_yyyymmdd=date_part.replace("-", ""),
        prepared_hhmm=time_part[:5].replace(":", ""),
        IncidentName=camel(fire["incident_name"]),
        UnitID=fire["unit_id_full"].replace("-", ""),
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


def apply_queries(layout, product: dict, fire: dict, report: list) -> None:
    """Compose the global query, the product query and the fire scope.

    The fire scope matters: all seven fires live in one geodatabase, so without
    it every sheet would show all seven perimeters at once."""
    queries = product.get("definition_query", {})
    global_q = PRODUCTS["global_definition_query"]
    scope = f"IncidentName = '{fire['incident_name']}'"

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
            if final != "1=0":
                final = f"({scope}) AND ({final})"
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


def export_fire(aprx, layouts, fire, wanted, out_dir, dpi, dry_run) -> tuple[int, list]:
    """Every requested product for one fire. Products go in a per-fire subfolder
    so 112 sheets do not land in one directory."""
    fire_out = os.path.join(out_dir, fire["color"].lower())
    os.makedirs(fire_out, exist_ok=True)

    exported, skipped = 0, []
    arcpy.AddMessage(f"\n=== {fire['incident_name']} ({fire['local_incident_id']}) — "
                     f"op {fire['operational_period']['date_display']} "
                     f"{fire['operational_period']['shift']}, "
                     f"{fire['perimeter_source']['acres']:,.0f} acres ===")

    for key in wanted:
        product = PRODUCTS["products"].get(key)
        if product is None:
            arcpy.AddWarning(f"{key}: not in config/map_products.yml, skipping")
            continue
        layout = layouts.get(key.lower())
        if layout is None:
            skipped.append(key)
            continue

        report: list[str] = []
        apply_queries(layout, product, fire, report)

        if product.get("safety_critical") and not verify_pio(layout, report):
            for line in report:
                arcpy.AddMessage(line)
            raise SystemExit(
                f"{fire['color']}/{key}: refusing to export a public-facing product "
                f"with tactical layers visible"
            )

        name = output_name(key, product, fire)
        if dry_run:
            arcpy.AddMessage(f"  {key:<14} would export -> {name}")
        else:
            export(layout, os.path.join(fire_out, name), dpi)
            arcpy.AddMessage(f"  {key:<14} -> {name}")
            exported += 1

    return exported, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aprx", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fire", help="single colour")
    ap.add_argument("--all-fires", action="store_true")
    ap.add_argument("--root", default=None,
                    help="folder holding <colour>/fire.json (default: data/fixtures)")
    ap.add_argument("--products", nargs="*", default=None,
                    help="subset of product keys; default is all 16")
    ap.add_argument("--dry-run", action="store_true", help="apply queries and report, do not export")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root else FIXTURE_ROOT
    if not root.is_absolute():
        root = ROOT / root

    colors = sorted(d.name for d in root.iterdir() if d.is_dir()) if root.exists() else []
    if args.fire:
        colors = [c for c in colors if c.lower() == args.fire.lower()]
    elif not args.all_fires:
        raise SystemExit("pass --fire <colour> or --all-fires")
    if not colors:
        raise SystemExit(f"no fire folders under {root}")

    aprx = arcpy.mp.ArcGISProject(args.aprx)
    layouts = {lyt.name.lower(): lyt for lyt in aprx.listLayouts()}
    wanted = args.products or list(PRODUCTS["products"].keys())
    os.makedirs(args.out, exist_ok=True)
    dpi = PRODUCTS["export"]["dpi"]

    total, all_skipped = 0, set()
    for color in colors:
        fire = load_fire(root, color)
        n, skipped = export_fire(aprx, layouts, fire, wanted, args.out, dpi, args.dry_run)
        total += n
        all_skipped.update(skipped)

    aprx.save()

    arcpy.AddMessage(f"\n{total} product(s) exported to {args.out} "
                     f"({len(colors)} fire(s) x {len(wanted)} product(s))")
    if all_skipped:
        arcpy.AddWarning(
            "no layout in the project for: " + ", ".join(sorted(all_skipped))
            + "\nBuild one layout per product key, named to match."
        )
    arcpy.AddMessage(
        "\nBefore these leave the ICP:\n"
        "  - every sheet carries the watermark: " + PRODUCTS["export"]["watermark"] + "\n"
        "  - open one in Avenza and confirm the georeferencing took\n"
        "  - photocopy the IAP sheet in black and white and confirm it still reads\n"
        "  - a second person confirms the public sheets have no tactical data on them"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
