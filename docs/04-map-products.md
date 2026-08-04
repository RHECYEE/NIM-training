# 4 — Map products

Nine products, one layout each, **one layer set**. What makes them different is
the definition query, not the layer list. All of it is encoded in
`config/map_products.yml` and applied by `scripts/arcpy/export_products.py`.

Full specs: <https://www.nwcg.gov/publications/pms936/map-product-standards>

## The products

| Product | Size | Must carry |
|---|---|---|
| **IAP** | 8.5×11 port | Ops content plus full SGD, sized for the IAP packet |
| **Operations** | Arch C port | Perimeter; all Event lines; all Event points; division and branch breaks; ownership; special management areas; structures; utilities; topo base |
| **Air Operations** | Arch E land | Perimeter and edges; TFR; aerial hazards; retardant avoidance; helibase and helispots; dip and draft sites; drop points; division breaks; lat-long table for key points |
| **Pilot** | 11×17 land | Air ops content simplified for a kneeboard |
| **Briefing (BAM)** | Arch E land | Simplified. Perimeter, division breaks, camps, drop points, helispots, planned and completed line, major access. **Oversized symbols.** |
| **Public Information** | 8.5×11 port | Perimeter only. Closures, communities, admin boundaries, simple base. **No tactical data.** |
| **Facilities** | 8.5×11 port | No Event data. ICP functional areas. |
| **Transportation** | 8.5×11 port | Roads by type; gates; closures; drop points; access routes |
| **Progression** | Arch C port | Daily perimeters symbolized by date |

## Definition queries are a safety mechanism

The public product's queries are hard-set:

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
queries from config on every run and **refuses to export** the public product if
the point or line query is anything other than `1=0`.

## Extents

Three of them:

- `aoi` — the 10 × 10 mile box. Most products.
- `aoi_plus_tfr` — the 5 NM TFR is *wider than the AOI*. Do not clip it. Zoom the
  air ops and pilot layouts out until the whole circle fits, or the product is
  lying about the airspace. This is a deliberate teaching point in the scenario.
- `icp` — large scale, the ICP footprint only. Facilities.

## Air ops coordinate table

Pilots fly the table, not the symbol. Generate it, never type it:

```
python3 scripts/make_coordinate_table.py                       # markdown
python3 scripts/make_coordinate_table.py --csv --out table.csv # for a Pro table frame
python3 scripts/make_coordinate_table.py --full                # adds DM and UTM columns
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
`products.transportation.road_symbology`.

## Export

```
python scripts\arcpy\export_products.py --aprx projects\StormMountain.aprx --out products\pdf
python scripts\arcpy\export_products.py --aprx ... --out ... --products iap pio --dry-run
```

Geospatial PDF, 300 dpi, layers and attributes, georeferencing on. Filenames
follow the convention in [08-naming-conventions.md](08-naming-conventions.md).
