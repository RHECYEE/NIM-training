"""Turn the fetched GeoJSON into a ready-to-draw ArcGIS Pro project.

    python scripts\\arcpy\\build_project.py --incident D:\\incidents\\2026_StormMountain

REQUIRES arcpy. NOT executed in CI — see the note at the bottom of this docstring.

This is the step between "files on disk" and "open Pro and start drawing":

  1. base_data.gdb   — every fetched GeoJSON converted to a feature class and
                       projected to EPSG:26913
  2. site.gdb        — the 12 leased mining claims, split by fire district
  3. StormMountain.aprx — a project whose map is already in UTM 13N, with every
                       layer added in sensible draw order, key layers labelled,
                       and the Event feature classes on top ready to edit

After this you open one file and draw. Nothing else to add, nothing to set.

Layer order matters and is deliberate: Event layers on top (you are editing
them), then the leased property and jurisdiction, then transportation, then
hydro, then ownership and PLSS underneath. Anything you cannot see, you will not
draw against.

NOT TESTED HERE. This repo has no ArcGIS install, so every arcpy path in it is
unrun. Optional steps are individually wrapped so a version difference degrades
to a warning instead of killing the build.
"""

from __future__ import annotations

import argparse
import glob
import os
import pathlib
import sys

try:
    import arcpy
except ImportError:  # pragma: no cover
    sys.exit("arcpy not found. Run this from the ArcGIS Pro Python environment.")

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml not found. Clone the arcgispro-py3 environment and install it there.")

ROOT = pathlib.Path(__file__).resolve().parents[2]
SITE = yaml.safe_load((ROOT / "config" / "site.yml").read_text())
SERVICES = yaml.safe_load((ROOT / "config" / "services.yml").read_text())

import json  # noqa: E402

AOI = json.loads((ROOT / "config" / "aoi.json").read_text())
EPSG = AOI["crs"]["projected"]["epsg"]
SR = arcpy.SpatialReference(EPSG)

# Bottom of the drawing order first. addDataFromPath puts each new layer on top,
# so adding in this order leaves Event data at the very top where it belongs.
DRAW_ORDER = [
    ("plss_township", "PLSS Townships"),
    ("plss_section", "PLSS Sections"),
    ("ownership", "USFS Ownership"),
    ("nhd_area", "NHD Areas"),
    ("nhd_waterbody", "NHD Waterbodies"),
    ("nhd_flowline", "NHD Flowlines"),
    ("roads_closed", "Roads closed to motorized use"),
    ("roads", "USFS Roads"),
    ("trails", "USFS Trails"),
    ("leased_parcels", "LEASED PROPERTY - 12 claims"),
]

LABEL_FIELDS = {
    "trails": "trail_name",
    "roads": "name",
    "plss_section": "FRSTDIVNO",
    "leased_parcels": "Subdivisio",
}

EVENT_LAYERS = ["EventPolygon", "EventLine", "EventPoint"]


def convert_geojson(src_dir: pathlib.Path, gdb: str, names: list[str]) -> list[str]:
    """GeoJSON -> feature class, projected to the map's CRS."""
    made = []
    for name in names:
        src = src_dir / f"{name}.geojson"
        if not src.exists():
            arcpy.AddWarning(f"  {name}: no {src.name} — skipped")
            continue
        raw = os.path.join(gdb, f"{name}_raw")
        out = os.path.join(gdb, name)
        try:
            arcpy.conversion.JSONToFeatures(str(src), raw)
            desc = arcpy.Describe(raw)
            if desc.spatialReference.factoryCode == EPSG:
                arcpy.management.Rename(raw, out)
            else:
                arcpy.management.Project(raw, out, SR)
                arcpy.management.Delete(raw)
            n = int(arcpy.management.GetCount(out)[0])
            arcpy.AddMessage(f"  {name:<18} {n:>6} features")
            made.append(out)
        except arcpy.ExecuteError:
            arcpy.AddWarning(f"  {name}: conversion failed — {arcpy.GetMessages(2)}")
    return made


def split_by_fire_district(gdb: str) -> None:
    """Two feature classes so the split boundary is impossible to miss.

    The fire district line runs THROUGH the leased property: nine claims are
    Rockerville, three are Whispering Pines. Split them so the map shows it
    rather than relying on someone reading an attribute table.
    """
    parcels = os.path.join(gdb, "leased_parcels")
    if not arcpy.Exists(parcels):
        return
    fields = {f.name for f in arcpy.ListFields(parcels)}
    if "Fire" not in fields:
        arcpy.AddWarning("  leased_parcels has no Fire field — skipping district split")
        return
    for district, out_name in (("Rockerville", "leased_rockerville"),
                               ("Whispering Pines", "leased_whisperingpines")):
        out = os.path.join(gdb, out_name)
        where = f"Fire LIKE '{district}%'"
        try:
            arcpy.analysis.Select(parcels, out, where)
            n = int(arcpy.management.GetCount(out)[0])
            arcpy.AddMessage(f"  {out_name:<24} {n:>3} claims  ({district} FD)")
        except arcpy.ExecuteError:
            arcpy.AddWarning(f"  district split failed for {district}")


