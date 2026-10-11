"""Read a Fusion tool library (.tools, or an exported .json) as BOM rows.

A .tools file is a zip holding one tools.json; an exported .json is the same
document unzipped. Its "data" array has one entry per tool, each with its
holder embedded.

Fusion's part-number fields ("product-id", holder "vendor"/"product-id") are
usually empty. Libraries encode identity in the descriptions instead:

    tool:   "LIB0202_1001 - KESTREL_KT-FM5200-A (FM_D50.8_L45.0 _R.787)"
             <tool ID>      <brand>_<part number>  (<size spec>)
    holder: "APEX_AH-ER16-100"   ->  brand APEX, part AH-ER16-100

Descriptions that don't follow the pattern (Fusion's "Milling Tool-5
Parameters" placeholder, a bare size spec) get a blank brand and part number,
never a guess. See docs/FUSION.md.
"""

import json
import re
import zipfile
import zlib
from pathlib import Path
from typing import Any, NamedTuple

from toolbom_reader.errors import LibraryError, TooManyToolsError
from toolbom_reader.rows import MAX_TOOLS, BomRow, format_shank

ZIP_ENTRY = "tools.json"
# A real library averages ~6.6 KB, ~28 JSON objects/arrays and ~117 commas
# per tool. These caps, checked on the raw bytes before parsing, leave ~40%
# headroom over MAX_TOOLS real tools while stopping a JSON bomb (a few MB of
# "{}," parses into millions of objects).
MAX_TOOLS_JSON_BYTES = 40 * 1024 * 1024
MAX_JSON_CONTAINERS = 200_000
MAX_JSON_COMMAS = 820_000
_NOT_TOOLS = frozenset({"holder", "probe"})

# "<tool ID> - <rest>"; the ID itself never contains " - ".
_TOOL_ID_PREFIX = re.compile(r"^\S+\s+-\s+")
# "<head> (<spec>)": identity before the parentheses, size spec inside.
_HEAD_AND_SPEC = re.compile(r"^(?P<head>.+?)\s*\((?P<spec>.*)\)\s*$")


class Identity(NamedTuple):
    brand: str
    part_number: str


def read_rows(path: Path) -> list[BomRow]:
    """One row per tool, ordered by tool number."""
    rows = [_to_row(tool) for tool in _load_tools(path)]
    return sorted(rows, key=lambda r: (r.tool_number is None, r.tool_number or 0))


def parse_tool_description(description: str, vendor: str) -> tuple[Identity, str]:
    """Split a tool description into (brand, part number) and the size spec.

    `vendor` anchors the brand when the description uses a space instead of an
    underscore ("Blue Ridge 32257 (...)").
    """
    rest = _TOOL_ID_PREFIX.sub("", description.strip())
    match = _HEAD_AND_SPEC.match(rest)
    if not match:
        return Identity("", ""), rest
    head, spec = match["head"].strip(), match["spec"].strip()
    vendor = vendor.strip()
    anchored = len(head) > len(vendor) and head.lower().startswith(vendor.lower())
    if vendor and anchored and head[len(vendor)] in "_ ":
        return Identity(head[: len(vendor)], head[len(vendor) + 1 :].strip()), spec
    if "_" in head:
        brand, part = head.split("_", 1)
        return Identity(brand.strip(), part.strip()), spec
    return Identity("", head), spec


def parse_holder_description(description: str) -> Identity:
    """ "APEX_AH-ER16-100" -> brand APEX, part AH-ER16-100."""
    description = description.strip()
    if "_" in description:
        brand, part = description.split("_", 1)
        return Identity(brand.strip(), part.strip())
    return Identity("", description)


def _to_row(tool: dict[str, Any]) -> BomRow:
    identity, spec = parse_tool_description(
        _text(tool.get("description")), _text(tool.get("vendor"))
    )
    tool_type = _text(tool.get("type")).upper()
    # A parsed spec ("EM_D6.0_L25.34") is cryptic alone, so prefix the tool type.
    # An unparsed description is kept as written.
    parsed = bool(identity.part_number)
    description = f"{tool_type} - {spec}" if parsed and spec and tool_type else spec or tool_type
    holder = _section(tool, "holder")
    holder_identity = parse_holder_description(_text(holder.get("description")))
    return BomRow(
        brand=identity.brand,
        part_number=_text(tool.get("product-id")) or identity.part_number,
        description=description,
        # SFDM is the shank diameter, in the tool's own unit.
        shank=format_shank(
            _number(_section(tool, "geometry").get("SFDM")),
            flagged_metric=_text(tool.get("unit")).lower().startswith("millimet"),
        ),
        tool_number=_integer(_section(tool, "post-process").get("number")),
        holder_brand=_text(holder.get("vendor")) or holder_identity.brand,
        holder_part_number=_text(holder.get("product-id")) or holder_identity.part_number,
        holder_description="",
        hyperlink=_text(tool.get("product-link")),
        holder_hyperlink=_text(holder.get("product-link")),
    )


def _load_tools(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise LibraryError(f"Tool library not found: {path}")
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                raw = _read_entry(archive, path)
        else:
            raw = path.read_bytes()
        _check_structure(raw, path)
        document = json.loads(raw)
    except KeyError as error:
        raise LibraryError(f"Not a Fusion tool library: {path} (no {ZIP_ENTRY})") from error
    except (
        zipfile.BadZipFile,
        zlib.error,
        EOFError,
        NotImplementedError,  # unsupported compression method
        RuntimeError,  # encrypted entry
        UnicodeDecodeError,
        ValueError,  # bad JSON, or an integer too long to convert
        RecursionError,  # pathologically nested JSON
    ) as error:
        raise LibraryError(f"Not a readable Fusion tool library: {path} ({error})") from error
    tools = document.get("data") if isinstance(document, dict) else None
    if not isinstance(tools, list):
        raise LibraryError(f"Not a Fusion tool library: {path} (no tool list)")
    entries = [t for t in tools if isinstance(t, dict) and t.get("type") not in _NOT_TOOLS]
    if len(entries) > MAX_TOOLS:
        raise TooManyToolsError(len(entries))
    return entries


def _check_structure(raw: bytes, path: Path) -> None:
    """Reject a JSON bomb by its shape, without parsing it.

    Brackets inside strings count too, which only makes the check stricter.
    """
    if len(raw) > MAX_TOOLS_JSON_BYTES:
        raise LibraryError(f"Fusion tool library too large: {path} ({len(raw)} bytes)")
    containers = raw.count(b"{") + raw.count(b"[")
    commas = raw.count(b",")
    if containers > MAX_JSON_CONTAINERS or commas > MAX_JSON_COMMAS:
        raise LibraryError(
            f"Not a plausible Fusion tool library: {path} "
            f"({containers} objects/arrays, {commas} commas)"
        )


def _read_entry(archive: zipfile.ZipFile, path: Path) -> bytes:
    # Check the declared size before inflating: a few KB of zip can expand to
    # gigabytes. zipfile stops at the declared size, so a lying header can't
    # get past this either.
    size = archive.getinfo(ZIP_ENTRY).file_size
    if size > MAX_TOOLS_JSON_BYTES:
        raise LibraryError(f"Fusion tool library too large: {path} ({size} bytes of {ZIP_ENTRY})")
    return archive.read(ZIP_ENTRY)


def _section(tool: dict[str, Any], key: str) -> dict[str, Any]:
    """A nested object of the tool, or {} when it's missing or malformed."""
    value = tool.get(key)
    return value if isinstance(value, dict) else {}


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None
