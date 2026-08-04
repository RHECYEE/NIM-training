# 11 — The leased property

Everything else in this repo is about a 10 × 10 mile AOI. This page is about the
**246 acres inside it that we control**, where people will actually be standing.

Machine-readable version: [`config/site.yml`](../config/site.yml).
Geometry: `data/site/leased_parcels.geojson`, refreshed by
`python3 scripts/fetch_site.py`.

## What the property actually is

**23740 Storm Mountain Rd, Rapid City, SD 57702** is not one parcel. It is
**12 contiguous patented lode mining claims — Mineral Survey 2049 —
246.54 acres**, held by the SD Annual Conference of the United Methodist Church
and leased by us for five years.

| Claim | PIN | Acres | Section | Fire district |
|---|---|---|---|---|
| EDITH #1 LODE | 5310400001 | 19.97 | 10 | Whispering Pines |
| EDITH #2 LODE | 5310400002 | 19.97 | 10 | Whispering Pines |
| MONTANA LODE | 5310400003 | 20.66 | 10 | Whispering Pines |
| UTAH LODE | 5314100002 | 20.66 | 14 | Rockerville |
| RED CROSS LODE | 5314100003 | 20.66 | 14 | Rockerville |
| NEVADA LODE | 5314100004 | 20.66 | 14 | Rockerville |
| DAN PATCH LODE | 5314100005 | 20.66 | 14 | Rockerville |
| GOLD DUST LODE | 5314100006 | 20.66 | 14 | Rockerville |
| ALASKA LODE | 5315200001 | 20.66 | 15 | Rockerville |
| OREGON LODE | 5315200002 | 20.66 | 15 | Rockerville |
| IDAHO LODE | 5315200003 | 20.66 | 15 | Rockerville |
| ARIZONA LODE | 5315200004 | 20.66 | 15 | Rockerville |

T1S R6E, Sections 10, 14 and 15. Centre roughly 43°58'05" N, 103°22'53" W —
UTM 13N 629848 E, 4869590 N.

All of it is county assessor record, and all of it is verifiable. The claim
boundaries are **real surveyed lines**, which means the exercise can use them as
real features: division breaks that follow a claim line are defensible, and a
crew can find one on the ground.

> Stated acreage (246.54) is the legal figure from the deeds. The county's
> polygons measure 253.02. A few percent apart, as parcel data always is. Use
> the stated figure when the number has legal weight; use the geometry for map
> extents and area calculations.

## The finding that matters most

**The fire district boundary runs through the property.**

| | |
|---|---|
| Sections 14 & 15 — 9 claims | **Rockerville Fire District** · Keystone Ambulance |
| Section 10 — 3 claims | **Whispering Pines Fire District** · *no ambulance district on record* |

This is not a neighbouring-district footnote. The line crosses ground we
control. A crew working the north end of the property is under a different
district than a crew at the lodge, and **which side of that line a fire starts
on decides who is IC for the first hour.**

Two things follow, and both are work:

1. **Put both district boundaries on the ops, medtrans and owner products**, and
   label which claims fall in which. Then brief it.
2. **The county lists no ambulance district for the three Section 10 claims.**
   Resolve that with the county before an exercise puts people on the north end
   of the property. Find out who actually responds, and write it into
   `config/site.yml`. Do not map around a gap in EMS coverage.

## We are the tenant, not the owner

Five years in, but a lease is not a deed. It changes who has authority:

- **A closure order** on National Forest land does not close this property, and
  we cannot close NF land. Two different instruments, two different signatures.
- **Dozer authority.** Putting a blade on leased ground is a conversation with
  the lessor, not a decision the exercise makes on its own.
- **Suppression repair.** The resource advisor's counterpart for anything on
  this property is the owner, and the `repair` product is what that conversation
  gets held over. Start it on day one — you cannot reconstruct where a dozer
  went three weeks later.
- **The owner's name stays off the products.** See Privacy below.

## Mine workings — treat as present until walked

"Lode claim" is not decorative. These are **patented hard rock claims** from a
19th-century mineral survey. A claim block of this vintage in the Black Hills
very often carries shafts, adits, prospect pits and tailings.

**Open shafts do not show on a DEM. They do not show on imagery under canopy.
They are not on any layer you can download.** They are a life-safety hazard for
anyone building line, and worse at night.

So:

- Treat every one of the 12 claims as suspected to hold workings until somebody
  has walked it.
- Record every working found as a `Hazard` point with a real description in
  `Comments` — "open shaft, ~4 ft square, no collar" beats "mine".
- **Never anchor control line to a mine working.**

This is the single highest-value piece of field collection on the property, and
the claim names give you a natural survey grid: walk it claim by claim and tick
them off.

## Access — one way in

Storm Mountain Rd, 1.7 miles off US-16 at Rockerville. Winding Forest Service
road, single lane with turnouts. Everything larger than a type 6 stops
somewhere on it.

Survey and record:

- Every turnout, and whether two engines can actually pass at it
- The turnaround point **by vehicle class** — where a type 3 stops, where a
  lowboy stops
- Corners a lowboy or type 1 physically cannot make
- Gates, and who holds the combination
- Cattle guards and their weight rating
- Overhead clearance: branches, powerline crossings

**Then answer the question that matters: is there a second way off this
property?** A single ingress that is also the single egress is an LCES problem
for everyone on the ground, not just the crews. If the answer is no, *that is
the finding* — it belongs in the briefing, not in a footnote.

## What to collect on the ground

Beyond the mine workings and the road:

**Structures** — lodge, dining hall, cabins, maintenance and storage buildings.
One `Structure` point each, inside a `Structure Group` polygon. Per structure:
construction type and roof material, defensible space assessed honestly,
occupancy (how many sleep there, and when), propane tanks and their setback.

**Water** — tank capacity *and fitting thread* (NH or NPSH), hydrant flow if West
Dakota Water District will give you the figure, any draft-capable pond with its
depth, approach and tender turnaround. Whether the supply is on the district main
or on a well. A water source a tender cannot reach is worse than no water source,
because it appears on the map as an option.

**Comms** — walk the property with a radio and record where you lose the
repeater. That turns straight into a repeater-siting exercise.

## Privacy

The property is private and the owner is a named third party. Parcel data is
public record, but an exercise product that maps a real owner's buildings is not
something to hand out.

- **Owner name and mailing address stay off every product.** They live in
  `config/site.yml` and the county record, which is where they belong.
- `pio`, `evac` and `closure` already exclude all Event points, so structures
  cannot leak onto them. **Do not add exceptions for this property.**
- The `owner` product may show the parcel boundary and that it is private. It
  does not need to name anyone.
- Structure detail — occupancy, defensible space, propane — is operational data
  for the incident. It is not public information.

## Refreshing the data

```bash
python3 scripts/fetch_site.py           # cached
python3 scripts/fetch_site.py --force   # refetch from the county
```

The query lives in `config/site.yml` under `parcel_service.where` and matches on
owner of record plus mineral survey. **If the property changes hands the query
returns nothing and the script says so**, rather than silently writing an empty
file. Update the query in that one place.
