# 10 — Digitizing guide

**This is the page you work from at the laptop.** It says exactly what to draw
for each of the seven fires, what to attribute, and what you can leave alone
because the pipeline derives it.

## The division of labour

| You draw | The pipeline derives |
|---|---|
| Fire perimeter polygon | Contained / Uncontrolled Fire Edge |
| Helispot points | Coordinate tables (DMS, DM, UTM) |
| Drop point **locations** | Drop point **numbers** |
| Which trail segments are being held | `Completed Hand Line` features |
| Which road segments are being held | `Completed Road as Line` features |
| Division / branch breaks | Acreage, line mileage, source statements |
| Anything unusual for that fire | All 16 products |

The premise is that almost everything except the perimeter is static. Cabins,
roads and trails do not move between incidents. What changes per fire is **where
the fire is**, **which trail segments are line**, and **the drop point numbers**.

## Before you start

Double-click **`START.cmd`**.

That does all of it: folder tree, base data, the leased property's 12 parcels,
the Event geodatabase, and an `.aprx` with every layer loaded, the map already
in EPSG:26913, and the Event layers on top ready to edit.

**One manual step it cannot do for you:** repair the Event `.lyrx` paths from
the GeoOps template to your Event geodatabase, so the official symbology and
feature templates come through. Skipping that is what makes digitizing
miserable — you end up hand-styling features one at a time.

Read [11-leased-property.md](11-leased-property.md) once before you draw. The
fire district boundary runs through the property, which affects where a
sensible division break goes.

## Draw once: the static layer

These are the same for all seven fires. Place them one time in
`data/static/`, and every fire reuses them.

| Category | What |
|---|---|
| `Structure` | Lodge, dining hall, cabins — one point per building |
| `Value at Risk` | The training grounds as a whole |
| `Water Tank`, `Hydrant` | Camp water |
| `Gate`, `Access Point` | Storm Mountain Rd gates, the US-16 junction |
| `Incident Command Post`, `Camp` | Where they actually go |
| `Repeater`, `Internet Access`, `Sign` | Comms and signage |

A static feature that does not matter for a given fire stays in the data with
`IsVisible = 'No'` on that fire's copy. **Do not delete it** — a cabin that is
out of the way this week is still a cabin.

## Draw per fire: the seven perimeters

One `EventPolygon` per fire, `FeatureCategory = 'Wildfire Daily Fire Perimeter'`.

Required attributes:

| Field | Value |
|---|---|
| `FeatureCategory` | `Wildfire Daily Fire Perimeter` |
| `Label` | `<Colour> MM/DD`, e.g. `Red 07/28` |
| `IncidentName` | The colour: `Red`, `Orange`, … |
| `PolygonDateTime` | When that perimeter was collected |
| `MapMethod` | Honestly — `Infrared Image`, `GPS-Flight`, `Hand Sketch` |
| `IsVisible` / `DeleteThis` | `Yes` / `No` |
| `IRWINID` | **Leave null.** Always. |

Leave `GISAcres` alone — it gets calculated, never typed.

**Draw two or three daily perimeters per fire** if you want the progression
product to have anything to show. Same category, different `PolygonDateTime`,
each one nested inside the next.

Colours, incident IDs and drop point blocks are already assigned in
`config/fires.yml`. Match them.

## Draw per fire: helispots and drop points

**Helispots** — `FeatureCategory = 'Helispot'`, `Label` `H-1`, `H-2`, … Set
`Comments` to something useful: *"Ridgetop, one ship at a time"*, *"Dusty,
needs water"*. The coordinate table pulls `Comments` through to the pilot sheet.

**Drop points** — `FeatureCategory = 'Drop Point'`. Place them where they go and
**do not number them**. Instead set:

| Field | Value |
|---|---|
| `DIVISION` | `A`, `Z`, `M` — which division the drop point is in |

`scripts/derive_tactical.py` assigns the numbers, using that fire's block from
`config/fires.yml` and ordering them the way a driver encounters them along the
access route. That is why numbers differ between incidents and why they come out
grouped with gaps, the way they do on a real fire:

