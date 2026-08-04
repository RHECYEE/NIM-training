# Storm Mountain Training Grounds — mock IMT fire mapping exercise

> ## TRAINING EXERCISE — NOT AN ACTUAL INCIDENT
>
> Every perimeter, line and point produced here is fabricated. Nothing describes
> a real fire. Read [docs/07-guardrails.md](docs/07-guardrails.md) before
> producing anything.

Seven mock fires named for the colours of the rainbow, each producing the full
set of **16 NWCG map products** — 112 sheets — for the Storm Mountain Training
Grounds, Black Hills National Forest, South Dakota. Built to **PMS 936
(GeoOps)**.

**AOI** — 10 × 10 miles centred on 23740 Storm Mountain Rd, Rapid City, SD 57702
(43.964 N, −103.377 W), Pennington County, near Rockerville.
**CRS** — NAD 1983 UTM Zone 13N (EPSG:26913).

## How this works

**You draw. The pipeline derives. Then it builds every product.**

| You draw in ArcGIS Pro | The pipeline derives |
|---|---|
| Fire perimeter polygons | Contained / Uncontrolled Fire Edge |
| Helispots, dip sites, safety zones | Coordinate tables (DMS, DM, UTM) |
| Drop point **locations** | Drop point **numbers**, per-fire blocks |
| Which trails are being held as line | `Completed Hand Line` features |
| Which roads are being held as line | `Completed Road as Line` features |
| Division and branch breaks | Acreage, line mileage, source statements |
| | All 16 products × 7 fires |

The premise is that almost everything except the perimeter is static. Cabins,
roads and trails do not move between incidents. What changes per fire is where
the fire is, which trail segments are line, and the drop point numbers.

**[docs/10-digitizing-guide.md](docs/10-digitizing-guide.md) is the page to work
from at the laptop.**

## Start here