def add_layer(m, source: str, label_field: str | None, visible: bool = True):
    try:
        lyr = m.addDataFromPath(source)
    except Exception as exc:  # noqa: BLE001
        arcpy.AddWarning(f"  could not add {source}: {exc}")
        return None
    lyr.visible = visible
    if label_field:
        try:
            fields = {f.name.lower() for f in arcpy.ListFields(source)}
            if label_field.lower() in fields:
                for lc in lyr.listLabelClasses():
                    lc.expression = f"$feature.{label_field}"
                lyr.showLabels = True
        except Exception:  # noqa: BLE001 - labelling is a nicety, never fatal
            arcpy.AddWarning(f"  could not label {lyr.name}")
    return lyr


def find_blank_template() -> str | None:
    candidates = []
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if not base:
            continue
        candidates.append(os.path.join(base, "ArcGIS", "Pro", "Resources",
                                       "ProTemplates", "Blank.aprx"))
        candidates.extend(glob.glob(os.path.join(base, "ArcGIS", "Pro", "Resources",
                                                 "ProTemplates", "*.aprx")))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--incident", required=True, help="the incident folder")
    ap.add_argument("--template", help="an .aprx to base the project on")
    ap.add_argument("--name", default="StormMountain")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    arcpy.env.overwriteOutput = True
    incident = pathlib.Path(args.incident)
    base_dir = incident / "base_data"
    site_dir = ROOT / "data" / "site"
    projects = incident / "projects"
    projects.mkdir(parents=True, exist_ok=True)

    base_gdb = str(incident / "base_data" / "base_data.gdb")
    event_gdb = str(incident / "incident_data" / "event.gdb")
    aprx_path = str(projects / f"{args.name}.aprx")

    if os.path.exists(aprx_path) and not args.overwrite:
        arcpy.AddError(f"{aprx_path} exists. Pass --overwrite to rebuild it.")
        return 1

    # ---------------------------------------------------------- geodatabases --
    arcpy.AddMessage("Converting base data")
    if not arcpy.Exists(base_gdb):
        arcpy.management.CreateFileGDB(str(base_dir), "base_data.gdb")
    convert_geojson(base_dir, base_gdb, [s["id"] for s in SERVICES["layers"]])

    arcpy.AddMessage("\nConverting the leased property")
    convert_geojson(site_dir, base_gdb, ["leased_parcels", "leased_extent"])
    split_by_fire_district(base_gdb)

    if not arcpy.Exists(event_gdb):
        arcpy.AddWarning(
            f"\n{event_gdb} does not exist. Run build_event_gdb.py first, or the "
            f"project will have nothing to draw into."
        )

    # ------------------------------------------------------------- project --
    arcpy.AddMessage("\nBuilding the project")
    template = args.template or find_blank_template()
    if not template:
        arcpy.AddError(
            "No .aprx template found. Pass --template pointing at any existing "
            "project, or at <Pro>\\Resources\\ProTemplates\\Blank.aprx"
        )
        return 1

    aprx = arcpy.mp.ArcGISProject(template)
    aprx.saveACopy(aprx_path)
    aprx = arcpy.mp.ArcGISProject(aprx_path)

    m = aprx.listMaps()[0]
    m.name = f"{args.name} - UTM 13N"
    try:
        m.spatialReference = SR
        arcpy.AddMessage(f"  map CRS set to EPSG:{EPSG}")
    except Exception as exc:  # noqa: BLE001
        arcpy.AddWarning(f"  could not set the map CRS ({exc}). SET IT BY HAND before drawing.")

    for name, _pretty in DRAW_ORDER:
        source = os.path.join(base_gdb, name)
        if arcpy.Exists(source):
            add_layer(m, source, LABEL_FIELDS.get(name))

    # The district split goes above the parcels so the boundary reads at a glance.
    for name in ("leased_whisperingpines", "leased_rockerville"):
        source = os.path.join(base_gdb, name)
        if arcpy.Exists(source):
            add_layer(m, source, None)

    if arcpy.Exists(event_gdb):
        for name in EVENT_LAYERS:
            source = os.path.join(event_gdb, name)
            if arcpy.Exists(source):
                add_layer(m, source, "Label")

    # -------------------------------------------------------------- extent --
    try:
        e = AOI["extent_utm_26913"]
        cam = m.defaultCamera
        cam.setExtent(arcpy.Extent(e["xmin"], e["ymin"], e["xmax"], e["ymax"],
                                   spatial_reference=SR))
        arcpy.AddMessage("  default extent set to the AOI")
    except Exception:  # noqa: BLE001
        arcpy.AddWarning("  could not set the default extent — zoom to the AOI by hand")

    aprx.defaultGeodatabase = event_gdb if arcpy.Exists(event_gdb) else base_gdb
    aprx.homeFolder = str(incident)
    aprx.save()

    # --------------------------------------------------------------- report --
    arcpy.AddMessage(f"\nProject: {aprx_path}")
    arcpy.AddMessage(f"  layers        : {len(m.listLayers())}")
    arcpy.AddMessage(f"  editing into  : {aprx.defaultGeodatabase}")
    arcpy.AddMessage("\nOpen it and draw. Read docs/10-digitizing-guide.md first.")
    arcpy.AddWarning(
        "\nThe fire district boundary runs THROUGH the leased property: "
        "9 claims Rockerville, 3 claims Whispering Pines (no ambulance district "
        "on record). See docs/11-leased-property.md."
    )
    arcpy.AddMessage("\nTRAINING EXERCISE - NOT AN ACTUAL INCIDENT")

    # The .lyrx symbology from the GeoOps template still has to be pointed at
    # this geodatabase; nothing here can do that for you.
    arcpy.AddWarning(
        "Still manual: repair the Event .lyrx paths to " + event_gdb +
        " so the official symbology and feature templates come through."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
