# 6 — Site-specific field work

The part nobody can download, and the part that makes the exercise about *this*
place rather than a generic 10 × 10 box. Budget a day. Collect with Field Maps
or a GPS unit, load into the Event GDB.

The mock incident in `data/mock_incident/` already has placeholder features for
all of this so the products can be built before anyone walks the ground. Replace
the placeholders with real surveyed positions — that swap is itself a good
exercise in what changes when the data gets real.

## What to collect

### Structures and values at risk
Camp buildings, lodge, cabins, dining hall. Collect as `Structure` points inside
a `Structure Group` polygon, with a `Value at Risk` point for the site as a
whole. Note construction type and defensible space while you are standing there
— you will not want to go back for it.

### Water
- Tanks, including capacity and whether the fitting is NH or NPSH
- Hydrants, including flow if the camp's public water system operator will tell you
- Any draft-capable pond: depth, approach, whether a tender can turn around

Water sources that a tender cannot physically reach are worse than no water
source, because they appear on the map as an option.

### Access
- Gates and cattle guards, with who holds the combination
- **Pinch points on Storm Mountain Rd.** Roughly 1.7 miles of winding Forest
  Service road is the access constraint the whole scenario turns on. Collect
  every turnout, every spot where two engines cannot pass, and every place a
  type 1 engine or a lowboy physically cannot make the corner.
- Turnaround points, by vehicle class

### Tactical candidates
- Candidate helispots — size, slope, surface, obstructions, prevailing wind
- Candidate safety zones — measure them, do not eyeball them; record the acreage
  and what fuel surrounds them

### Trails
Trail junction numbering on the Storm Mountain / Coon Hollow loop. Junctions are
how people describe where they are when they are lost, so the numbers on your
map need to match the numbers on the posts.

### Hazards
- The abandoned mine workings on the property. Open shafts and adits, as `Hazard`
  points with a description in `Comments`. Never anchor line to one.
- Standing dead and beetle-kill concentrations
- Powerline and utility crossings

### Communications
Cell and radio dead zones. Walk the ground with a radio and record where you
lose the repeater. This turns directly into a repeater-siting exercise, and the
mock incident already places `RPT Storm` to cover the Coon Hollow dead zone —
have students verify or move it based on what they actually find.

## Collection standards

- Set `MapMethod` honestly. `GPS-Walked` and `Digitized-Topo` mean different
  things about how much you should trust the position, and the source statement
  on the map inherits it.
- Put something in `Comments`. "Locked" is worth more than a perfect coordinate
  with no context.
- Give every feature a `Label` that matches what is painted on the ground or
  spoken on the radio.
- Photograph everything. Field Maps attachments cost nothing and answer
  arguments later.

## After collection

```
python3 scripts/validate_event_data.py
```

then reload into the Event GDB. Recalculate `GISAcres` and `LengthMiles` before
you export anything.
