# Fusion tool libraries (`.tools` and `.json`)

Fusion exports a tool library in one of two forms:

- **`.tools`**: a zip archive (first bytes `PK\3\4`) holding a single entry, `tools.json`.
- **`.json`**: the same document, unzipped. Windows editors sometimes add a UTF-8 byte-order mark (`EF BB BF`) when they save it, so skip one if it's there.

## The document

```json
{
  "version": 37,
  "data": [
    {
      "type": "flat end mill",
      "description": "LIB0201_1010 - NORTHLINE_NL-1550 (EM_D6.0_L25.34_R0.0_A)",
      "vendor": "NORTHLINE",
      "product-id": "",
      "product-link": "",
      "unit": "millimeters",
      "geometry": { "DC": 6, "SFDM": 6, "OAL": 57 },
      "post-process": { "number": 11 },
      "holder": {
        "description": "APEX_AH-ER16-563",
        "vendor": "",
        "product-id": "",
        "product-link": ""
      }
    }
  ]
}
```

`data` holds **one entry per tool, each with its holder embedded**. The list can also contain standalone `"type": "holder"` and `"type": "probe"` entries. Those aren't tools, so skip them. Expect any field to be missing or the wrong type, and treat that as blank.

## Field mapping

| BOM field | Source | Notes |
|---|---|---|
| `brand` | parsed from `description` | See below. `vendor` helps but doesn't decide. |
| `part_number` | `product-id`, else parsed from `description` | `product-id` is almost always empty. |
| `description` | the size spec from `description`, prefixed with the upper-cased `type` | `FLAT END MILL - EM_D6.0_L25.34_R0.0_A`. If the description didn't parse, keep it as written. |
| `shank` | `geometry.SFDM` in the tool's `unit` | `unit` starting `millimet` means the value is millimetres. Otherwise apply the same inch-fraction and half-millimetre checks as [Mastercam](MASTERCAM.md#the-metric-shank-trap). |
| `tool_number` | `post-process.number` | Must be an integer (watch out: JSON `true` is not 1). |
| `holder_brand` | `holder.vendor`, else parsed from `holder.description` | |
| `holder_part_number` | `holder.product-id`, else parsed from `holder.description` | |
| `holder_description` | blank | Fusion's holder description *is* the identity. |
| `hyperlink` | `product-link` | Vendor and MachiningCloud libraries often fill it. |
| `holder_hyperlink` | `holder.product-link` | |

## Parsing identity out of the description

Fusion's own part-number fields are empty in most real libraries. Shops encode identity in the description instead:

```
LIB0202_1001 - KESTREL_KT-FM5200-A (FM_D50.8_L45.0 _R.787)
└─ tool ID ─┘   └brand┘ └─ part ──┘  └──── size spec ────┘
```

The rules, in order:

1. Strip a leading `<tool ID> - ` (a run of non-spaces, then ` - `).
2. Split off the trailing `(…)`: what's inside is the size spec, and what's before it is the identity. **No parentheses means no identity**: brand and part are blank, and the description is kept as written.
3. If the identity starts with the `vendor` value followed by `_` or a space, that's the brand. This handles `Blue Ridge 32257`, where the brand itself contains a space.
4. Otherwise split on the **first** `_`: `BRAND_PART`. Part numbers keep any further underscores, dashes and dots.
5. No `_` at all: the whole identity is the part number and the brand is blank.

Holder descriptions are simpler: `APEX_AH-ER16-100` gives brand `APEX` and part `AH-ER16-100`, split on the first `_`. With no `_`, the whole thing is the part number.

| Description | Brand | Part | Why |
|---|---|---|---|
| `T1 - TAPWORKS_1942.002 (EM_D2.0)` | TAPWORKS | 1942.002 | the usual pattern |
| `T1 - Blue Ridge 32257 (drill)` + vendor `Blue Ridge` | Blue Ridge | 32257 | vendor anchors a brand with a space |
| `T1 - MICROLINE_70078 (BM)` + vendor `Northline` | MICROLINE | 70078 | the description beats a wrong vendor |
| `T1 - P-75442 (BM_D4.0)` | *(blank)* | P-75442 | no brand given |
| `T1 - Milling Tool-5 Parameters` | *(blank)* | *(blank)* | Fusion's placeholder. Never guess. |
| `T1 - TM_D1.1_L8.0` | *(blank)* | *(blank)* | a bare size spec. `TM` is a tool type, not a brand. |

The last two rows are why the parentheses are required. Without that rule, `TM_D1.1_L8.0` would come out as brand `TM`.

Reference: [`src/toolbom_reader/fusion.py`](../src/toolbom_reader/fusion.py).

## Before you trust the file

A `.tools` file is a zip, and a zip can be a bomb. Check the declared size of `tools.json` before inflating it, and count brackets and commas in the raw bytes before parsing the JSON. [SAFETY.md](SAFETY.md) has the numbers.
