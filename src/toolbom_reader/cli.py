"""toolbom-reader LIBRARY [--combine] [--csv | --check] [-o FILE]: print a tool library's BOM."""

import argparse
import io
import json
import sys
from pathlib import Path

from toolbom_reader.combine import combine
from toolbom_reader.csv_output import purchase_lists_csv, rows_csv
from toolbom_reader.errors import LibraryError
from toolbom_reader.issues import row_issues
from toolbom_reader.library import Library, read_library


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="toolbom-reader",
        description="Read a Mastercam .tooldb or Fusion .tools/.json library as a BOM.",
    )
    parser.add_argument("library", help="path to the tool library")
    parser.add_argument(
        "--combine",
        action="store_true",
        help="purchase lists (duplicates merged) instead of one row per tool",
    )
    parser.add_argument("--csv", action="store_true", help="CSV instead of JSON")
    parser.add_argument(
        "--check",
        action="store_true",
        help="list the rows that can't be ordered from as they stand, instead of the BOM",
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="write to this file instead of standard output"
    )
    args = parser.parse_args(argv)
    if args.check and (args.combine or args.csv):
        parser.error("--check can't be used with --combine or --csv")
    try:
        library = read_library(args.library)
    except LibraryError as error:
        print(f"toolbom-reader: {error}", file=sys.stderr)
        return 1
    text = _render(library, combined=args.combine, as_csv=args.csv, check=args.check)
    if args.output is None:
        # Brands and descriptions aren't ASCII ("Ø"); a Windows console defaults to cp1252.
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    else:
        # Excel reads a CSV as ANSI unless it starts with a byte-order mark.
        encoding = "utf-8-sig" if args.csv else "utf-8"
        args.output.write_text(text, encoding=encoding, newline="")
    return 0


def _render(library: Library, *, combined: bool, as_csv: bool, check: bool) -> str:
    if check:
        return _check_report(library)
    if as_csv:
        return purchase_lists_csv(combine(library.rows)) if combined else rows_csv(library.rows)
    output = (
        {"source": library.source, **combine(library.rows).to_dict()}
        if combined
        else library.to_dict()
    )
    return json.dumps(output, indent=2, ensure_ascii=False) + "\n"


def _check_report(library: Library) -> str:
    """One line per row that needs a person, then a count."""
    lines = []
    for row in library.rows:
        issues = row_issues(row)
        if issues:
            number = "T?" if row.tool_number is None else f"T{row.tool_number}"
            name = " ".join(p for p in (row.brand, row.part_number) if p) or row.description
            lines.append(f"{number}  {name}: {'; '.join(i.message for i in issues)}")
    lines.append(f"{len(lines)} of {len(library.rows)} rows need a person's attention.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
