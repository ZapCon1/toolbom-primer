"""CSV output: column order, purchase-list sections, and formula injection."""

import csv
import io

import pytest

from toolbom_reader import BomRow, combine
from toolbom_reader.csv_output import BOM_COLUMNS, purchase_lists_csv, rows_csv

ROW = BomRow("NORTHLINE", "NL-1550", "FLAT END MILL Ø6", "6MM", 11, "APEX", "AH-ER16-563", "")


def _parse(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_no_rows_is_just_the_header() -> None:
    assert _parse(rows_csv([])) == [list(BOM_COLUMNS)]


def test_rows_come_out_in_bom_column_order() -> None:
    inch = BomRow("KESTREL", "KT-200", "DRILL", 0.25, 2, "", "", "", quantity=3, stickout=1.5)
    assert _parse(rows_csv([ROW, inch]))[1:] == [
        ["NORTHLINE", "NL-1550", "FLAT END MILL Ø6", "", "", "6MM", "11", "APEX", "AH-ER16-563", "", "", "", "", ""],
        ["KESTREL", "KT-200", "DRILL", "", "3", "0.25", "2", "", "", "", "", "", "", "1.5"],
    ]  # fmt: skip


def test_bom_columns_cover_every_row_field_once() -> None:
    assert sorted(BOM_COLUMNS) == sorted(ROW.to_dict())


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ('=HYPERLINK("http://x")', '\'=HYPERLINK("http://x")'),
        ("+1", "'+1"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("-A1", "'-A1"),
        ("-12.5", "-12.5"),  # a plain negative number is safe
        ("NL-1550", "NL-1550"),  # a dash inside is fine
    ],
)
def test_text_a_spreadsheet_would_run_as_a_formula_is_quoted(value: str, written: str) -> None:
    row = BomRow(value, "P", "", None, 1, "", "", "")
    assert _parse(rows_csv([row]))[1][0] == written


def test_purchase_lists_are_titled_sections_with_tool_numbers_joined() -> None:
    rows = [
        BomRow("NORTHLINE", "NL-1550", "EM", "6MM", 1, "APEX", "AH-1", "", collet="C-6"),
        BomRow("NORTHLINE", "NL-1550", "EM", "6MM", 4, "APEX", "AH-1", "", collet="C-6"),
    ]
    assert _parse(purchase_lists_csv(combine(rows))) == [
        ["tools"],
        ["brand", "part_number", "description", "hyperlink", "shank", "quantity", "tool_numbers"],
        ["NORTHLINE", "NL-1550", "EM", "", "6MM", "2", "1, 4"],
        [],
        ["holders"],
        [
            "brand",
            "part_number",
            "description",
            "hyperlink",
            "spindle_taper",
            "quantity",
            "tool_numbers",
        ],
        ["APEX", "AH-1", "", "", "", "2", "1, 4"],
        [],
        ["collets"],
        ["collet", "holder", "shank", "quantity", "tool_numbers"],
        ["C-6", "APEX AH-1", "6MM", "2", "1, 4"],
    ]


def test_empty_purchase_lists_keep_their_titles_and_headers() -> None:
    assert [line[0] for line in _parse(purchase_lists_csv(combine([]))) if line] == [
        "tools", "brand", "holders", "brand", "collets", "collet",
    ]  # fmt: skip
