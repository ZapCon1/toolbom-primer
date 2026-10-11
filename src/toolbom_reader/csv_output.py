"""BOM rows and purchase lists as CSV, for spreadsheets and ERP imports.

Headers are the JSON keys. Text that a spreadsheet would run as a formula
("=HYPERLINK(...)", "+1", "@SUM") is prefixed with a quote: a library is
untrusted input, and CSV is the classic way to smuggle a formula into Excel.
"""

import csv
import io
import re
from collections.abc import Sequence
from dataclasses import fields

from toolbom_reader.combine import ColletLine, HolderLine, PurchaseLists, ToolLine
from toolbom_reader.rows import BomRow

# The column order a shop BOM spreadsheet uses (docs/BOM.md).
BOM_COLUMNS = (
    "brand",
    "part_number",
    "description",
    "hyperlink",
    "quantity",
    "shank",
    "tool_number",
    "holder_brand",
    "holder_part_number",
    "holder_description",
    "holder_hyperlink",
    "collet",
    "spindle_taper",
    "stickout",
)

_FORMULA_TRIGGERS = ("=", "+", "@", "\t", "\r")
_NEGATIVE_NUMBER = re.compile(r"^-\d+(\.\d+)?$")

Line = ToolLine | HolderLine | ColletLine


def rows_csv(rows: Sequence[BomRow]) -> str:
    """One line per tool assembly, in BOM column order."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(BOM_COLUMNS)
    for row in rows:
        writer.writerow([csv_cell(getattr(row, name)) for name in BOM_COLUMNS])
    return buffer.getvalue()


def purchase_lists_csv(lists: PurchaseLists) -> str:
    """The three lists in one file, each under a title line, a blank line between.

    A CSV holds one table, but titled blocks import cleanly into Excel and
    Google Sheets. tool_numbers are written as "1, 4, 12".
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    sections: list[tuple[str, type[Line], Sequence[Line]]] = [
        ("tools", ToolLine, lists.tools),
        ("holders", HolderLine, lists.holders),
        ("collets", ColletLine, lists.collets),
    ]
    for index, (title, line_type, lines) in enumerate(sections):
        if index:
            writer.writerow([])
        names = [f.name for f in fields(line_type)]
        writer.writerow([title])
        writer.writerow(names)
        for line in lines:
            writer.writerow([csv_cell(getattr(line, name)) for name in names])
    return buffer.getvalue()


def csv_cell(value: object) -> str:
    """One value as CSV cell text: blank for null, lists joined, formulas defused."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    text = str(value)
    if text.startswith(_FORMULA_TRIGGERS) or (
        text.startswith("-") and not _NEGATIVE_NUMBER.match(text)
    ):
        return "'" + text
    return text
