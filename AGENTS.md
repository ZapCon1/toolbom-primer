# For AI coding assistants

You're helping someone build tool-library-to-BOM conversion into their own system. This repo is the reference: the docs in `docs/` are the spec, and `src/toolbom_reader/` is a working implementation. Read the doc for the format you're working on before you write code. The rules below are the ones that get broken most often.

## Rules that must hold

1. **Detect format by the first bytes**, never the file extension: `SQLite format 3\0` → Mastercam; `PK\3\4` → Fusion zip; `{` (after an optional UTF-8 BOM) → Fusion JSON.
2. **Mastercam part number = `TlToolMill.MfgToolCode`** (joined on the tool item's ID), falling back to `TlAssemblyItem.CatalogID` only when it's blank.
3. **Don't trust Mastercam's `IsMetric`.** Shanks are stored in inches. A value within 0.001 mm of a 0.5 mm step after × 25.4 is metric, output as `"6MM"`. Inch shanks stay numbers.
4. **Fusion brand/part come from the description** (`<ID> - <BRAND>_<PART> (<spec>)`). No parentheses → blank brand and part. **Never guess an identity**; a blank is fixable, a wrong part number gets ordered.
5. **Never merge rows without a part number** when combining. Blank quantity counts as 1 for tools; holders and collets count assemblies.
6. **A CAM system name in a brand field (Mastercam, Fusion, Autodesk…) is a placeholder,** not a manufacturer. Flag it for a person.
7. **Every library file is untrusted input.** Apply every defense in `docs/SAFETY.md`: read-only SQLite with `trusted_schema=OFF`, no generated/virtual columns, unique IDs, a time limit, zip size checked before inflating, and bracket/comma counts before JSON parsing.
8. **Output matches `schema/bom.schema.json`** (or `purchase-lists.schema.json` for the combined form). Validate against it in tests.

## Testing

Build synthetic libraries in tests (see `tests/tooldb_factory.py` and `tests/fusion_factory.py`). Never commit a real customer library: it can hold proprietary tooling data. Cover 0, 1, 2 and many tools, and one malicious file per defense.
