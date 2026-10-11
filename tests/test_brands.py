"""Brand-spelling suggestions, beyond the conformance cases."""

from collections import Counter

import pytest

from toolbom_reader import BomRow, brand_suggestions
from toolbom_reader.brands import edit_distance, suggest


@pytest.mark.parametrize(
    ("a", "b", "distance"),
    [
        ("KESTREL", "KESTREL", 0),
        ("KESTREL", "KESTERL", 1),  # neighbours swapped
        ("GRIPWELL", "GRIPWEL", 1),  # deletion
        ("ORBIT", "ORBIK", 1),  # substitution
        ("NORTHLINE", "NORTHLAND", 2),
        ("", "ABC", 3),
    ],
)
def test_edit_distance_counts_a_swap_as_one_edit(a: str, b: str, distance: int) -> None:
    assert edit_distance(a, b) == distance
    assert edit_distance(b, a) == distance


def test_holder_brands_are_suggested_alongside_tool_brands() -> None:
    rows = [
        BomRow("NORTHLINE", "NL-1", "", None, 1, "Gripwell", "GW-1", ""),
        BomRow("APEX", "AP-1", "", None, 2, "GRIPWELL", "GW-1", ""),
    ]
    [suggestion] = brand_suggestions(rows)
    assert suggestion.spellings == ("GRIPWELL", "Gripwell")


def test_groups_used_more_often_come_first() -> None:
    found = suggest(Counter({"ORBIT": 1, "Orbit": 1, "NORTHLINE": 5, "Northline": 2}))
    assert [s.spellings[0] for s in found] == ["NORTHLINE", "ORBIT"]


def test_a_crowd_sharing_one_variant_is_not_treated_as_typos() -> None:
    # 60 names all one deletion from "ABCDEF": a generated list, not misspellings.
    crowd = Counter({f"ABCDEF{chr(0x4E00 + i)}": 1 for i in range(60)})
    assert suggest(crowd) == []
