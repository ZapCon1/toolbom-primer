# The BOM row

One row per **tool assembly**: a numbered cutting tool in its holder. A job's BOM is the list of these rows.

| # | Field | Type | From the library? | Meaning |
|---|---|---|---|---|
| 1 | `brand` | text | yes | Tool manufacturer |
| 2 | `part_number` | text | yes | Tool vendor part number. Blank when it can't be found, never guessed. |
| 3 | `description` | text | yes | What the tool is |
| 4 | `hyperlink` | text | Fusion only, sometimes | Tool product page |
| 5 | `quantity` | integer or null | **no** | How many to buy. Blank counts as 1 when combining. |
| 6 | `shank` | number, `"<n>MM"`, or null | yes | Shank diameter. Inch sizes are numbers (`0.25`); metric sizes are text (`"6MM"`). |
| 7 | `tool_number` | integer or null | yes | T number |
| 8 | `holder_brand` | text | yes | Holder manufacturer |
| 9 | `holder_part_number` | text | yes | Holder part number |
| 10 | `holder_description` | text | Mastercam only | Holder description |
| 11 | `holder_hyperlink` | text | Fusion only, sometimes | Holder product page |
| 12 | `collet` | text | **no** | Sleeve or collet part number |
| 13 | `spindle_taper` | text | **no** | CAT40, HSK63A, BT30… |
| 14 | `stickout` | number or null | **no** | How far the tool sticks out of the holder |

The numbering is the column order a shop BOM spreadsheet typically uses. The JSON keys are what the reader outputs.

## The fields no library has

Neither format reliably stores quantity, collet, spindle taper or stickout. Hyperlinks only exist in Fusion libraries built from vendor catalogs. **Plan for a person to fill these in.** Ask for them in your UI, or join them from your own item master by brand + part number.

That join is also the best way to make the BOM better over time: once someone has entered the collet for holder `APEX AH-ER16-100` with a 6 mm shank, every later BOM with that combination can fill it in automatically.

## Values that need a person's attention

A row can't be ordered from as it stands when any of these is true:

- the brand is blank;
- the part number is blank;
- the holder brand or holder part number is blank;
- **the brand is a CAM system, not a manufacturer.** Libraries fill the brand field with `Mastercam`, `Fusion` or `Autodesk` when nobody entered the real maker. Treat those as blank.

Flag these rows; don't drop them. The tool is still in the program. Match CAM names after lower-casing and dropping everything but letters and digits, so `Fusion 360` and `FUSION-360` are caught alike, and match whole names only: `Fusionware` could be a real brand, not a placeholder.

Reference: [`src/toolbom_reader/issues.py`](../src/toolbom_reader/issues.py) (`row_issues`, `is_cam_brand`), or `toolbom-reader LIBRARY --check`.

## CSV

`toolbom-reader LIBRARY --csv` writes the rows in the column order above, with the JSON keys as headers. `--combine --csv` writes the three purchase lists as titled blocks in one file. Two things matter if you write your own:

- **Quote anything a spreadsheet would run as a formula.** A cell starting with `=`, `+`, `@`, a tab, or a `-` that isn't a plain number is prefixed with `'`. Library text is untrusted, and a description of `=HYPERLINK(...)` would otherwise run when someone opens the file.
- **Start the file with a UTF-8 byte-order mark** if people will open it in Excel. Without it, Excel reads the file as ANSI and mangles `Ø` in a description. (`-o FILE` does this; standard output doesn't.)

## Limits

The reader caps input at 5,000 tools per library. Text fields are capped at 300 characters and links at 2,048. Control characters are removed. Tool numbers outside 0–1,000,000 are dropped. These caps keep a hostile or corrupt file from breaking whatever consumes the output (spreadsheets reject control characters, for example).

## JSON Schema

- [`schema/bom.schema.json`](../schema/bom.schema.json): `{ "source": "mastercam" | "fusion", "rows": [ BomRow, … ] }`
- [`schema/purchase-lists.schema.json`](../schema/purchase-lists.schema.json): the combined form; see [COMBINE.md](COMBINE.md).

Both use JSON Schema 2020-12. The test suite validates the reader's real output against them, so they stay in step.
