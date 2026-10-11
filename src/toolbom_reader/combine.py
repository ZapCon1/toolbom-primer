"""Combine duplicate tools, holders and collets into purchase lists.

A BOM has one row per tool assembly, so a holder used by 27 tools appears 27
times. Combining turns the rows into three shopping lists:

  tools    grouped by tool brand + part number
  holders  grouped by holder brand + part number
  collets  grouped by collet part number (the same holder takes different
           collets for different shanks)

A tool line's quantity is the sum of its rows' quantities, a blank quantity
counting as 1. Holder and collet lines count assemblies instead: a holder
holds one tool at a time, so buying 4 of an end mill as spares doesn't mean
buying 4 holders. Rows without a part number can't be matched safely (Fusion's
"Milling Tool-5 Parameters" placeholders are different tools), so such a tool
stays on its own line, and a holder or collet without one is left out.
See docs/COMBINE.md.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from toolbom_reader.rows import BomRow, Shank


@dataclass(frozen=True)
class ToolLine:
    brand: str
    part_number: str
    description: str
    hyperlink: str
    shank: Shank | None
    quantity: int
    tool_numbers: list[int]  # where the part is used


@dataclass(frozen=True)
class HolderLine:
    brand: str
    part_number: str
    description: str
    hyperlink: str
    spindle_taper: str
    quantity: int
    tool_numbers: list[int]


@dataclass(frozen=True)
class ColletLine:
    collet: str
    holder: str  # "APEX AH-ER16-100"
    shank: Shank | None
    quantity: int
    tool_numbers: list[int]


@dataclass(frozen=True)
class PurchaseLists:
    tools: list[ToolLine]
    holders: list[HolderLine]
    collets: list[ColletLine]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _Group:
    first: BomRow
    rows: list[BomRow] = field(default_factory=list)

    def tool_quantity(self) -> int:
        return sum(1 if row.quantity is None else row.quantity for row in self.rows)

    def tool_numbers(self) -> list[int]:
        return sorted({row.tool_number for row in self.rows if row.tool_number is not None})

    def first_text(self, field_name: str) -> str:
        """The first non-blank value: rows for one part should agree, but may not."""
        for row in self.rows:
            value = getattr(row, field_name)
            if isinstance(value, str) and value.strip():
                return value
        return ""


def combine(rows: list[BomRow]) -> PurchaseLists:
    """Purchase lists from BOM rows, in order of first appearance."""
    tools = _group(rows, lambda r: _part_key(r.brand, r.part_number), keep_unkeyed=True)
    holders = _group(rows, lambda r: _part_key(r.holder_brand, r.holder_part_number))
    collets = _group(rows, lambda r: r.collet.strip().upper() or None)
    return PurchaseLists(
        tools=[
            ToolLine(
                brand=g.first.brand,
                part_number=g.first.part_number,
                description=g.first_text("description"),
                hyperlink=g.first_text("hyperlink"),
                shank=g.first.shank,
                quantity=g.tool_quantity(),
                tool_numbers=g.tool_numbers(),
            )
            for g in tools
        ],
        holders=[
            HolderLine(
                brand=g.first.holder_brand,
                part_number=g.first.holder_part_number,
                description=g.first_text("holder_description"),
                hyperlink=g.first_text("holder_hyperlink"),
                spindle_taper=g.first_text("spindle_taper"),
                quantity=len(g.rows),
                tool_numbers=g.tool_numbers(),
            )
            for g in holders
        ],
        collets=[
            ColletLine(
                collet=g.first.collet.strip(),
                holder=" ".join(p for p in (g.first.holder_brand, g.first.holder_part_number) if p),
                shank=g.first.shank,
                quantity=len(g.rows),
                tool_numbers=g.tool_numbers(),
            )
            for g in collets
        ],
    )


def _part_key(brand: str, part: str) -> str | None:
    """Brand + part, case-insensitive; None when there's no part number to match on."""
    part = part.strip().upper()
    return f"{brand.strip().upper()}|{part}" if part else None


def _group(
    rows: list[BomRow], key_of: Callable[[BomRow], str | None], keep_unkeyed: bool = False
) -> list[_Group]:
    groups: dict[str | tuple[str, int], _Group] = {}
    for index, row in enumerate(rows):
        part_key = key_of(row)
        if part_key is None and not keep_unkeyed:
            continue
        key = part_key if part_key is not None else ("row", index)  # unkeyed: its own line
        group = groups.setdefault(key, _Group(first=row))
        group.rows.append(row)
    return list(groups.values())
