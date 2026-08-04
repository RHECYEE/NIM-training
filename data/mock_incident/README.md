# Mock incident data

## TRAINING EXERCISE — NOT AN ACTUAL INCIDENT

Everything in this folder is **fabricated**. No perimeter, line or point here
describes anything that ever happened.

The geometry is placed inside the real Storm Mountain AOI so the exercise sits
on real terrain, real roads and real ownership. That is what makes it useful for
training and also what makes it plausible enough to be mistaken for real. Treat
it accordingly: see [../../docs/07-guardrails.md](../../docs/07-guardrails.md).

## Files

| File | Features |
|---|---|
| `eventpoint.geojson` | 45 |
| `eventline.geojson` | 17 |
| `eventpolygon.geojson` | 10 |

CRS is WGS84 lon/lat (`CRS84`), per the GeoJSON spec. Reproject to EPSG:26913 on
load — `scripts/arcpy/load_mock_incident.py` does this.

## Regenerating

```
python3 scripts/make_mock_incident.py
python3 scripts/validate_event_data.py
```

Do not hand-edit these files. `GISAcres` and `LengthMiles` are computed from the
geometry by the generator, and the validator fails the build if a stored value
drifts from what the geometry actually measures.

## The scenario

Ignition on the west side of the AOI, wind-driven run to the northeast over
three burning periods. The head is pointed at the Storm Mountain Training
Grounds.

| Operational period | Date | Acres |
|---|---|---|
| 1 | 07/26/2026 | 241 |
| 2 | 07/27/2026 | 775 |
| 3 | 07/28/2026 | 1,765 |

Completed line: 4.44 miles.

What the scenario is built to teach:

- **The camp is a value at risk.** A `Structure Group` polygon and individual
  `Structure` points sit directly in the path of the head.
- **Access is the constraint.** Storm Mountain Rd is roughly 1.7 miles of
  winding Forest Service road with a turnaround at DP 3. Everything heavier than
  a type 6 stops there. A Management Action Point covers the trigger to evacuate
  the training grounds.
- **The TFR is wider than the AOI.** The 5 NM circle does not fit in the
  10 × 10 mile box, so the air ops and pilot layouts need a wider extent than
  ops. Clipping it would misrepresent the airspace.
- **Real hazards.** Two abandoned mine workings, a powerline crossing, and heavy
  beetle-kill — all things the actual property has, all things you do not anchor
  line to.
- **A communications problem.** `RPT Storm` is sited to cover the Coon Hollow
  dead zone. Have students verify it against what they find on the ground.
- **Divisions that span sheets.** Div A / Div Z / Div M with a branch break,
  arranged so fitting whole divisions on one sheet takes actual thought.

## Identifiers

| | |
|---|---|
| Incident | Storm Mountain |
| Local incident ID | `EX-SD-TRNG-0001` |
| Unit ID | `SD-BKF-EX0001` |
| IRWIN ID | none, and none is ever to be assigned |

All fabricated and chosen so they cannot collide with a real incident.
