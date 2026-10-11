# Combining duplicates into purchase lists

A BOM has one row per tool assembly, so a holder used by 27 tools appears 27 times. Purchasing wants a shopping list instead. Combining turns rows into three lists:

| List | Grouped by | Quantity |
|---|---|---|
| **tools** | tool brand + part number | sum of the rows' `quantity`, **a blank counting as 1** |
| **holders** | holder brand + part number | number of assemblies using it |
| **collets** | collet part number | number of assemblies using it |

Each line also lists the T numbers where it's used (`tool_numbers`, ascending, no repeats). Lines appear in the order each part first appears in the BOM.

## The rules, and why

- **Match ignoring case and surrounding spaces.** `Northline` and `NORTHLINE ` are the same brand. Brand *spelling* mistakes (`NORTHLNIE`) are not caught here: clean brands before combining if your data has them.
- **A blank quantity counts as 1.** One tool in the library is one physical tool unless someone says otherwise.
- **Holders and collets count assemblies, not tool quantities.** A holder holds one tool at a time. Buying 4 of an end mill as spares doesn't mean buying 4 holders.
- **Collets are their own list,** keyed by collet part number alone. The same holder takes different collets for different shanks, and the same collet fits several holders.
- **Never merge a row that has no part number.** Fusion's "Milling Tool-5 Parameters" placeholders all share one description but are different tools. Merging them would quietly undercount. A tool without a part number keeps its own line, and a holder or collet without one is left out of its list. It can't be bought by part number anyway.
- **When rows for one part disagree** (a description or link filled on one row but not another), take the first non-blank value.

## Example

| T | Tool | Qty | Holder | Collet |
|---|---|---|---|---|
| 1 | NORTHLINE NL-1550 | 3 | APEX AH-ER16-100 | ER16-6 |
| 2 | NORTHLINE NL-1550 | | APEX AH-ER16-100 | ER16-6 |
| 3 | *(no part number)* | | APEX AH-ER16-100 | ER16-4 |
| 4 | *(no part number)* | | *(no part number)* | |

combines to:

- **tools:** NORTHLINE NL-1550 × 4 (T1, 2); *(blank)* × 1 (T3); *(blank)* × 1 (T4)
- **holders:** APEX AH-ER16-100 × 3 (T1, 2, 3)
- **collets:** ER16-6 × 2 (T1, 2); ER16-4 × 1 (T3)

Reference: [`src/toolbom_reader/combine.py`](../src/toolbom_reader/combine.py). Schema: [`schema/purchase-lists.schema.json`](../schema/purchase-lists.schema.json).
