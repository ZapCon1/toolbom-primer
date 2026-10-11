"""Run the reader against conformance/cases.json, the language-neutral spec.

Any implementation, in any language, should pass the same cases.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from toolbom_reader import (
    BomRow,
    brand_suggestions,
    combine,
    detect_format,
    format_shank,
    row_issues,
)
from toolbom_reader.csv_output import csv_cell
from toolbom_reader.fusion import parse_holder_description, parse_tool_description

CASES: dict[str, Any] = json.loads(
    (Path(__file__).parent.parent / "conformance" / "cases.json").read_text(encoding="utf-8")
)


def _cases(group: str) -> pytest.MarkDecorator:
    return pytest.mark.parametrize("case", CASES[group], ids=[c["name"] for c in CASES[group]])


def _row(fields: dict[str, Any]) -> BomRow:
    """A row from a case: missing text is "", missing numbers are None."""
    blank: dict[str, Any] = {name: "" for name in BomRow.__dataclass_fields__}
    blank.update(shank=None, tool_number=None, quantity=None, stickout=None)
    return BomRow(**(blank | fields))


@_cases("format_detection")
def test_format_detection(case: dict[str, Any]) -> None:
    assert detect_format(bytes.fromhex(case["first_bytes_hex"])) == case["expected"]


@_cases("tool_description")
def test_tool_description(case: dict[str, Any]) -> None:
    identity, spec = parse_tool_description(case["description"], case["vendor"])
    assert (identity.brand, identity.part_number, spec) == (
        case["brand"],
        case["part_number"],
        case["spec"],
    )


@_cases("holder_description")
def test_holder_description(case: dict[str, Any]) -> None:
    identity = parse_holder_description(case["description"])
    assert (identity.brand, identity.part_number) == (case["brand"], case["part_number"])


@_cases("shank")
def test_shank(case: dict[str, Any]) -> None:
    assert format_shank(case["stored"], case["flagged_metric"]) == case["expected"]


@_cases("row_issues")
def test_row_issues(case: dict[str, Any]) -> None:
    assert [issue.kind for issue in row_issues(_row(case["row"]))] == case["expected"]


@_cases("combine")
def test_combine(case: dict[str, Any]) -> None:
    combined = combine([_row(fields) for fields in case["rows"]]).to_dict()
    assert combined == case["expected"]


@_cases("csv_cell")
def test_csv_cell(case: dict[str, Any]) -> None:
    assert csv_cell(case["value"]) == case["expected"]


@_cases("brand_suggestions")
def test_brand_suggestions(case: dict[str, Any]) -> None:
    rows = [_row({"brand": brand}) for brand in case["brands"]]
    found = [{"spellings": list(s.spellings), "reason": s.reason} for s in brand_suggestions(rows)]
    assert found == case["expected"]


def test_every_case_group_is_run() -> None:
    tested = {name.removeprefix("test_") for name in globals() if name.startswith("test_")}
    groups = {key for key, value in CASES.items() if isinstance(value, list)}
    assert groups <= tested
