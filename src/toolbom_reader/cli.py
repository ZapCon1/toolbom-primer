"""toolbom-reader LIBRARY [--combine]: print a tool library's BOM rows as JSON."""

import argparse
import json
import sys

from toolbom_reader.combine import combine
from toolbom_reader.errors import LibraryError
from toolbom_reader.library import read_library


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="toolbom-reader",
        description="Read a Mastercam .tooldb or Fusion .tools/.json library as BOM rows (JSON).",
    )
    parser.add_argument("library", help="path to the tool library")
    parser.add_argument(
        "--combine",
        action="store_true",
        help="print purchase lists (duplicates merged) instead of one row per tool",
    )
    args = parser.parse_args(argv)
    try:
        library = read_library(args.library)
    except LibraryError as error:
        print(f"toolbom-reader: {error}", file=sys.stderr)
        return 1
    output = (
        {"source": library.source, **combine(library.rows).to_dict()}
        if args.combine
        else library.to_dict()
    )
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
