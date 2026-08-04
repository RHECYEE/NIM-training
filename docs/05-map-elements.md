# 5 — Required map elements (STANDL-SGD)

Every product needs these. This is the checklist the reference products are
built to.

## STANDL

| | Element | Notes |
|---|---|---|
| **S** | Scale | A **graphical scale bar**, not a ratio. PDFs get reprinted at odd sizes and a "1:24,000" that was reprinted at 80% is a lie. |
| **T** | Title | Map type + incident name + unit ID / local incident ID + operational period date. |
| **A** | Author | Who prepared it. A name, so the question at 0530 has somewhere to go. |
| **N** | North arrow | Add magnetic declination if you are teaching land navigation. |
| **D** | Date and time of preparation | Distinct from the operational period. |
| **L** | Legend | Only the symbols actually on the sheet. |

## SGD

Required on the IAP map, recommended on all of them.

| | Element | Notes |
|---|---|---|
| **S** | Source statement | Date and time the perimeter was collected, the collection method, and the projection. |
| **G** | Graticule / grid | Lat-long ticks. |
| **D** | Datum | Stated whenever a grid or any coordinate appears. Non-negotiable — a coordinate without a datum can be several hundred metres from where you think. |

## The title block

Element order taken from the reference IAP sheet, so exercise products read the
same way as the real thing:

```
EX TRAINING IMT 1 | 7/28/2026 0430          <- author | date-time of preparation
Acres from IR                                <- collection method
North American 1983 Datum. Lat/Long Grid     <- datum
1,765 acres at 7/28/2026 at 0214 MDT         <- source statement
Storm Mountain                               <- incident name
EX-SD-TRNG-0001                              <- local incident ID
07/28/2026                                   <- operational period
IAP                                          <- product type
```

Drive all of it from dynamic text bound to `config/incident.json`. Change the
operational period in one place, not in fourteen text elements — and the acreage
comes from the geometry via `scripts/make_mock_incident.py`, never typed.

Two dates appear on every sheet and they are different, usually by a day:

- **Prepared** — when the PDF was made (7/28 0430)
- **Operational period** — what shift it is *for* (07/28 day)

## Map series

Per GeoOps map-series guidance:

- Sequential map sheet ID on every sheet
- Sheets overlap
- Fit whole divisions on one sheet wherever possible — a division supervisor
  should not need two pieces of paper to see their own division
- Design so it survives **black-and-white photocopying**. The IAP gets
  duplicated in B&W at 0500. Test it: print one, photocopy it, read it.
- Remove the perimeter polygon outline where an Event Line sits on top of it

## Watermark

Every sheet of this exercise carries:

```
TRAINING EXERCISE — NOT AN ACTUAL INCIDENT
```

Diagonally across the map frame, not tucked into a corner. It has to survive
being cropped, photocopied and photographed off a wall. See
[07-guardrails.md](07-guardrails.md).

## Reference

- Map elements: <https://www.nwcg.gov/publications/pms936/map-elements>
- Map product standards: <https://www.nwcg.gov/publications/pms936/map-product-standards>
