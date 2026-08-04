# 8 — Naming conventions

Decoded from the reference products so exercise exports sort and read the same
way. Encoded in `config/map_products.yml` under `naming` and applied by
`scripts/arcpy/export_products.py`.

## Pattern

```
{product}_{page_size}_{orientation}_{prepared_yyyymmdd}_{prepared_hhmm}_{IncidentName}_{UnitID}_{op_mmdd}{shift}.pdf
```

Example:

```
iap_8.5x11_port_20260728_0430_StormMountain_SDBKFEX0001_0728day.pdf
```

## Fields

| Part | Meaning | Example |
|---|---|---|
| `product` | Product key from `config/map_products.yml` | `iap`, `ops`, `airops`, `pilot`, `briefing`, `pio`, `facilities`, `transportation`, `progression` |
| `page_size` | Sheet size | `8.5x11`, `11x17`, `arch_c`, `arch_d`, `arch_e` |
| `orientation` | `port` or `land` | `port` |
| `prepared_yyyymmdd` | Date the PDF was **made** | `20260728` |
| `prepared_hhmm` | Time the PDF was **made**, 24h | `0430` |
| `IncidentName` | CamelCase, no spaces | `StormMountain` |
| `UnitID` | Unit ID with hyphens removed | `SDBKFEX0001` |
| `op_mmdd` | Operational period the product is **for** | `0728` |
| `shift` | `day` or `night` | `day` |

## The two dates

The single most common mistake. Every product carries two:

- **Prepared** — when you made it. `20260728_0430`.
- **Operational period** — what shift it is for. `0728day`.

They are different, usually by a day: the sheet for tomorrow's day shift gets
made this evening. On the reference products the gap is visible — a file
prepared `20260725_2104` for op period `0726day`.

Get these backwards and someone briefs off yesterday's map.

## Other conventions

**Incident folder:** `2026_StormMountain` — year first so incidents sort
chronologically. Created by `scripts/make_folder_structure.py`.

**Event GDB backups:** `event_YYYYMMDD_HHMM.gdb` in `incident_data/backup/`.
Back up before every edit session, not after.

**Do not overwrite yesterday.** Every operational period's products go to
`products/archive/`. The progression map is built from them, and "what did the
map say on the 27th" is a question that gets asked after the fact.

**Product keys are lowercase, no spaces.** They have to match layout names in the
`.aprx` — `export_products.py` looks the layout up by product key, case
insensitively, and skips with a warning if there is no match.
