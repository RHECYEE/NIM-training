# Storm Mountain Training Grounds — mock IMT fire map build-out

> ## TRAINING EXERCISE — NOT AN ACTUAL INCIDENT
>
> Every perimeter, line and point in this repository is fabricated. Nothing here
> describes a real fire. Read [docs/07-guardrails.md](docs/07-guardrails.md)
> before producing anything.

A complete, reproducible kit for building the standard NWCG fire map products
for a mock incident at Storm Mountain Training Grounds, Black Hills National
Forest, South Dakota — built to **PMS 936 (GeoOps)**.

**AOI** — 10 × 10 miles centred on 23740 Storm Mountain Rd, Rapid City, SD 57702
(43.964 N, −103.377 W), Pennington County, near Rockerville.
**CRS** — NAD 1983 UTM Zone 13N (EPSG:26913).

## Start here

**Do not build from scratch.** The NWCG GeoOps Incident Directory Structure
ships the blank Event geodatabase, the current official `.lyrx` symbology, the
BAM large-symbol layer file, and an ArcGIS Pro template with a layout per
product. Get it from the [Geospatial Training Unit tools
page](https://www.nwcg.gov/page/geospatial-training-unit-tools) first. Drawing
your own icons is wasted effort and makes the products look non-standard to
anyone who has worked an incident.

This repository is what the template does *not* give you: the AOI definition,
the data manifest, the fabricated incident, the per-product definition queries,
and the scripts that keep the numbers honest.

## Quick start

```bash
python3 scripts/make_aoi.py              # AOI extents in both CRSs
python3 scripts/make_mock_incident.py    # the fabricated incident, 72 features
python3 scripts/validate_event_data.py   # lint it
python3 scripts/make_coordinate_table.py # air ops lat/long table
```

Then, in the ArcGIS Pro Python environment:

```
python scripts\arcpy\build_event_gdb.py     --dest <incident>\incident_data
python scripts\arcpy\load_mock_incident.py  --gdb  <incident>\incident_data\event.gdb
python scripts\arcpy\derive_terrain.py      --dem  <dem.tif> --out <incident>\base_data\elevation
python scripts\arcpy\export_products.py     --aprx <project.aprx> --out <incident>\products\pdf
```

## Documentation

| | |
|---|---|
| [01 — Setup](docs/01-setup.md) | Get the GeoOps template, project setup sequence, CRS |
| [02 — Base data](docs/02-base-data.md) | What to download for the AOI and why it matters |
| [03 — Event geodatabase](docs/03-event-gdb.md) | Three feature classes, the domains, the rules |
| [04 — Map products](docs/04-map-products.md) | Nine products, one layer set, definition queries |
| [05 — Map elements](docs/05-map-elements.md) | STANDL-SGD, the title block, the map series |
| [06 — Field collection](docs/06-field-collection.md) | The part nobody can download |
| [07 — Guardrails](docs/07-guardrails.md) | **Read before producing anything** |
| [08 — Naming conventions](docs/08-naming-conventions.md) | Filename pattern, the two dates |
| [09 — QA checklist](docs/09-qa-checklist.md) | Run before anything leaves the ICP |

## Layout

```
config/
  aoi.json            10 x 10 mi box in UTM 13N and geographic. Generated.
  incident.json       Dynamic-text source: names, IDs, operational period, watermark.
  event_schema.json   Event Point/Line/Polygon fields and FeatureCategory domains.
  map_products.yml    Per-product page size, extent, definition queries, naming.
  sources.yml         Base-data acquisition manifest.

data/mock_incident/   The fabricated incident as GeoJSON. Generated.

scripts/              Pure Python, no dependencies. Run anywhere.
scripts/arcpy/        Require ArcGIS Pro. Not exercised in CI.

docs/                 The nine pages above.
```

## Two things worth knowing

**Acreage is computed, never typed.** `make_mock_incident.py` derives `GISAcres`
and `LengthMiles` from the geometry, and `validate_event_data.py` fails the
build if a stored value drifts more than 0.5% from what the geometry actually
measures. The number on the map and the number in the 209 come from the same
place, which is the only way they stay equal.

**The public product's definition queries fail closed.** `EventPoint` and
`EventLine` are hard-set to `1=0` rather than an inclusion list. An inclusion
list fails open — add a `FeatureCategory` next season and it appears on the
public map because nobody remembered to exclude it. Publishing drop points and
crew locations is a firefighter safety issue, so the failure mode needs to be a
missing symbol, not an exposed crew. `export_products.py` refuses to export the
public product if those queries are anything else.

## Reference

- [PMS 936 — NWCG Standards for Geospatial Operations](https://www.nwcg.gov/publications/pms936/nwcg-standards-for-geospatial-operations-pms-936)
- [PMS 936-1 — GISS Workflow](https://www.nwcg.gov/publications/pms936-1)
- [Symbology](https://www.nwcg.gov/publications/pms936/symbology) · [Map elements](https://www.nwcg.gov/publications/pms936/map-elements) · [Map product standards](https://www.nwcg.gov/publications/pms936/map-product-standards)
- [Geospatial Training Unit tools and templates](https://www.nwcg.gov/page/geospatial-training-unit-tools)
- [USFS data hub](https://data-usfs.hub.arcgis.com/) · [USGS National Map](https://apps.nationalmap.gov/downloader/) · [LANDFIRE](https://landfire.gov/)
- [SD DOT GIS](https://dot.sd.gov/inside-sddot/forms-publications/maps/gis/) · [SDGS digital data](https://www.sdgs.usd.edu/digitaldata/default.aspx)

**Verify the `FeatureCategory` domains against the PMS 936 symbology pages before
finalizing a legend.** They are revised annually.
