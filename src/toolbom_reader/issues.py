"""Rows a person has to look at before anyone orders from the BOM.

A row can't be ordered from as it stands when the tool brand or part number is
blank, the holder brand or part number is blank, or a brand field holds a CAM
system's name (libraries fill in "Mastercam" or "Fusion" when nobody entered
the real maker). Flag these rows; don't drop them: the tool is still in the
program. See docs/BOM.md.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from toolbom_reader.rows import BomRow

IssueKind = Literal["no-brand", "no-part-number", "no-holder", "cam-brand"]

# CAM systems and their makers as they show up in brand fields, folded by
# _fold. None of them is a brand you can buy a cutter or holder from.
CAM_NAMES = frozenset(
    {
        "mastercam",
        "cncsoftware",
        "fusion",
        "fusion360",
        "autodesk",
        "autodeskfusion",
        "autodeskfusion360",
        "hsm",
        "hsmworks",
        "inventorcam",
        "featurecam",
        "powermill",
        "delcam",
        "solidcam",
        "esprit",
        "gibbscam",
        "hypermill",
        "openmind",
        "nx",
        "nxcam",
        "siemensnx",
        "camworks",
        "bobcad",
        "bobcadcam",
        "edgecam",
        "cimatron",
        "worknc",
        "topsolid",
        "sprutcam",
        "tebis",
        "visualcam",
        "rhinocam",
        "mecsoft",
    }
)

_NOT_ALPHANUMERIC = re.compile(r"[^a-z0-9]")


@dataclass(frozen=True)
class RowIssue:
    kind: IssueKind
    fields: tuple[str, ...]  # the BomRow fields to fix
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_cam_brand(name: str) -> bool:
    """True for a CAM system's name, however it's spelled ("Fusion 360", "FUSION-360")."""
    return _fold(name) in CAM_NAMES


def row_issues(row: BomRow) -> list[RowIssue]:
    """Why the row can't be ordered from as it stands; empty when it can."""
    issues: list[RowIssue] = []
    brand = row.brand.strip()
    if not brand:
        issues.append(RowIssue("no-brand", ("brand",), "No brand"))
    elif is_cam_brand(brand):
        issues.append(_cam_brand("brand", brand, "tool"))
    if not row.part_number.strip():
        issues.append(RowIssue("no-part-number", ("part_number",), "No part number"))
    holder_brand = row.holder_brand.strip()
    if not holder_brand or not row.holder_part_number.strip():
        issues.append(
            RowIssue(
                "no-holder",
                ("holder_brand", "holder_part_number"),
                "Holder brand or part number missing",
            )
        )
    if holder_brand and is_cam_brand(holder_brand):
        issues.append(_cam_brand("holder_brand", holder_brand, "holder"))
    return issues


def _cam_brand(field_name: str, name: str, what: str) -> RowIssue:
    return RowIssue("cam-brand", (field_name,), f"{name} is a CAM system, not a {what} brand")


def _fold(name: str) -> str:
    return _NOT_ALPHANUMERIC.sub("", name.lower())
