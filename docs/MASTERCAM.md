# Mastercam tool libraries (`.tooldb`)

A Mastercam `.tooldb` is a **SQLite 3 database**. Its first 16 bytes are `SQLite format 3\0`. A real library has around 80 tables. You need four of them.

## The tables that matter

```
TlAssembly ──MainTool───▶ TlAssemblyItem ──TlManufacturerID──▶ TlManufacturer
     │                         ▲   (the cutting tool)
     │                         │ same ID
     │                    TlToolMill   (milling-tool details: part number, shank)
     │
     └──MainHolder──▶ TlAssemblyItem ──TlManufacturerID──▶ TlManufacturer
                         (the holder)
```

| Table | One row per | Columns used |
|---|---|---|
| `TlAssembly` | numbered tool assembly: a tool in its holder. **This is one BOM row.** | `ToolNumber`, `Name`, `MainTool`, `MainHolder` |
| `TlAssemblyItem` | component: a cutting tool or a holder | `ID`, `CatalogID`, `TlManufacturerID`, `Name`, `Description`, `IsMetric` |
| `TlManufacturer` | manufacturer | `ID`, `Name` |
| `TlToolMill` | milling tool, keyed by the **same ID** as its `TlAssemblyItem` | `MfgToolCode`, `ArborDiameter` |

The whole read is one query:

```sql
SELECT
    a.ToolNumber, a.Name,
    ti.ID AS tool_id, tm.Name AS tool_brand, ti.CatalogID AS tool_catalog_id,
    ti.Name AS tool_name, ti.IsMetric AS tool_is_metric,
    hi.ID AS holder_id, hm.Name AS holder_brand, hi.CatalogID AS holder_part,
    hi.Description AS holder_description,
    mill.MfgToolCode AS part_number, mill.ArborDiameter AS shank
FROM TlAssembly a
LEFT JOIN TlAssemblyItem ti  ON ti.ID = a.MainTool
LEFT JOIN TlManufacturer tm  ON tm.ID = ti.TlManufacturerID
LEFT JOIN TlAssemblyItem hi  ON hi.ID = a.MainHolder
LEFT JOIN TlManufacturer hm  ON hm.ID = hi.TlManufacturerID
LEFT JOIN TlToolMill mill    ON mill.ID = a.MainTool
ORDER BY a.ToolNumber IS NULL, a.ToolNumber, a.Name
```

Use `LEFT JOIN` throughout. An assembly can have no holder, and a probe or placeholder can have no tool.

## Field mapping

| BOM field | Source | Notes |
|---|---|---|
| `brand` | `TlManufacturer.Name` via the tool item | |
| `part_number` | **`TlToolMill.MfgToolCode`** | The "Manufacturer's Code" in Mastercam's Tool Manager. Fall back to the tool item's `CatalogID` only when it's blank. `CatalogID` is usually empty. |
| `description` | tool item `Name` | Strip the internal prefix: `CID0001 - .5" X 1.0 EM` → `.5" X 1.0 EM`. With no tool item, use the assembly `Name`. |
| `shank` | `TlToolMill.ArborDiameter` | See below. **Not** `IsMetric`. |
| `tool_number` | `TlAssembly.ToolNumber` | May be NULL. Sort those last. |
| `holder_brand` | `TlManufacturer.Name` via the holder item | |
| `holder_part_number` | holder item `CatalogID` | |
| `holder_description` | holder item `Description` | e.g. `HYDRO 12` |

Every text column can hold NULL or a non-string. Treat anything that isn't a string as blank, and trim whitespace.

## The metric shank trap

`ArborDiameter` is stored **in inches, even for metric tools**, and the item's `IsMetric` flag is usually off for those tools. A 6 mm shank comes back as `0.23622047244094202`.

The fix is to look at the value itself. First, a value on a 1/64" step is an inch size. Otherwise convert to millimetres: if the result lands within 0.001 mm of a half-millimetre step, the tool is metric:

| Stored | × 25.4 | On a 0.5 mm step? | BOM shows |
|---|---|---|---|
| 0.23622047 | 6.0000 | yes | `6MM` |
| 0.0984252 | 2.5000 | yes | `2.5MM` |
| 0.25 | 6.35 | no | `0.25` |
| 0.125 | 3.175 | no | `0.125` |
| 1.25 | 31.75 | no (a quarter step) | `1.25` |
| 2.5 | 63.5 | yes, but 2.5" is a 1/64" step | `2.5` |

The inch check has to come first: multiples of 2.5" (63.5 mm, 127 mm) sit on the metric grid, and a 2.5" face-mill arbor is real. No metric size lands on a 1/64" step except those multiples, so the two checks never disagree on a real tool. When `IsMetric` *is* set, treat the value as millimetres already. Blank out values that are zero, negative, non-finite or absurdly large; they come from corrupt data.

Metric shanks come out as text (`"6MM"`) and inch shanks as numbers (`0.25`). That's deliberate: a purchasing team reads `6MM` correctly, and an inch number stays sortable.

Reference: [`src/toolbom_reader/mastercam.py`](../src/toolbom_reader/mastercam.py) and [`rows.py`](../src/toolbom_reader/rows.py) (`format_shank`).

## Before you trust the file

A `.tooldb` is a database, and a database can carry code. Before running the query:

- open it **read-only** (`?mode=ro`);
- set `PRAGMA trusted_schema=OFF`;
- confirm the four tables are plain tables: not views, not virtual tables, and no generated columns;
- confirm `ID` is unique in the joined tables, or the joins multiply;
- set a time limit and a value-length limit.

[SAFETY.md](SAFETY.md) explains why each one matters.
