# Changelog

## 0.1.0 (2026-10-11)

First public release.

- Primer docs: Mastercam `.tooldb` and Fusion `.tools`/`.json` formats, the 14-field BOM row, combining into purchase lists, and reading untrusted files safely.
- `toolbom_reader`: a dependency-free Python reader for both formats, with `combine()` and a `toolbom-reader` CLI that prints JSON.
- JSON Schemas for the row and purchase-list output, validated against real output in the tests.
