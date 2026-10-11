"""Format detection, the CLI, and the JSON output against the published schemas."""

import json
from pathlib import Path
from typing import Any

import pytest
from fusion_factory import build_fusion_library, fusion_tool
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from tooldb_factory import AssemblySpec, build_tooldb

from toolbom_reader import LibraryError, combine, read_library
from toolbom_reader.cli import main

SCHEMA_DIR = Path(__file__).parent.parent / "schema"


def _validator(name: str) -> Draft202012Validator:
    schemas = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in SCHEMA_DIR.glob("*.json")
    }
    registry: Registry[Any] = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    schema = schemas[name]
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=registry)


def test_mastercam_is_recognised_by_content_whatever_the_name(tmp_path: Path) -> None:
    library = read_library(build_tooldb(tmp_path / "renamed.bin", [AssemblySpec()]))
    assert library.source == "mastercam"
    assert len(library.rows) == 1


@pytest.mark.parametrize(("name", "zipped"), [("lib.tools", True), ("lib.json", False)])
def test_fusion_is_recognised_zipped_or_plain(tmp_path: Path, name: str, zipped: bool) -> None:
    library = read_library(build_fusion_library(tmp_path / name, [fusion_tool()], zipped=zipped))
    assert library.source == "fusion"


def test_json_with_a_byte_order_mark_is_read_as_fusion(tmp_path: Path) -> None:
    path = build_fusion_library(tmp_path / "lib.json", [fusion_tool()], zipped=False)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert read_library(path).source == "fusion"


def test_anything_else_is_a_library_error(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(LibraryError, match="Unrecognized tool library"):
        read_library(path)


def test_a_missing_file_is_a_library_error(tmp_path: Path) -> None:
    with pytest.raises(LibraryError, match="not found"):
        read_library(tmp_path / "nope.tooldb")


def test_rows_are_cleaned_of_control_characters(tmp_path: Path) -> None:
    tool = fusion_tool(description="T1 - NORTHLINE_155\x00503 (EM)")
    library = read_library(build_fusion_library(tmp_path / "lib.tools", [tool]))
    assert library.rows[0].part_number == "155503"


def test_output_matches_the_bom_schema(tmp_path: Path) -> None:
    tools = [
        fusion_tool(number=1),
        fusion_tool(number=2, description="Milling Tool-5 Parameters", shank=None),
        fusion_tool(number=3, unit="millimeters", shank=6.0),
    ]
    library = read_library(build_fusion_library(tmp_path / "lib.tools", tools))
    _validator("bom.schema.json").validate(library.to_dict())


def test_combined_output_matches_the_purchase_list_schema(tmp_path: Path) -> None:
    library = read_library(
        build_tooldb(tmp_path / "t.tooldb", [AssemblySpec(tool_number=n) for n in (1, 2)])
    )
    combined = {"source": library.source, **combine(library.rows).to_dict()}
    _validator("purchase-lists.schema.json").validate(combined)


def test_cli_prints_rows_as_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = build_fusion_library(tmp_path / "lib.tools", [fusion_tool()])
    assert main([str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["source"] == "fusion"
    assert output["rows"][0]["part_number"] == "NL-1550"


def test_cli_combine_prints_purchase_lists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = build_fusion_library(
        tmp_path / "lib.tools", [fusion_tool(number=1), fusion_tool(number=2)]
    )
    assert main([str(path), "--combine"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert [(t["quantity"], t["tool_numbers"]) for t in output["tools"]] == [(2, [1, 2])]


def test_cli_reports_a_bad_file_and_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "nope.tools")]) == 1
    assert "not found" in capsys.readouterr().err
