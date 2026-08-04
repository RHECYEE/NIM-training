"""Derive hillshade, contours, slope and aspect from the AOI DEM.

    python scripts\\arcpy\\derive_terrain.py --dem D:\\...\\base_data\\elevation\\dem.tif ^
        --out D:\\...\\base_data\\elevation

REQUIRES arcpy and a Spatial Analyst licence. NOT executed in CI.

Parameters come from config/aoi.json so the hillshade on the ops sheet and the
hillshade on the briefing sheet are the same hillshade. Clips to the AOI plus
the download buffer first — deriving contours across a whole 1-degree tile and
then clipping wastes an hour.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

try:
    import arcpy
    from arcpy.sa import Aspect, Contour, Hillshade, Slope
except ImportError:  # pragma: no cover
    sys.exit("arcpy / Spatial Analyst not found. Run this from the ArcGIS Pro Python environment.")

ROOT = pathlib.Path(__file__).resolve().parents[2]
AOI = json.loads((ROOT / "config" / "aoi.json").read_text())

SR = arcpy.SpatialReference(AOI["crs"]["projected"]["epsg"])
HS = AOI["hillshade_parameters"]
CONTOUR = AOI["contour_interval_ft"]
METERS_PER_FOOT = 0.3048


def buffered_extent():
    e = AOI["extent_utm_26913"]
    pad = AOI["download_buffer_miles"] * 1609.344
    return arcpy.Extent(e["xmin"] - pad, e["ymin"] - pad, e["xmax"] + pad, e["ymax"] + pad)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem", required=True, help="source DEM (1 m LiDAR preferred)")
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--vertical-units", choices=["meters", "feet"], default="meters",
                    help="vertical units of the source DEM")
    args = ap.parse_args()

    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = SR
    ext = buffered_extent()
    arcpy.env.extent = ext
    os.makedirs(args.out, exist_ok=True)

    dem_proj = os.path.join(args.out, "dem_aoi.tif")
    arcpy.management.ProjectRaster(
        args.dem, dem_proj, SR, resampling_type="BILINEAR"
    )
    arcpy.AddMessage(f"projected DEM -> {dem_proj}")

    dem_clip = os.path.join(args.out, "dem_clip.tif")
    arcpy.management.Clip(
        dem_proj, f"{ext.XMin} {ext.YMin} {ext.XMax} {ext.YMax}", dem_clip, clipping_geometry="NONE"
    )
    arcpy.AddMessage(f"clipped to AOI + {AOI['download_buffer_miles']} mi buffer")

    hs = Hillshade(dem_clip, HS["azimuth"], HS["altitude"], "NO_SHADOWS", HS["z_factor"])
    hs.save(os.path.join(args.out, "hillshade.tif"))
    arcpy.AddMessage(f"hillshade az {HS['azimuth']} alt {HS['altitude']} z {HS['z_factor']}")

    # Contours are specified in feet. If the DEM is in metres, convert the
    # interval rather than the raster so elevations stay in source units.
    if args.vertical_units == "meters":
        intermediate = CONTOUR["intermediate"] * METERS_PER_FOOT
        index = CONTOUR["index"] * METERS_PER_FOOT
        arcpy.AddMessage(
            f"DEM is in metres: {CONTOUR['intermediate']} ft -> {intermediate:.4f} m interval"
        )
    else:
        intermediate, index = CONTOUR["intermediate"], CONTOUR["index"]

    Contour(dem_clip, os.path.join(args.out, "contour_intermediate.shp"), intermediate)
    Contour(dem_clip, os.path.join(args.out, "contour_index.shp"), index)
    arcpy.AddMessage(
        f"contours: {CONTOUR['intermediate']} ft intermediate / {CONTOUR['index']} ft index"
    )

    Slope(dem_clip, "PERCENT_RISE").save(os.path.join(args.out, "slope_pct.tif"))
    Aspect(dem_clip).save(os.path.join(args.out, "aspect.tif"))
    arcpy.AddMessage("slope (percent rise) and aspect written")

    arcpy.CheckInExtension("Spatial")
    arcpy.AddMessage("\nLabel the index contours, not the intermediate ones, or the sheet goes solid brown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
