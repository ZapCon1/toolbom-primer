import time
import zipfile
from pathlib import Path

import pytest
from fusion_factory import build_fusion_library, fusion_tool

from toolbom_reader import BomRow, LibraryError, TooManyToolsError, fusion
from toolbom_reader.fusion import parse_holder_description, parse_tool_description
from toolbom_reader.rows import MAX_TOOLS


@pytest.mark.parametrize(
    ("description", "vendor", "brand", "part", "spec"),
    [
        ("LIB0202_1001 - KESTREL_KT-FM5200-A (FM_D50.8_L45.0 _R.787)", "KESTREL", "KESTREL", "KT-FM5200-A", "FM_D50.8_L45.0 _R.787"),
        ("LIB0201_1020 - TAPWORKS_1942.002 (EM_D2.0)", "TAPWORKS", "TAPWORKS", "1942.002", "EM_D2.0"),
        # A space after the brand: the vendor field marks where the brand ends.
        ("LIB0301_1001 - Blue Ridge 32257 (1.0 drill)", "Blue Ridge", "Blue Ridge", "32257", "1.0 drill"),
        # The vendor field disagrees: the description wins.
        ("LIB0203_1005 - MICROLINE_70078 (BM_D2.0)", "Northline", "MICROLINE", "70078", "BM_D2.0"),
        ("LIB0203_1014 - P-75442 (BM_D4.0_L24.0)", "", "", "P-75442", "BM_D4.0_L24.0"),
        ("ORBIT_OB-781005 (EM_D0.5)", "ORBIT", "ORBIT", "OB-781005", "EM_D0.5"),
    ],
)  # fmt: skip
def test_tool_description_gives_brand_part_and_spec(
    description: str, vendor: str, brand: str, part: str, spec: str
) -> None:
    identity, parsed_spec = parse_tool_description(description, vendor)
    assert (identity.brand, identity.part_number, parsed_spec) == (brand, part, spec)


@pytest.mark.parametrize(
    "description",
    ["LIB0201_1005 - Milling Tool-5 Parameters", "LIB0231_1005 - TM_D1.1_L8.0_R0.0", ""],
)
def test_description_without_the_pattern_gets_no_brand_or_part(description: str) -> None:
    identity, _ = parse_tool_description(description, "")
    assert identity == ("", "")


@pytest.mark.parametrize(
    ("description", "brand", "part"),
    [("APEX_AH-ER16-100", "APEX", "AH-ER16-100"), ("CT-4075", "", "CT-4075"), ("", "", "")],
)
def test_holder_description_gives_brand_and_part(description: str, brand: str, part: str) -> None:
    assert parse_holder_description(description) == (brand, part)


def test_tool_maps_to_a_bom_row(tmp_path: Path) -> None:
    tool = fusion_tool()
    tool["product-link"] = "https://northline.example/x"
    library = build_fusion_library(tmp_path / "lib.tools", [tool])
    assert fusion.read_rows(library) == [
        BomRow(
            brand="NORTHLINE",
            part_number="NL-1550",
            description="FLAT END MILL - EM_D6.0_L25.34_R0.0_A",
            shank="6MM",
            tool_number=11,
            holder_brand="APEX",
            holder_part_number="AH-ER16-563",
            holder_description="",
            hyperlink="https://northline.example/x",
        )
    ]


@pytest.mark.parametrize("count", [0, 1, 2, 30])
def test_one_row_per_tool_ordered_by_number(tmp_path: Path, count: int) -> None:
    tools = [fusion_tool(number=n) for n in reversed(range(count))]
    rows = fusion.read_rows(build_fusion_library(tmp_path / "lib.tools", tools))
    assert [row.tool_number for row in rows] == list(range(count))


def test_plain_json_export_reads_the_same_as_a_tools_zip(tmp_path: Path) -> None:
    tools = [fusion_tool(number=1), fusion_tool(number=2, unit="millimeters", shank=8.0)]
    zipped = fusion.read_rows(build_fusion_library(tmp_path / "a.tools", tools))
    plain = fusion.read_rows(build_fusion_library(tmp_path / "a.json", tools, zipped=False))
    assert zipped == plain
    assert plain[1].shank == "8MM"


def test_holders_and_probes_in_the_list_are_not_tools(tmp_path: Path) -> None:
    tools = [fusion_tool(), {"type": "holder"}, {"type": "probe"}]
    assert len(fusion.read_rows(build_fusion_library(tmp_path / "lib.tools", tools))) == 1


def test_a_zip_without_tools_json_is_a_library_error(tmp_path: Path) -> None:
    path = tmp_path / "lib.tools"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("other.json", "{}")
    with pytest.raises(LibraryError, match="no tools.json"):
        fusion.read_rows(path)


def test_a_json_bomb_is_rejected_fast_without_parsing(tmp_path: Path) -> None:
    path = tmp_path / "bomb.tools"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("tools.json", '{"data":[' + "{}," * 400_000 + "{}]}")
    start = time.perf_counter()
    with pytest.raises(LibraryError, match="Not a plausible Fusion tool library"):
        fusion.read_rows(path)
    assert time.perf_counter() - start < 1.0


def test_more_than_the_tool_limit_is_refused(tmp_path: Path) -> None:
    tools = [{"type": "flat end mill"}] * (MAX_TOOLS + 1)
    with pytest.raises(TooManyToolsError, match="5,001 tools"):
        fusion.read_rows(build_fusion_library(tmp_path / "lib.tools", tools))
