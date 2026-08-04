# 4 — Map products

**16 products, one layout each, one layer set.** Seven fires x 16 products =
112 sheets. What makes the products different is the definition query, not the
layer list. All of it is encoded in `config/map_products.yml` and applied by
`scripts/arcpy/export_products.py`.

The product keys and page-size tokens below were decoded from a real incident's
published products, not invented — see
[08-naming-conventions.md](08-naming-conventions.md).

Full specs: <https://www.nwcg.gov/publications/pms936/map-product-standards>

## The products

| Key | Product | Size | Must carry |
|---|---|---|---|
| `iap` | IAP | 85x11 port | Ops content plus full SGD, sized for the packet |
| `ops` | Operations | arch C + arch E port | Everything. Ownership, structures, utilities, topo base |
| `airops` | Air Operations | arch E land | TFR, aerial hazards, retardant avoidance, helibase, dip/draft sites, coordinate table |
| `pilot` | Pilot | 11x17 land | Air ops simplified for a kneeboard |
| `brief` | Briefing (BAM) | arch E land | Simplified, **oversized symbols** |
| `pio` | Public Information | 85x11 + 11x17 port | Perimeter and closures only. **No tactical data.** |
| `trans` | Transportation | arch E port | Roads by surface and maintenance level, gates, closures, inset with street address |
| `progression` | Progression | 11x17 port | Daily perimeters symbolized by date |
| `avenza` | Avenza | 64x64 land | Everything, georeferenced, never printed |
| `camp` | Camp / ICP | 85x11 port | No Event data. Site plan. |
| `medtrans` | Medical Transport | arch E port | Evac routes, ambulance interception, hospitals. Label drive times, not miles |
| `closure` | Closure Order | arch E port | Boundary must match the written order exactly |
| `evac` | Evacuation | e land | The **sheriff's** zones, labelled verbatim as broadcast |
| `owner` | Ownership | 85x11 land | SMA and parcels under the fire. Drives cost apportionment |
| `allotments` | Range Allotments | arch C + arch E port | Pastures, fences, water developments |
| `repair` | Suppression Repair | arch E port | Every piece of ground suppression disturbed |

## Definition queries are a safety mechanism

Three products go to the public: `pio`, `evac` and `closure`. All three hard-set
their tactical queries:

```yaml
pio:
  definition_query:
    EventPoint: "1=0"
    EventLine:  "1=0"
    EventPolygon: "FeatureCategory IN ('Wildfire Daily Fire Perimeter','Closure Area','Evacuation Area')"
```

`1=0` rather than an inclusion list, deliberately. An inclusion list fails open:
add a new `FeatureCategory` next season and it appears on the public map because
nobody remembered to exclude it. `1=0` fails closed. If something genuinely
needs to be on the public sheet, it gets added on purpose.

Publishing drop points, crew locations, camps and helispots is a firefighter
safety issue, not a data-tidiness issue. `export_products.py` re-applies the
queries from config on every run and **refuses to export** any product
marked `safety_critical` if its point or line query is anything other than `1=0`.

Products are also scoped to one fire — all seven live in one geodatabase, so
without `IncidentName = '<colour>'` every sheet would show all seven perimeters
at once. `export_products.py` composes that scope in automatically.

## Extents

Three of them:

- `aoi` — the 10 × 10 mile box. Most products.
- `aoi_plus_tfr` — the 5 NM TFR is *wider than the AOI*. Do not clip it. Zoom the
  air ops and pilot layouts out until the whole circle fits, or the product is
  lying about the airspace. This is a deliberate teaching point in the scenario.
- `icp` — large scale, the ICP footprint only. `camp`.
- `aoi_wide` — zoomed out for the public-facing and transport products.

## Air ops coordinate table

Pilots fly the table, not the symbol. Generate it, never type it:

```
python3 scripts/make_coordinate_table.py --fire red                        # markdown
python3 scripts/make_coordinate_table.py --fire red --csv --out table.csv  # for a Pro table frame
python3 scripts/make_coordinate_table.py --fire red --full                 # adds DM and UTM columns
```

Covers helibase, helispots, dip sites, draft sites and medivac sites, in DMS,
sorted by type. A coordinate table that disagrees with the map is worse than no
table.

## Transportation

Follows the reference product's pattern: a wide route map plus an inset at the
destination with the physical street address spelled out. Drivers arrive at
night with no cell service and a printed sheet.

Symbolize roads on the USFS attributes rather than one flat line style — paved,
gravel, native surface, high-clearance/4WD only, closed to public. The classes
and their queries are in `config/map_products.yml` under
`products.trans.road_symbology`.

## Export

```
python scripts\arcpy\export_products.py --aprx projects\StormMountain.aprx --out products\pdf --all-fires
python scripts\arcpy\export_products.py --aprx ... --out ... --fire Red --products iap pio --dry-run
```

Geospatial PDF, 300 dpi, layers and attributes, georeferencing on. Filenames
follow the convention in [08-naming-conventions.md](08-naming-conventions.md).
