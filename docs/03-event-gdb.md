# 3 — The Event geodatabase

Everything red, blue and black on a standard fire map lives in **one**
geodatabase with **three** feature classes: `EventPoint`, `EventLine`,
`EventPolygon`.

Populate `FeatureCategory` and the symbology draws itself from the `.lyrx`. That
is the whole design. It is why a GISS from another team can open your project
and read it immediately.

## Rules

1. **Do not modify the schema.** Do not add fields, rename fields, or change
   types. Downstream tools and the `.lyrx` files bind to these names.
2. **Symbolize on `FeatureCategory` only.** If a feature draws wrong, the
   attribute is wrong. Do not fix it by overriding the symbol — you will have
   hidden a data error behind a cosmetic one.
3. **Recalculate `GISAcres` and `LengthMiles`** at the end of every edit
   session, before export. The acreage on the map and the acreage in the 209
   have to come from the same geometry.
4. **`IRWINID` stays null** for the whole exercise. See
   [07-guardrails.md](07-guardrails.md).
5. **Use `IsVisible = 'No'`, not deletion**, when a feature goes cold. A drop
   point that stops being used still happened.
6. **Suppress the perimeter outline where an Event Line sits on top of it.**
   A dozer line drawn over a perimeter outline reads as neither. This is a
   display setting on the polygon layer, not an edit to the geometry.

## Feature categories

The lists below are what `config/event_schema.json` enforces and what the mock
incident uses. **The domains get revised annually** — verify against the PMS 936
symbology pages before you finalize a legend or print a key:

- Point: <https://www.nwcg.gov/publications/pms936/symbology/pms-936-point-feature-symbology>
- Line: <https://www.nwcg.gov/publications/pms936/pms-936-symbology-event-line>
- Polygon: <https://www.nwcg.gov/publications/pms936/symbology/pms-936-polygon-feature-symbology>

### EventPoint

Incident Command Post · Camp · Staging Area · Helibase · Helispot · Drop Point ·
Dip Site · Draft Site · Hydrant · Water Tank · Safety Zone · Lookout · Repeater ·
Mobile Weather Unit · Access Point · Gate · Closure · Hazard · Medical Site ·
Medivac Site · Value at Risk · Structure · Spot Fire · Point of Origin · Sign ·
Internet Access

### EventLine

Completed Hand Line · Completed Dozer Line · Completed Road as Line · Completed
Fuel Break · Completed Mixed Construction Line · Proposed Dozer Line · Proposed
Hand Line · Proposed Road as Line · **Uncontrolled Fire Edge** · Contained Fire
Edge · Access Route · Escape Route · Pump and Hose Lay · Fire Spread Direction ·
Division Break · Branch Break

### EventPolygon

**Wildfire Daily Fire Perimeter** · Wildfire Final Fire Perimeter · Aerial
Hazard Area · Retardant Avoidance Area · Closure Area · Evacuation Area ·
Temporary Flight Restriction · Safety Zone · Structure Group · Management Action
Point Area · Repair Area

## Fields

Common to all three:

| Field | Type | Notes |
|---|---|---|
| `FeatureCategory` | TEXT 100 | Drives symbology. Domain-constrained. |
| `Label` | TEXT 100 | What the annotation shows: `DP 5`, `H-2`, `Div A`. |
| `IsVisible` | TEXT 5 | `Yes` / `No`. Hides without deleting. |
| `MapMethod` | TEXT 50 | How the geometry was captured. Feeds the source statement. |
| `GeometryID` | TEXT 50 | Stable identifier that survives an edit session. |
| `IncidentName` | TEXT 100 | |
| `IRWINID` | TEXT 50 | **Null on exercises.** |
| `CreateName` | TEXT 100 | |
| `CreateDate` | DATE | |
| `DeleteThis` | TEXT 5 | `Yes` / `No`. |
| `Comments` | TEXT 255 | |

`EventLine` adds `LengthMiles`. `EventPolygon` adds `GISAcres` and
`PolygonDateTime` — the latter is what the progression product symbolizes on.

## Which schema to use

If you have the official blank Event GDB from the GeoOps template, **use it**
and treat `config/event_schema.json` as documentation.

`config/event_schema.json` exists so that:

- the validator can lint exercise data on a machine with no ArcGIS install
- `scripts/arcpy/build_event_gdb.py` can produce a throwaway GDB for a classroom
- the schema is visible in one readable place

## Validate before you export

```
python3 scripts/validate_event_data.py
```

Catches the failures that actually happen: a `FeatureCategory` outside the
domain (the feature draws as a grey dot and nobody notices until the briefing),
a stale `GISAcres` that no longer matches the geometry, an `IRWINID` on exercise
data, unclosed rings, duplicate `GeometryID`s, and features that have wandered
outside the AOI. Exit code is non-zero on any error, so it can gate an export or
sit in a pre-commit hook.
