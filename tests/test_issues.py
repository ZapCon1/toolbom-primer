"""Which rows need a person before anyone orders from the BOM."""

from dataclasses import replace

import pytest

from toolbom_reader import BomRow, is_cam_brand, row_issues

GOOD = BomRow("NORTHLINE", "NL-1550", "FLAT END MILL", "6MM", 11, "APEX", "AH-ER16-563", "")


def _row(
    brand: str = GOOD.brand,
    part_number: str = GOOD.part_number,
    holder_brand: str = GOOD.holder_brand,
    holder_part_number: str = GOOD.holder_part_number,
) -> BomRow:
    return replace(
        GOOD,
        brand=brand,
        part_number=part_number,
        holder_brand=holder_brand,
        holder_part_number=holder_part_number,
    )


def test_a_complete_row_has_no_issues() -> None:
    assert row_issues(GOOD) == []


@pytest.mark.parametrize(
    ("changes", "kinds"),
    [
        ({"brand": "  "}, ["no-brand"]),
        ({"part_number": ""}, ["no-part-number"]),
        ({"holder_brand": ""}, ["no-holder"]),
        ({"holder_part_number": ""}, ["no-holder"]),
        ({"holder_brand": "", "holder_part_number": ""}, ["no-holder"]),  # one issue, not two
        (
            {"brand": "", "part_number": "", "holder_brand": ""},
            ["no-brand", "no-part-number", "no-holder"],
        ),
    ],
)
def test_each_missing_value_is_flagged(changes: dict[str, str], kinds: list[str]) -> None:
    assert [issue.kind for issue in row_issues(_row(**changes))] == kinds


def test_a_cam_system_as_tool_brand_is_flagged_with_its_name() -> None:
    [issue] = row_issues(_row(brand="Mastercam"))
    assert issue.to_dict() == {
        "kind": "cam-brand",
        "fields": ("brand",),
        "message": "Mastercam is a CAM system, not a tool brand",
    }


def test_a_cam_system_as_holder_brand_is_flagged() -> None:
    [issue] = row_issues(_row(holder_brand="Autodesk"))
    assert (issue.kind, issue.fields) == ("cam-brand", ("holder_brand",))
    assert issue.message == "Autodesk is a CAM system, not a holder brand"


def test_a_cam_holder_brand_without_a_part_number_gets_both_issues() -> None:
    issues = row_issues(_row(holder_brand="Fusion", holder_part_number=""))
    assert [i.kind for i in issues] == ["no-holder", "cam-brand"]


@pytest.mark.parametrize(
    "name", ["Mastercam", "MASTERCAM", "Fusion 360", "fusion-360", "Autodesk Fusion", " hyperMILL "]
)
def test_cam_names_match_however_they_are_spelled(name: str) -> None:
    assert is_cam_brand(name)


@pytest.mark.parametrize("name", ["NORTHLINE", "Mastercam Tools Inc", "Fusionware", "", "NXT"])
def test_real_brands_and_near_misses_are_not_cam_systems(name: str) -> None:
    assert not is_cam_brand(name)
