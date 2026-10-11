"""Rebuild the example libraries and their expected output.

    python examples/build_examples.py

The libraries are synthetic (fictional brands and part numbers), built with
the same factories the tests use. Each shows one of the traps the docs
describe; tests/test_examples.py checks the committed output still matches.
"""

import sys
from pathlib import Path
from typing import Any

EXAMPLES = Path(__file__).parent
sys.path.insert(0, str(EXAMPLES.parent / "tests"))

from fusion_factory import build_fusion_library, fusion_tool  # noqa: E402
from tooldb_factory import AssemblySpec, ItemSpec, build_tooldb  # noqa: E402

from toolbom_reader.cli import main  # noqa: E402

GRIPWELL_HYDRO = ItemSpec("GRIPWELL", "GW-HYD-12", "", "HYDRO CHUCK 12MM CAT40")
APEX_ER16 = ItemSpec("APEX", "AH-ER16-100", "", "ER16 COLLET CHUCK CAT40")

MASTERCAM_ASSEMBLIES = [
    # A metric end mill: the shank is stored in inches (6 mm) and IsMetric is off.
    AssemblySpec(
        tool_number=1,
        tool=ItemSpec("NORTHLINE", "", "CID0001 - 6MM 3FL SQUARE END MILL", ""),
        holder=GRIPWELL_HYDRO,
        manufacturer_code="NL-1550",
        shank_diameter=0.23622047244094202,
    ),
    # The same end mill again at another T number: combines into one tool line.
    AssemblySpec(
        tool_number=2,
        tool=ItemSpec("NORTHLINE", "", "CID0002 - 6MM 3FL SQUARE END MILL", ""),
        holder=GRIPWELL_HYDRO,
        manufacturer_code="NL-1550",
        shank_diameter=0.23622047244094202,
    ),
    # An inch drill: 1/4" is 6.35 mm, off the metric grid, so it stays a number.
    AssemblySpec(
        tool_number=3,
        tool=ItemSpec("KESTREL", "", 'CID0003 - 1/4" JOBBER DRILL', ""),
        holder=APEX_ER16,
        manufacturer_code="KT-D250",
        shank_diameter=0.25,
    ),
    # A 2.5" face mill arbor: 63.5 mm lands on the metric grid, but it's an inch size.
    AssemblySpec(
        tool_number=10,
        tool=ItemSpec("ORBIT", "", 'CID0004 - 4" FACE MILL', ""),
        holder=ItemSpec("APEX", "AH-SM-250", "", "SHELL MILL ARBOR 2.5 CAT40"),
        manufacturer_code="OR-FM400",
        shank_diameter=2.5,
    ),
    # A placeholder: the brand is the CAM system and there's no part number.
    AssemblySpec(
        tool_number=12,
        tool=ItemSpec("Mastercam", "", "CID0005 - 1/2 CHAMFER MILL", ""),
        holder=APEX_ER16,
        manufacturer_code="",
        shank_diameter=0.5,
    ),
    # No holder assigned.
    AssemblySpec(
        tool_number=20,
        tool=ItemSpec("TAPWORKS", "", "CID0006 - M8x1.25 THREAD MILL", ""),
        holder=None,
        manufacturer_code="TW-M8-125",
        shank_diameter=0.31496062992126,
    ),
]


def _from_catalog(product_id: str, product_link: str, **tool: Any) -> dict[str, Any]:
    """A tool from a library built from a vendor catalog: product fields filled in."""
    built = fusion_tool(**tool)
    built["product-id"] = product_id
    built["product-link"] = product_link
    return built


FUSION_TOOLS = [
    # The usual pattern: "<tool ID> - <BRAND>_<PART> (<spec>)".
    fusion_tool(
        number=1,
        description="LIB0201_1010 - NORTHLINE_NL-1550 (EM_D6.0_L25.34_R0.0_A)",
        holder={"description": "APEX_AH-ER16-100", "vendor": "", "product-id": ""},
    ),
    # A brand with a space, anchored by the vendor field.
    fusion_tool(
        number=2,
        description="LIB0202_1001 - Blue Ridge 32257 (DR_D3.0_L20.0)",
        vendor="Blue Ridge",
        tool_type="drill",
        shank=0.11811023622047245,
        holder={"description": "APEX_AH-ER16-100", "vendor": "", "product-id": ""},
    ),
    _from_catalog(
        number=3,
        description="LIB0203_1002 - MICROLINE_ML-0400 (BEM_D1.0_L3.0)",
        vendor="MICROLINE",
        tool_type="ball end mill",
        unit="millimeters",
        shank=4.0,
        holder={
            "description": "GRIPWELL_GW-SHR-4",
            "vendor": "GRIPWELL",
            "product-id": "GW-SHR-4",
            "product-link": "https://example.com/gripwell/gw-shr-4",
        },
        product_id="ML-0400",
        product_link="https://example.com/microline/ml-0400",
    ),
    # Fusion's placeholder: no identity to parse, so brand and part stay blank.
    fusion_tool(
        number=4,
        description="Milling Tool-5 Parameters",
        vendor="",
        shank=0.5,
        holder={"description": "", "vendor": "", "product-id": ""},
    ),
]


def build() -> None:
    mastercam = EXAMPLES / "mastercam-example.tooldb"
    mastercam.unlink(missing_ok=True)  # sqlite would add to an existing file
    build_tooldb(mastercam, MASTERCAM_ASSEMBLIES)
    fusion = build_fusion_library(EXAMPLES / "fusion-example.tools", FUSION_TOOLS)
    for library in (mastercam, fusion):
        stem = EXAMPLES / library.stem
        main([str(library), "-o", f"{stem}.bom.json"])
        main([str(library), "--combine", "-o", f"{stem}.purchase-lists.json"])
        main([str(library), "--csv", "-o", f"{stem}.bom.csv"])
        main([str(library), "--check", "-o", f"{stem}.check.txt"])


if __name__ == "__main__":
    build()
