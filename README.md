# ToolBOM Primer

**How to turn a CAM tool library into a bill of materials: the file formats, the rules, and a small reader you can drop into your own system.**

Every shop that programs in Mastercam or Fusion already has its tooling written down: the tool library. What it doesn't have is a purchase list. That means brand, part number, holder and quantity for every tool in a job, in a form purchasing or an ERP can use. This primer documents how to get from one to the other:

- **[docs/MASTERCAM.md](docs/MASTERCAM.md)**: the `.tooldb` format (a SQLite database), which tables and columns hold what, and the traps (the part number isn't where you'd look, and the metric flag lies).
- **[docs/FUSION.md](docs/FUSION.md)**: the `.tools` / `.json` format, and why brand and part number have to be parsed out of the description.
- **[docs/BOM.md](docs/BOM.md)**: the 14-column BOM row, which fields the library supplies and which it can't, and the JSON schema.
- **[docs/COMBINE.md](docs/COMBINE.md)**: turning one-row-per-tool into tool, holder and collet purchase lists without merging things that aren't the same part.
- **[docs/SAFETY.md](docs/SAFETY.md)**: reading library files someone else sent you (or uploaded to your server) without getting hurt.
- **[`toolbom_reader`](src/toolbom_reader)**: a reference implementation in Python. It has no dependencies, is fully typed and tested, and is MIT licensed.
- **[schema/](schema)**: JSON Schemas for the output, so a system in any language can consume it.

> **Want the finished app instead?** [ToolBOM](https://toolbom.zappettiniconsulting.com) reads either library format in the browser and lets you fill in links, quantities, collets and stickout. It remembers parts you've seen before, cleans up brand spellings, and exports a formatted Excel BOM. It's free to use.

## Quick start

```bash
pip install git+https://github.com/ZapCon1/toolbom-primer@v0.2.0
toolbom-reader examples/mastercam-example.tooldb         # one row per tool, as JSON
toolbom-reader examples/fusion-example.tools --combine   # tool / holder / collet purchase lists
toolbom-reader MyLibrary.tooldb --csv -o bom.csv         # CSV, ready for Excel or an ERP import
toolbom-reader MyLibrary.tools --check                   # rows a person must fix before ordering
```

No library of your own yet? [`examples/`](examples) has a small synthetic Mastercam and Fusion library, each with the exact JSON, CSV and `--check` output the reader produces from it. If you're writing your own reader, those outputs are your test expectations.

```python
from toolbom_reader import combine, read_library, row_issues

library = read_library("MyLibrary.tooldb")  # format detected from content, not extension
print(library.source)  # "mastercam" or "fusion"
for row in library.rows:
    print(row.tool_number, row.brand, row.part_number, row.shank)

lists = combine(library.rows)
for line in lists.holders:
    print(line.quantity, line.brand, line.part_number, "used at T", line.tool_numbers)

for row in library.rows:
    for issue in row_issues(row):  # blank brand/part/holder, or "Mastercam" as a brand
        print(row.tool_number, issue.message)
```

Output of `toolbom-reader` (abridged):

```json
{
  "source": "fusion",
  "rows": [
    {
      "brand": "NORTHLINE",
      "part_number": "NL-1550",
      "description": "FLAT END MILL - EM_D6.0_L25.34_R0.0_A",
      "shank": "6MM",
      "tool_number": 11,
      "holder_brand": "APEX",
      "holder_part_number": "AH-ER16-563",
      "holder_description": "",
      "hyperlink": "",
      "quantity": null,
      "holder_hyperlink": "",
      "collet": "",
      "spindle_taper": "",
      "stickout": null
    }
  ]
}
```

## Building it into your own system

You don't have to use the Python package. The docs are written so you can implement the reader in whatever your ERP, MES or tool crib software is built on. In order of importance, the rules that matter:

1. **Detect the format from the file's first bytes, not its extension.** `SQLite format 3\0` is Mastercam. `PK\3\4` is a Fusion `.tools` zip. `{` (after an optional UTF-8 byte-order mark) is a Fusion JSON export.
2. **Mastercam's part number is `TlToolMill.MfgToolCode`** (the "Manufacturer's Code" field in the UI), not `CatalogID`, which is usually empty.
3. **Mastercam's metric flag is unreliable.** Shanks are stored in inches even for metric tools. A value that lands on a 0.5 mm step is metric (0.23622 in is 6 mm), unless it's also a 1/64" size such as 2.5".
4. **Fusion's part-number fields are usually empty.** Brand and part number live in the description, as `<tool ID> - <BRAND>_<PART> (<size spec>)`. If it doesn't match, leave them blank. Never guess.
5. **Never merge rows that have no part number.** Fusion's "Milling Tool-5 Parameters" placeholders are different tools that share a description.
6. **A CAM system's name in a brand field is a placeholder.** Libraries fill in `Mastercam` or `Fusion` when nobody entered the real maker. Flag those rows for a person; don't order from them.
7. **Treat every library file as untrusted input.** A crafted `.tooldb` can run computations from its schema, and a crafted `.tools` can expand to gigabytes. See [docs/SAFETY.md](docs/SAFETY.md).

If you're building with an AI coding assistant, point it at [AGENTS.md](AGENTS.md) first. It summarizes the rules above as constraints the assistant should follow.

## What's in scope

| Covered | Not covered (bring your own) |
|---|---|
| Mastercam `.tooldb` libraries (SQLite) | Mastercam libraries in older, pre-`.tooldb` formats |
| Fusion `.tools` and Fusion JSON exports | Other CAM systems (contributions welcome) |
| Tool, holder and shank identity; T numbers | Hyperlinks, quantity, collet, spindle taper, stickout (no library format stores them reliably) |
| Combining duplicates into purchase lists | Spreadsheet formatting, pricing, ordering |
| JSON and CSV output; flagging rows a person must fix | |

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"     # Windows: .venv\Scripts\pip
pytest                                # tests use synthetic libraries built in tests/
mypy && ruff check . && ruff format --check .
```

The tests never need a real tool library. `tests/tooldb_factory.py` and `tests/fusion_factory.py` build minimal synthetic ones. Please don't commit real libraries: they can hold a shop's proprietary tooling data. See [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md) to report a way past one of the defenses.

After a deliberate change to the reader's output, rebuild the examples with `python examples/build_examples.py` and review the diff.

## License

MIT. See [LICENSE](LICENSE). Mastercam is a trademark of CNC Software, LLC. Fusion is a trademark of Autodesk, Inc. This project is not affiliated with either company.
