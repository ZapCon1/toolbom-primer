import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest
from tooldb_factory import AssemblySpec, ItemSpec, build_tooldb

from toolbom_reader import BomRow, LibraryError, TooManyToolsError, mastercam
from toolbom_reader.rows import MAX_TOOLS


def test_empty_library_gives_no_rows(tmp_path: Path) -> None:
    assert mastercam.read_rows(build_tooldb(tmp_path / "t.tooldb", [])) == []


def test_assembly_maps_to_a_bom_row(tmp_path: Path) -> None:
    db = build_tooldb(
        tmp_path / "t.tooldb",
        [
            AssemblySpec(
                tool_number=7,
                tool=ItemSpec("Northline", "", 'CID0001 - .5" X 1.0 EM', "", False),
                manufacturer_code="NL-9550",
                shank_diameter=0.23622047244094202,
            )
        ],
    )
    assert mastercam.read_rows(db) == [
        BomRow(
            brand="Northline",
            part_number="NL-9550",
            description='.5" X 1.0 EM',
            shank="6MM",
            tool_number=7,
            holder_brand="GRIPWELL",
            holder_part_number="GW-HYD-12",
            holder_description="HYDRO 12",
        )
    ]


def test_rows_are_ordered_by_tool_number_with_unnumbered_last(tmp_path: Path) -> None:
    db = build_tooldb(
        tmp_path / "t.tooldb",
        [AssemblySpec(tool_number=n) for n in (3, None, 1, 2)],
    )
    assert [row.tool_number for row in mastercam.read_rows(db)] == [1, 2, 3, None]


def test_part_number_falls_back_to_catalog_id(tmp_path: Path) -> None:
    db = build_tooldb(
        tmp_path / "t.tooldb",
        [AssemblySpec(manufacturer_code="", tool=ItemSpec(catalog_id="CAT-1"))],
    )
    assert mastercam.read_rows(db)[0].part_number == "CAT-1"


def test_assembly_without_tool_or_holder_leaves_those_fields_blank(tmp_path: Path) -> None:
    db = build_tooldb(
        tmp_path / "t.tooldb", [AssemblySpec(name="T5 PROBE", tool=None, holder=None)]
    )
    row = mastercam.read_rows(db)[0]
    assert (row.brand, row.part_number, row.description, row.shank) == ("", "", "T5 PROBE", None)
    assert (row.holder_brand, row.holder_part_number, row.holder_description) == ("", "", "")


def test_a_file_that_isnt_a_tool_library_is_a_library_error(tmp_path: Path) -> None:
    other = tmp_path / "other.tooldb"
    with closing(sqlite3.connect(other)) as conn:
        conn.execute("CREATE TABLE Notes (ID INT)")
    with pytest.raises(LibraryError, match="missing tables"):
        mastercam.read_rows(other)


def test_generated_columns_are_rejected(tmp_path: Path) -> None:
    db = build_tooldb(tmp_path / "t.tooldb", [])
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("DROP TABLE TlAssembly")
        conn.execute(
            "CREATE TABLE TlAssembly (ID GUID, Description VARCHAR, MainHolder GUID,"
            " MainTool GUID, ToolNumber INT,"
            " Name TEXT GENERATED ALWAYS AS (printf('%.*c', 200000000, 'x')))"
        )
        conn.commit()
    with pytest.raises(LibraryError, match="computed columns"):
        mastercam.read_rows(db)


def test_repeated_ids_are_rejected_before_the_joins_multiply(tmp_path: Path) -> None:
    db = build_tooldb(tmp_path / "t.tooldb", [])
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("DROP TABLE TlAssemblyItem")
        conn.execute(
            "CREATE TABLE TlAssemblyItem (ID GUID, CatalogID VARCHAR, TlManufacturerID GUID,"
            " Name VARCHAR, Description VARCHAR, IsMetric BOOL)"
        )
        conn.executemany(
            "INSERT INTO TlAssembly VALUES (?, 'a', '', 'x', 'x', ?)",
            ((n, n) for n in range(3_000)),
        )
        conn.executemany(
            "INSERT INTO TlAssemblyItem VALUES ('x', '', 'm', '', '', 0)",
            ([] for _ in range(3_000)),
        )
        conn.commit()
    start = time.perf_counter()
    with pytest.raises(LibraryError, match="TlAssemblyItem repeats IDs"):
        mastercam.read_rows(db)
    assert time.perf_counter() - start < 1.0


def test_an_oversized_stored_value_is_a_library_error(tmp_path: Path) -> None:
    db = build_tooldb(tmp_path / "t.tooldb", [AssemblySpec(name="x" * 200_000)])
    with pytest.raises(LibraryError, match="Not a readable tool library"):
        mastercam.read_rows(db)


def test_more_than_the_tool_limit_is_refused(tmp_path: Path) -> None:
    db = build_tooldb(
        tmp_path / "t.tooldb",
        [AssemblySpec(tool_number=n, tool=None, holder=None) for n in range(MAX_TOOLS + 1)],
    )
    with pytest.raises(TooManyToolsError):
        mastercam.read_rows(db)
