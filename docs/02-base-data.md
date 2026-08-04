# 2 — Base data

The machine-readable manifest is `config/sources.yml`. This page is the
narrative version and the part you cannot encode: what matters and why.

## The AOI

10 × 10 miles centred on 23740 Storm Mountain Rd, Rapid City, SD 57702
(43.964 N, −103.377 W) — Black Hills National Forest, Pennington County, near
Rockerville.

Exact extents live in `config/aoi.json`. Regenerate with
`python3 scripts/make_aoi.py`; do not hand-edit.

| | |
|---|---|
| UTM 13N (EPSG:26913) | 622155.2, 4861108.0 → 638248.6, 4877201.5 |
| Geographic (EPSG:4269) | N 44°02.268′ / S 43°53.407′ / W 103°28.747′ / E 103°16.478′ |
| Download buffer | AOI + 2 miles |

**Pull to the buffer, not to the box.** Layouts pan, the briefing map zooms out,
and the TFR is wider than the AOI. Clipping tight to the box guarantees white
corners on the first product you build.

## Terrain

The Black Hills has 1 m QL1/QL2 LiDAR coverage. Take it. Forty-foot contours
derived from a 1/3 arc-second DEM look mushy in this terrain, and part of the
point of this exercise is reading slope off the map.

Derive hillshade, contours, slope and aspect with
`scripts/arcpy/derive_terrain.py` so every product shares one hillshade:

- Hillshade: azimuth 315°, altitude 45°, z-factor 1
- Contours: 40 ft intermediate, 200 ft index — label the index only, or the
  sheet goes solid brown
- Slope in percent rise, for fire-behavior injects

If the DEM is in metres, convert the *interval*, not the raster. The script
does this and says so when it does.

## Transportation — the layer this exercise is actually about

Storm Mountain Rd is roughly 1.7 miles of winding Forest Service road, and it is
the constraint the whole scenario turns on. Get the attributes, not just the
lines:

- **USFS `RoadCore` (INFRA)** — keep `SURFACE_TYPE` and `OPER_MAINT_LEVEL`
  through the clip. The transportation product symbolizes on both.
- **MVUM for Black Hills NF** — tells you what a vehicle is *allowed* on, which
  the road layer does not.
- **`TrailNFS_Publish`** — Coon Hollow, the Storm Mountain loop, the Rockerville
  Flume Trail (NRT).
- **SD DOT** for state and county roads, **Pennington County** for local roads
  and 911 addressing.

Features you should see once these are loaded: US-16, Silver Mountain Rd, Storm
Mountain Rd, Coon Hollow trailhead, the Storm Mountain Trail loop, the
Rockerville Flume Trail, Spring Creek.

## Hydrography

NHD flowlines and waterbodies, plus WBD HUC12 if you want watershed context.
Spring Creek is the retardant-avoidance driver in the scenario and the draft
site sits on it, so it needs to be right.

## Ownership and jurisdiction

Surface Management Agency, USFS administrative forest and district boundaries,
PLSS, parcels, and the NIFC Jurisdictional Unit layer.

PLSS matters more than people expect: section corners are how ground resources
will describe locations to you over the radio, so the ops map needs the section
grid whether or not it looks tidy.

## Fuels

LANDFIRE FBFM40, canopy cover and canopy base height, for scenario realism and
fire-behavior injects. Historic NIFC perimeters are worth pulling as a sanity
check — if your exercise perimeter overlaps a real recent burn scar, the fuels
story does not survive a knowledgeable student.

## Values at risk

FEMA USA Structures for footprints, HIFLD for powerlines and substations. The
camp buildings, tanks, hydrants, gates, helispots and mine hazards are field
collection — see [06-field-collection.md](06-field-collection.md).

## Ingest rules

1. Clip to AOI + 2 mi buffer.
2. Project to EPSG:26913 **on ingest**. A project with eleven source CRSs will
   bite you at export.
3. Keep the source's own metadata. When someone asks where the road layer came
   from, the answer needs to be better than "the internet".
4. Base data is reference data about a real place. It is not incident data and
   it does not go in the Event geodatabase.
