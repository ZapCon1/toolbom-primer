# Changelog

## 0.2.0 (2026-10-11)

- **Fix:** shanks of 2.5" and 5" were shown as `63.5MM` and `127MM`. A value on a 1/64" step is now taken as inches before the metric check.
- `row_issues()` and `toolbom-reader --check`: flag rows with no brand, no part number, no holder, or a CAM system (Mastercam, Fusion…) as the brand. The docs described this rule; the reader now implements it.
- CSV output: `--csv` for rows, `--combine --csv` for purchase lists, with formula-like text quoted. `-o FILE` writes to a file (CSV with a byte-order mark for Excel).
- `examples/`: a synthetic Mastercam and Fusion library with their exact output, checked by the tests.
- Standard output is always UTF-8, so non-ASCII descriptions print on a Windows console.

## 0.1.0 (2026-10-11)

First public release.

- Primer docs: Mastercam `.tooldb` and Fusion `.tools`/`.json` formats, the 14-field BOM row, combining into purchase lists, and reading untrusted files safely.
- `toolbom_reader`: a dependency-free Python reader for both formats, with `combine()` and a `toolbom-reader` CLI that prints JSON.
- JSON Schemas for the row and purchase-list output, validated against real output in the tests.
