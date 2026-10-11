"""The BOM row: one tool assembly (a cutting tool in its holder).

Both readers produce these. Eight fields come from the library; the other six
have no source in either format and are left blank for the person building
the BOM to fill in (Fusion libraries sometimes carry product links, which fill
the two hyperlink fields).
"""

import math
import re
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

MM_PER_INCH = 25.4

# Size limits for text read from an untrusted file.
MAX_TOOLS = 5_000
MAX_TEXT_LENGTH = 300
MAX_LINK_LENGTH = 2_048
MAX_TOOL_NUMBER = 1_000_000
_MAX_SHANK_TEXT = 40

# A metric shank stored in inches lands within this distance (mm) of a
# half-millimetre step. No common inch size does: 1/4" = 6.35 mm,
# 1/8" = 3.175 mm, 1/2" = 12.7 mm.
_METRIC_GRID_MM = 0.5
_METRIC_TOLERANCE_MM = 0.001
# Multiples of 2.5" land on that grid too (2.5" = 63.5 mm), so a value on a
# 1/64" step is taken as inches first. No metric size lands on both grids.
_INCH_FRACTION = 1 / 64
_INCH_TOLERANCE = 1e-6
# Far above any real shank in inches or millimetres; bigger values are corrupt.
_MAX_SHANK = 10_000.0

# Control characters other than tab, newline and carriage return: spreadsheets
# can't store them and they never mean anything in a part number.
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

Shank = float | str
"""Inch shanks are numbers (0.5); metric shanks are text in millimetres ("6MM")."""


@dataclass(frozen=True)
class BomRow:
    # From the tool library.
    brand: str
    part_number: str
    description: str
    shank: Shank | None
    tool_number: int | None
    holder_brand: str
    holder_part_number: str
    holder_description: str
    # Not in either library format (except Fusion product links): fill in yourself.
    hyperlink: str = ""
    quantity: int | None = None
    holder_hyperlink: str = ""
    collet: str = ""
    spindle_taper: str = ""
    stickout: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LIBRARY_FIELDS = (
    "brand",
    "part_number",
    "description",
    "shank",
    "tool_number",
    "holder_brand",
    "holder_part_number",
    "holder_description",
)
USER_FIELDS = (
    "hyperlink",
    "quantity",
    "holder_hyperlink",
    "collet",
    "spindle_taper",
    "stickout",
)


def format_shank(stored: float | None, flagged_metric: bool) -> Shank | None:
    """A shank diameter as a BOM shows it.

    Metric sizes become text in millimetres ("6MM", "2.5MM"); inch sizes stay
    numbers, rounded to 4 places. Mastercam stores inches even for metric tools
    and rarely sets its metric flag, so metric is detected from the value. When
    the flag *is* set, the value is taken to be millimetres already.
    """
    if stored is None or not math.isfinite(stored) or not 0 < stored <= _MAX_SHANK:
        return None
    if flagged_metric:
        return _millimetres(stored)
    fraction = round(stored / _INCH_FRACTION) * _INCH_FRACTION
    if abs(stored - fraction) < _INCH_TOLERANCE:
        return round(stored, 4)
    mm = stored * MM_PER_INCH
    on_grid = round(mm / _METRIC_GRID_MM) * _METRIC_GRID_MM
    if abs(mm - on_grid) < _METRIC_TOLERANCE_MM:
        return _millimetres(on_grid)
    return round(stored, 4)


def clean_text(value: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Drop control characters and cap the length."""
    return _CONTROL_CHARACTERS.sub("", value)[:max_length]


_TEXT_FIELDS = tuple(f.name for f in fields(BomRow) if f.type in (str, "str"))
_LINK_FIELDS = frozenset({"hyperlink", "holder_hyperlink"})


def clean_row(row: BomRow) -> BomRow:
    """Make a row read from an untrusted file safe to store, show or export."""
    changes: dict[str, Any] = {
        name: clean_text(
            getattr(row, name), MAX_LINK_LENGTH if name in _LINK_FIELDS else MAX_TEXT_LENGTH
        )
        for name in _TEXT_FIELDS
    }
    if row.tool_number is not None and not 0 <= row.tool_number <= MAX_TOOL_NUMBER:
        changes["tool_number"] = None
    if isinstance(row.shank, str):
        changes["shank"] = clean_text(row.shank, _MAX_SHANK_TEXT)
    return replace(row, **changes)


def _millimetres(mm: float) -> str:
    return f"{round(mm, 3):g}MM"
