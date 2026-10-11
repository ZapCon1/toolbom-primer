"""Build minimal synthetic .tooldb files for tests.

Only the tables and columns the reader touches are created. Real libraries
have ~80 tables; the reader must not depend on the others.
"""

import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

_SCHEMA = """
CREATE TABLE TlManufacturer (ID GUID PRIMARY KEY, Name VARCHAR, Description VARCHAR);
CREATE TABLE TlAssemblyItem (
    ID GUID PRIMARY KEY, CatalogID VARCHAR, TlManufacturerID GUID,
    Name VARCHAR, Description VARCHAR, IsMetric BOOL
);
CREATE TABLE TlToolMill (ID GUID PRIMARY KEY, ArborDiameter DOUBLE, MfgToolCode VARCHAR);
CREATE TABLE TlAssembly (
    ID GUID PRIMARY KEY, Name VARCHAR, Description VARCHAR,
    MainHolder GUID, MainTool GUID, ToolNumber INT
);
"""


@dataclass
class ItemSpec:
    manufacturer: str | None = "Northline"
    catalog_id: str | None = "NL-9550"
    name: str | None = ""
    description: str | None = "AXFPS"
    is_metric: bool = False


@dataclass
class AssemblySpec:
    tool_number: int | None = 100
    name: str | None = "TID0001 - .5 ROUGH EM"
    description: str | None = ""
    tool: ItemSpec | None = field(default_factory=ItemSpec)
    holder: ItemSpec | None = field(
        default_factory=lambda: ItemSpec("GRIPWELL", "GW-HYD-12", "", "HYDRO 12")
    )
    manufacturer_code: str | None = "NL-9550"
    shank_diameter: float | None = 0.5


def build_tooldb(path: Path, assemblies: list[AssemblySpec]) -> Path:
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(_SCHEMA)
        manufacturers: dict[str, str] = {}
        for spec in assemblies:
            tool_id = _insert_item(conn, spec.tool, manufacturers)
            holder_id = _insert_item(conn, spec.holder, manufacturers)
            if tool_id is not None:
                conn.execute(
                    "INSERT INTO TlToolMill VALUES (?, ?, ?)",
                    (tool_id, spec.shank_diameter, spec.manufacturer_code),
                )
            conn.execute(
                "INSERT INTO TlAssembly VALUES (?, ?, ?, ?, ?, ?)",
                (_guid(), spec.name, spec.description, holder_id, tool_id, spec.tool_number),
            )
        conn.commit()
    return path


def _insert_item(
    conn: sqlite3.Connection, item: ItemSpec | None, manufacturers: dict[str, str]
) -> str | None:
    if item is None:
        return None
    manufacturer_id = None
    if item.manufacturer is not None:
        if item.manufacturer not in manufacturers:
            manufacturers[item.manufacturer] = _guid()
            conn.execute(
                "INSERT INTO TlManufacturer VALUES (?, ?, '')",
                (manufacturers[item.manufacturer], item.manufacturer),
            )
        manufacturer_id = manufacturers[item.manufacturer]
    item_id = _guid()
    conn.execute(
        "INSERT INTO TlAssemblyItem VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, item.catalog_id, manufacturer_id, item.name, item.description, item.is_metric),
    )
    return item_id


def _guid() -> str:
    return str(uuid.uuid4())
