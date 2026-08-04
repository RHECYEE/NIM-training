# 9 — QA checklist

Run before any product leaves the ICP. Fast to work through once you know it.

## Data

- [ ] `python3 scripts/validate_event_data.py` passes with no errors
- [ ] `GISAcres` and `LengthMiles` recalculated after the last edit
- [ ] Acreage on the map matches the acreage in the 209 — same geometry, same number
- [ ] `FeatureCategory` correct on every feature. Nothing drawing as a grey dot.
- [ ] `MapMethod` honest on everything — the source statement inherits it
- [ ] `IRWINID` null everywhere
- [ ] Event GDB backed up to `incident_data/backup/`

## Projection

- [ ] Map view is EPSG:26913, not a geographic CRS
- [ ] Every base layer projected on ingest — no eleven-CRS project
- [ ] Datum stated on every sheet carrying a grid or a coordinate

## Every sheet — STANDL-SGD

- [ ] **S** — graphical scale bar, not a ratio
- [ ] **T** — map type, incident name, unit ID / local incident ID, operational period
- [ ] **A** — author
- [ ] **N** — north arrow (declination if teaching land nav)
- [ ] **D** — date and time of preparation, distinct from the operational period
- [ ] **L** — legend showing only symbols actually on the sheet
- [ ] **S** — source statement: collection date/time, method, projection
- [ ] **G** — graticule with lat-long ticks
- [ ] **D** — datum

## Cartography

- [ ] Sequential map sheet ID
- [ ] Whole divisions fit on one sheet wherever possible
- [ ] Sheets overlap
- [ ] Perimeter outline suppressed where an Event Line sits on top of it
- [ ] Index contours labelled, intermediate contours not
- [ ] **Photocopy test** — print the IAP sheet, photocopy it in black and white,
      confirm it still reads. Not a thought experiment; actually do it once per
      exercise.

## Per product

- [ ] **Air ops / pilot** — the whole 5 NM TFR fits on the sheet. It is wider
      than the AOI; if it is clipped, the product is lying about the airspace.
- [ ] **Air ops / pilot** — coordinate table generated from the geometry, not
      typed, and every row matches its symbol
- [ ] **Briefing** — BAM large symbols applied. Readable from the back of the tent.
- [ ] **Public information** — no drop points, no crew locations, no camps, no
      helispots. **Second person confirms.**
- [ ] **Transportation** — roads symbolized by surface and maintenance level;
      inset carries the physical street address
- [ ] **Facilities** — no Event data at all
- [ ] **Progression** — daily perimeters ordered by `PolygonDateTime`, oldest on top

## Export

- [ ] Geospatial PDF, georeferencing on
- [ ] **Open one in Avenza** and confirm the georeferencing actually took. Do
      this every time; it silently fails often enough to matter.
- [ ] Filenames follow the convention — prepared date/time and operational
      period are not swapped
- [ ] Previous period's products archived, not overwritten

## Exercise guardrails

- [ ] Watermark on every sheet, diagonal across the map frame, legible after photocopying
- [ ] No real IRWIN ID, no real team designator, no real incident number
- [ ] Nothing synced to NIFS or NIFC AGOL
- [ ] Nothing published to a public-facing service
- [ ] Printed products collected or destroyed at the end of the exercise

## The two-minute version

If you only have two minutes before the briefing:

1. Acreage right?
2. Datum on the sheet?
3. Watermark on the sheet?
4. Public sheet clean?
5. Photocopy test passed?
