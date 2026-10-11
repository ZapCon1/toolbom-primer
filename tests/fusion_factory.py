"""Build synthetic Fusion 360 tool libraries (.tools zip or plain .json) for tests."""

import json
import zipfile
from pathlib import Path
from typing import Any


def fusion_tool(
    number: int | None = 11,
    description: str = "LIB0201_1010 - NORTHLINE_NL-1550 (EM_D6.0_L25.34_R0.0_A)",
    vendor: str = "NORTHLINE",
    tool_type: str = "flat end mill",
    unit: str = "inches",
    shank: float | None = 0.23622,
    holder: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    tool: dict[str, Any] = {
        "type": tool_type,
        "description": description,
        "vendor": vendor,
        "product-id": "",
        "unit": unit,
        "geometry": {} if shank is None else {"SFDM": shank},
        "holder": {"description": "APEX_AH-ER16-563", "vendor": "", "product-id": ""}
        if holder is None
        else holder,
        "post-process": {} if number is None else {"number": number},
    }
    tool.update(extra)
    return tool


def build_fusion_library(path: Path, tools: list[dict[str, Any]], zipped: bool = True) -> Path:
    document = json.dumps({"data": tools, "version": 37})
    if zipped:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("tools.json", document)
    else:
        path.write_text(document, encoding="utf-8")
    return path
