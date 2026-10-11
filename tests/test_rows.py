import math

import pytest

from toolbom_reader import BomRow, format_shank
from toolbom_reader.rows import LIBRARY_FIELDS, USER_FIELDS, clean_row, clean_text


@pytest.mark.parametrize(
    ("stored_inches", "expected"),
    [
        (0.23622047244094202, "6MM"),  # how Mastercam stores a 6 mm shank
        (0.314960629921256, "8MM"),
        (0.0984251968503925, "2.5MM"),  # half-millimetre sizes are metric too
        (0.393700787401575, "10MM"),
    ],
)
def test_metric_shank_stored_in_inches_comes_out_in_millimetres(
    stored_inches: float, expected: str
) -> None:
    assert format_shank(stored_inches, flagged_metric=False) == expected


@pytest.mark.parametrize(
    ("stored_inches", "expected"),
    [
        (0.25, 0.25),  # 6.35 mm: just off the metric grid
        (0.125, 0.125),  # 3.175 mm
        (1.25, 1.25),  # 31.75 mm: a quarter-mm step, not a half-mm one
        (0.16799163818359375, 0.168),  # float noise rounds to 4 places
    ],
)
def test_inch_shank_stays_a_number(stored_inches: float, expected: float) -> None:
    assert format_shank(stored_inches, flagged_metric=False) == expected


def test_a_value_flagged_metric_is_taken_as_millimetres() -> None:
    assert format_shank(6.0, flagged_metric=True) == "6MM"
    assert format_shank(3.05, flagged_metric=True) == "3.05MM"


@pytest.mark.parametrize("stored", [None, 0.0, -1.0, math.inf, math.nan, 10_001.0])
def test_missing_or_impossible_shank_is_blank(stored: float | None) -> None:
    assert format_shank(stored, flagged_metric=False) is None


def test_control_characters_are_dropped_and_tabs_kept() -> None:
    assert clean_text("A\x00B\x1fC\tD") == "ABC\tD"


def test_clean_row_caps_text_and_drops_out_of_range_tool_numbers() -> None:
    row = BomRow("B" * 400, "P", "D", "6MM", 2_000_000, "", "", "", hyperlink="h" * 3_000)
    cleaned = clean_row(row)
    assert len(cleaned.brand) == 300
    assert len(cleaned.hyperlink) == 2_048
    assert cleaned.tool_number is None
    assert cleaned.shank == "6MM"


def test_library_and_user_fields_cover_every_row_field_once() -> None:
    every = list(BomRow("", "", "", None, None, "", "", "").to_dict())
    assert sorted(LIBRARY_FIELDS + USER_FIELDS) == sorted(every)
    assert len(every) == 14
