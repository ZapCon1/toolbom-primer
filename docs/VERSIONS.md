# Format versions

What the reader has been checked against, and what hasn't been checked. If your library is a version not listed here, a report helps, whether it works or not. Open an issue saying which CAM version wrote it and what happened, **without attaching the library**.

## Mastercam

| | |
|---|---|
| Format | `.tooldb`, a SQLite database |
| Checked against | One real milling library, plus the synthetic libraries in this repo. The `.tooldb` itself carries no version number (`PRAGMA user_version` is 0 and there's no version table), so the exact Mastercam release isn't known. |
| Tables read | `TlAssembly`, `TlAssemblyItem`, `TlManufacturer`, `TlToolMill` |
| Not read | Turning tools: see [MASTERCAM.md](MASTERCAM.md#turning-tools). The rest of the ~80 tables (operations, materials, feeds and speeds). |
| Not supported | Libraries from Mastercam releases before `.tooldb`, which used a different file format |

If a future Mastercam release renames or moves the four tables above, the reader reports "missing tables" rather than producing a wrong BOM.

## Fusion

| | |
|---|---|
| Format | `.tools` (zip holding `tools.json`) or a plain `.json` export |
| Checked against | One real library with document `"version": 37`, plus the synthetic libraries in this repo |
| Fields read | `type`, `description`, `vendor`, `product-id`, `product-link`, `unit`, `geometry.SFDM`, `post-process.number`, and the embedded `holder`'s `description`, `vendor`, `product-id`, `product-link` |

The reader doesn't check `version`. Every field is read defensively, so if a later version moves one, it comes out blank instead of failing or coming out wrong.

## Telling which you have

- **Mastercam:** a `.tooldb` starts with the bytes `SQLite format 3`. Open it in any SQLite browser and look for the four tables above.
- **Fusion:** a `.tools` file opens as a zip. Inside, `tools.json` is one JSON object with a `data` list and a `version` number.
