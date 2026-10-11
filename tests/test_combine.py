from toolbom_reader import BomRow, combine


def row(tool_number: int, **overrides: object) -> BomRow:
    fields: dict[str, object] = {
        "brand": "NORTHLINE",
        "part_number": "NL-1550",
        "description": "EM D6",
        "shank": "6MM",
        "tool_number": tool_number,
        "holder_brand": "APEX",
        "holder_part_number": "AH-ER16-100",
        "holder_description": "",
    }
    fields.update(overrides)
    return BomRow(**fields)  # type: ignore[arg-type]


def test_no_rows_give_empty_lists() -> None:
    lists = combine([])
    assert (lists.tools, lists.holders, lists.collets) == ([], [], [])


def test_one_row_gives_one_line_of_each() -> None:
    lists = combine([row(1, collet="ER16-6")])
    assert [(t.part_number, t.quantity, t.tool_numbers) for t in lists.tools] == [
        ("NL-1550", 1, [1])
    ]
    assert [(h.part_number, h.quantity) for h in lists.holders] == [("AH-ER16-100", 1)]
    assert [(c.collet, c.holder, c.quantity) for c in lists.collets] == [
        ("ER16-6", "APEX AH-ER16-100", 1)
    ]


def test_same_tool_twice_is_one_line_with_quantities_summed() -> None:
    lists = combine([row(4, quantity=3), row(1)])  # blank quantity counts as 1
    assert [(t.quantity, t.tool_numbers) for t in lists.tools] == [(4, [1, 4])]


def test_brand_and_part_match_ignoring_case_and_spaces() -> None:
    lists = combine([row(1, brand="Northline "), row(2, part_number=" NL-1550")])
    assert len(lists.tools) == 1


def test_holders_count_assemblies_not_tool_quantities() -> None:
    lists = combine([row(1, quantity=4), row(2, part_number="OTHER", quantity=2)])
    assert [(h.quantity, h.tool_numbers) for h in lists.holders] == [(2, [1, 2])]


def test_tools_without_a_part_number_are_never_merged() -> None:
    lists = combine([row(1, part_number=""), row(2, part_number="")])
    assert [t.tool_numbers for t in lists.tools] == [[1], [2]]


def test_holders_and_collets_without_a_part_number_are_left_out() -> None:
    lists = combine([row(1, holder_part_number="", collet=" ")])
    assert (lists.holders, lists.collets) == ([], [])


def test_n_rows_keep_first_appearance_order() -> None:
    parts = ["C", "A", "B", "A", "C"]
    lists = combine([row(n, part_number=p) for n, p in enumerate(parts)])
    assert [t.part_number for t in lists.tools] == ["C", "A", "B"]
    assert [t.tool_numbers for t in lists.tools] == [[0, 4], [1, 3], [2]]


def test_the_worked_example_in_docs_combine_md() -> None:
    lists = combine(
        [
            row(1, quantity=3, collet="ER16-6"),
            row(2, collet="ER16-6"),
            row(3, part_number="", collet="ER16-4"),
            row(4, part_number="", holder_part_number=""),
        ]
    )
    assert [(t.part_number, t.quantity, t.tool_numbers) for t in lists.tools] == [
        ("NL-1550", 4, [1, 2]),
        ("", 1, [3]),
        ("", 1, [4]),
    ]
    assert [(h.part_number, h.quantity, h.tool_numbers) for h in lists.holders] == [
        ("AH-ER16-100", 3, [1, 2, 3])
    ]
    assert [(c.collet, c.quantity, c.tool_numbers) for c in lists.collets] == [
        ("ER16-6", 2, [1, 2]),
        ("ER16-4", 1, [3]),
    ]
