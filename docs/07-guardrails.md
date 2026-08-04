# 7 — Training-exercise guardrails

Read this before you make the first product, not after someone asks where the
map on the wall came from.

Exercise fire maps look exactly like real fire maps. That is the point, and it
is also the risk. A convincing product that escapes the classroom can end up in
front of someone who acts on it.

## The rules

### 1. Watermark every sheet

```
TRAINING EXERCISE — NOT AN ACTUAL INCIDENT
```

Diagonally across the map frame, not tucked into a corner. It must survive being
cropped, photocopied, and photographed off a wall. Every product, every export,
including drafts and including the ones you think nobody will see.

### 2. Use fake identifiers that cannot collide

| | |
|---|---|
| Local incident ID | `EX-SD-TRNG-0001` |
| Unit ID | `SD-BKF-EX0001` |
| IMT | `EX TRAINING IMT 1` |
| IRWIN ID | **none — and none is ever to be assigned** |

Never a real IRWIN ID. Never a real CIMT number — a real team's designator on an
exercise product implies that team produced it.

`scripts/validate_event_data.py` fails the build if any feature carries an
`IRWINID`.

### 3. Never sync to NIFS or NIFC AGOL

Exercise data lives in a local file geodatabase. Do not connect a training
project to the National Incident Feature Service, for reading or for writing.

`scripts/arcpy/load_incident.py` refuses to run against a geodatabase path
containing `nifs`, `agol`, `arcgis.com`, `national_incident` or `featureserver`,
and refuses `.sde` connections outright. That check is a backstop for a tired
person at 0300, not a substitute for knowing the rule.

### 4. Do not post exercise perimeters to any public-facing service

No public web maps, no public feature services, no open data portals. A
perimeter polygon with a plausible date on it is the single most repostable
artifact this exercise produces.

### 5. Be especially careful with the public information product

PIO products are the ones that escape. They are designed to be handed out. If
you print one, make the exercise marking unmistakable — larger than you think is
tasteful.

`export_products.py` refuses to export the public product if its point or line
definition query is anything other than `1=0`.

## Why the public product's queries fail closed

`1=0` on `EventPoint` and `EventLine`, rather than a list of allowed categories.

An inclusion list fails *open*: someone adds a `FeatureCategory` next season, it
is not on anyone's exclusion list, and it appears on the public map. `1=0` fails
*closed*: new categories are invisible until somebody deliberately adds them.

Publishing drop points, crew locations, camps and helispots is a firefighter
safety issue. Design the mechanism so the failure mode is a missing symbol, not
an exposed crew.

## Before anything leaves the room

- [ ] Watermark present and legible on every sheet
- [ ] No real IRWIN ID anywhere — `validate_event_data.py` passes
- [ ] No real team designator in the author line
- [ ] Nothing synced to NIFS or NIFC AGOL
- [ ] Nothing published to a public-facing service
- [ ] A second person has confirmed the public sheet carries no tactical data
- [ ] Anything printed is collected at the end of the exercise, or destroyed

## This repository

The repository itself is part of the exercise footprint. `data/fixtures/<colour>/`
contains fabricated perimeters that look real enough to be mistaken for real.
Keep it private, and keep the `_warning` key in the GeoJSON files intact — it is
the only marking that survives someone opening a single file out of context.