```
Red     DP 50  51  52  53  |  70  71  |  190  191
Orange  DP 10  12  14  16  |  30  32  |  210  212
Violet  DP 500 501 502 503 |  520 521 |  540  541
```

## Mark per fire: which trails and roads are line

**You do not draw hand line.** A trail on the fire edge is being held as hand
line — that is why a crew is standing on it. Mark the trails layer and the
derivation converts them.

Two ways to mark a segment, in priority order:

1. **Explicit** — set `LINE_STATUS` on the trail or road feature:

   | Value | Result |
   |---|---|
   | `completed` | Becomes `Completed Hand Line` / `Completed Road as Line` |
   | `proposed` | Becomes `Proposed Hand Line` / `Proposed Road as Line` |
   | `none` | Forced to stay base data even if it runs along the fire |

2. **Automatic** — leave `LINE_STATUS` empty and any trail running within
   **75 m** of the perimeter becomes `Completed Hand Line`; any road within
   **60 m** becomes `Completed Road as Line`.

Tune the buffers in `config/derivation.yml`. **Widen before you narrow** — a
hand-drawn perimeter and a surveyed trail centreline will not coincide, and too
tight silently drops line you are actually holding.

`LINE_STATUS = none` is the important escape hatch. The template's Old Mine
Trail runs straight through the burn but nobody is on it, so it stays a trail.

## Draw per fire: divisions and anything unusual

- `Division Break` / `Branch Break` — you draw these; nothing can infer them.
- `Safety Zone`, `Medical Site`, `Medivac Site`, `Dip Site`, `Draft Site`
- `Hazard` — the abandoned mine workings, powerline crossings, snag patches
- `Access Route` — **draw at least one.** Drop point ordering projects onto it;
  with no access route the numbers fall back to draw order.
- Polygons: `Closure Area`, `Evacuation Area`, `Aerial Hazard Area`,
  `Retardant Avoidance Area`, `Structure Group`, `Repair Area`,
  `Management Action Point Area`

Several products are empty without these. `evac` needs `Evacuation Area`,
`closure` needs `Closure Area`, `repair` needs `Repair Area`.

## Then hand it back

Export each fire to `data/drawn/<colour>/` as GeoJSON —
`eventpoint.geojson`, `eventline.geojson`, `eventpolygon.geojson`, plus
`trails.geojson` and `roads.geojson` clipped to the AOI:

```
python3 scripts/derive_tactical.py --all --in data/drawn
python3 scripts/validate_event_data.py --root data/drawn
python scripts\arcpy\export_products.py --aprx <project.aprx> --out products\pdf --all-fires
```

Or work in the geodatabase directly and skip the export step:

```
python scripts\arcpy\derive_tactical.py --gdb <incident>\incident_data\event.gdb --fire Red
```

## What the derivation will tell you

```
fire       H/L  road  edge  held mi  open mi   DPs
Red          1     1     5     0.28     5.90     8
  trail: 'Old Mine Trail' forced to stay base data by LINE_STATUS=none
```

**If `held mi` is near zero and `open mi` is the whole perimeter**, your line is
drawn too far off the perimeter for the `held_buffer_m` (90 m default) to
connect them. That is the derivation failing *safe* — unknown reads as
uncontrolled, never the reverse — but it means the map is wrong and you need to
either move the line onto the edge or widen the buffer.

**The derived fire edge is a starting point, not an answer.** Ops confirms it
every operational period. A stretch wrongly shown as contained is how people get
hurt, which is why the tool prints that warning on every run and why the
contained/uncontrolled split is the one thing on this list you should never
accept without looking at it.

## Before you draw anything real

Run the whole pipeline against the fixtures once, so you have seen what correct
output looks like:

```
python3 scripts/make_fires.py
python3 scripts/derive_tactical.py --all --in data/fixtures
python3 scripts/validate_event_data.py
```

The fixtures are throwaway geometry that exists only to prove the pipeline
works. They are not the exercise.