**Do not build from scratch.** The NWCG GeoOps Incident Directory Structure
ships the blank Event geodatabase, the current official `.lyrx` symbology, the
BAM large-symbol layer file, and an ArcGIS Pro template with a layout per
product. Get it from the [Geospatial Training Unit tools
page](https://www.nwcg.gov/page/geospatial-training-unit-tools) first. Drawing
your own icons is wasted effort and makes the products look non-standard to
anyone who has worked an incident.

This repository is what the template does *not* give you: the AOI, the data
manifest, the seven fire definitions, the derivation rules, the per-product
definition queries, and the scripts that keep the numbers honest.

## Quick start

Prove the pipeline works before drawing anything real:

```bash
python3 scripts/make_aoi.py                            # AOI extents in both CRSs
python3 scripts/make_fires.py                          # throwaway test fixtures
python3 scripts/derive_tactical.py --all --in data/fixtures
python3 scripts/validate_event_data.py                 # lint every fire
python3 scripts/make_coordinate_table.py --fire red    # air ops lat/long table
```

Then, in the ArcGIS Pro Python environment:

```
python scripts\arcpy\build_event_gdb.py   --dest <incident>\incident_data
python scripts\arcpy\derive_terrain.py    --dem <dem.tif> --out <incident>\base_data\elevation
                                          ... draw the seven fires ...
python scripts\arcpy\derive_tactical.py   --gdb <...>\event.gdb --fire Red ^
                                          --trails <...>\trails --roads <...>\roads
python scripts\arcpy\export_products.py   --aprx <project.aprx> --out products\pdf --all-fires
```

## The seven fires

Defined in [`config/fires.yml`](config/fires.yml). Each is an **independent
scenario**, not a concurrent incident — they share one base-data download and
one AOI.

| Fire | Incident ID | Op period | DP blocks | What it teaches |
|---|---|---|---|---|
| Red | EX-SD-TRNG-0001 | 07/28 day | 50 / 70 / 190 | Baseline. Head at the training grounds. |
| Orange | EX-SD-TRNG-0002 | 07/29 day | 10 / 30 / 210 | Small and early, no IR yet |
| Yellow | EX-SD-TRNG-0003 | 07/30 day | 100 / 120 / 230 | Divisions awkward to fit on one sheet |
| Green | EX-SD-TRNG-0004 | 07/31 **night** | 150 / 170 / 250 | The only night-shift product set |
| Blue | EX-SD-TRNG-0005 | 08/01 day | 300 / 320 / 270 | TFR falls off the AOI |
| Indigo | EX-SD-TRNG-0006 | 08/02 day | 400 / 420 / 440 | Hand-sketch perimeter, low confidence |
| Violet | EX-SD-TRNG-0007 | 08/03 day | 500 / 520 / 540 | Largest — forces the map-series talk |

## The 16 products

`iap` · `ops` · `airops` · `pilot` · `brief` · `pio` · `trans` · `progression` ·
`avenza` · `camp` · `medtrans` · `closure` · `evac` · `owner` · `allotments` ·
`repair`

Product keys, page-size tokens and the filename pattern were decoded from a real
incident's published products on the wildfire.gov FTP, so exercise output sorts
and reads like the real thing:

```
iap_85x11_port_20260728_0430_Red_SDBKFEX0001_0728day.pdf
```

## Documentation

| | |
|---|---|
| [01 — Setup](docs/01-setup.md) | GeoOps template, project setup, CRS |
| [02 — Base data](docs/02-base-data.md) | What to download and why it matters |
| [03 — Event geodatabase](docs/03-event-gdb.md) | Three feature classes, domains, rules |
| [04 — Map products](docs/04-map-products.md) | The products, definition queries |
| [05 — Map elements](docs/05-map-elements.md) | STANDL-SGD, title block, map series |
| [06 — Field collection](docs/06-field-collection.md) | The part nobody can download |
| [07 — Guardrails](docs/07-guardrails.md) | **Read before producing anything** |
| [08 — Naming conventions](docs/08-naming-conventions.md) | Filename pattern, the two dates |
| [09 — QA checklist](docs/09-qa-checklist.md) | Run before anything leaves the ICP |
| [10 — Digitizing guide](docs/10-digitizing-guide.md) | **What to draw, at the laptop** |

## Layout

```
config/
  aoi.json            10 x 10 mi box in UTM 13N and geographic. Generated.
  fires.yml           The seven fires: IDs, op periods, drop point blocks.
  derivation.yml      Trail->hand line, road->line, edge, DP numbering rules.
  event_schema.json   Event Point/Line/Polygon fields and FeatureCategory domains.
  map_products.yml    16 products: page size, extent, definition queries, naming.
  sources.yml         Base-data acquisition manifest.

data/drawn/<colour>/     What you export from Pro. The real exercise.
data/fixtures/<colour>/  Generated throwaway geometry. Proves the pipeline runs.

scripts/            Pure Python, no dependencies beyond pyyaml. Run anywhere.
scripts/arcpy/      Require ArcGIS Pro. Not exercised in CI.
docs/               The ten pages above.
```

## Three things worth knowing

**Acreage is computed, never typed.** `GISAcres` and `LengthMiles` come from the
geometry, and `validate_event_data.py` fails the build if a stored value drifts
from what the geometry measures. The number on the map and the number in the 209
come from the same place, which is the only way they stay equal.

**The public-facing products' definition queries fail closed.** `pio`, `evac` and
`closure` hard-set `EventPoint` and `EventLine` to `1=0` rather than listing
what is allowed. An inclusion list fails open — add a `FeatureCategory` next
season and it appears on the public map because nobody remembered to exclude it.
Publishing drop points and crew locations is a firefighter safety issue, so the
failure mode needs to be a missing symbol, not an exposed crew.
`export_products.py` refuses to export those products if the queries are
anything else.

**The derived fire edge is a starting point, not an answer.** Ops confirms the
contained/uncontrolled split every operational period. If no line is drawn near
the perimeter, the whole edge reads as uncontrolled — the tool fails toward
"unknown means open", never the reverse.

## Reference

- [PMS 936 — NWCG Standards for Geospatial Operations](https://www.nwcg.gov/publications/pms936/nwcg-standards-for-geospatial-operations-pms-936)
- [PMS 936-1 — GISS Workflow](https://www.nwcg.gov/publications/pms936-1)
- [Symbology](https://www.nwcg.gov/publications/pms936/symbology) · [Map elements](https://www.nwcg.gov/publications/pms936/map-elements) · [Map product standards](https://www.nwcg.gov/publications/pms936/map-product-standards)
- [Geospatial Training Unit tools and templates](https://www.nwcg.gov/page/geospatial-training-unit-tools)
- [USFS data hub](https://data-usfs.hub.arcgis.com/) · [USGS National Map](https://apps.nationalmap.gov/downloader/) · [LANDFIRE](https://landfire.gov/)
- [SD DOT GIS](https://dot.sd.gov/inside-sddot/forms-publications/maps/gis/) · [SDGS digital data](https://www.sdgs.usd.edu/digitaldata/default.aspx)

**Verify the `FeatureCategory` domains against the PMS 936 symbology pages before
finalizing a legend.** They are revised annually.
