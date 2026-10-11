"""Read a Mastercam tool library (.tooldb) as BOM rows.

A .tooldb is a SQLite database. Each `TlAssembly` row is one numbered tool in
its holder; `MainTool` and `MainHolder` point at `TlAssemblyItem` rows that
carry each component's catalog identity. See docs/MASTERCAM.md.
"""

import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from toolbom_reader.errors import LibraryError, TooManyToolsError
from toolbom_reader.rows import MAX_TOOLS, BomRow, format_shank

# A real 5,000-tool library reads in well under a second; this only stops
# crafted files from running forever.
QUERY_TIME_LIMIT_S = 3.0
# No text value the reader selects comes close; a crafted file could otherwise
# make SQLite build a huge string inside one call.
MAX_SQLITE_VALUE_BYTES = 100_000
_REQUIRED_TABLES = frozenset({"TlAssembly", "TlAssemblyItem", "TlManufacturer", "TlToolMill"})
# Tables the query joins on ID: one row per ID, or the joins multiply.
_JOINED_BY_ID = ("TlAssemblyItem", "TlManufacturer", "TlToolMill")

# Component names carry an internal ID prefix: 'CID0001 - .5" X ...'.
_COMPONENT_ID_PREFIX = re.compile(r"^CID\d+\s*-?\s*")

ASSEMBLY_QUERY = """
SELECT
    a.ToolNumber       AS tool_number,
    a.Name             AS name,
    ti.ID              AS tool_id,
    tm.Name            AS tool_manufacturer,
    ti.CatalogID       AS tool_catalog_id,
    ti.Name            AS tool_name,
    ti.IsMetric        AS tool_is_metric,
    hi.ID              AS holder_id,
    hm.Name            AS holder_manufacturer,
    hi.CatalogID       AS holder_catalog_id,
    hi.Description     AS holder_description,
    mill.MfgToolCode   AS manufacturer_code,
    mill.ArborDiameter AS shank_diameter
FROM TlAssembly a
LEFT JOIN TlAssemblyItem ti ON ti.ID = a.MainTool
LEFT JOIN TlManufacturer tm ON tm.ID = ti.TlManufacturerID
LEFT JOIN TlAssemblyItem hi ON hi.ID = a.MainHolder
LEFT JOIN TlManufacturer hm ON hm.ID = hi.TlManufacturerID
LEFT JOIN TlToolMill mill ON mill.ID = a.MainTool
ORDER BY a.ToolNumber IS NULL, a.ToolNumber, a.Name
LIMIT ?
"""


def read_rows(path: Path) -> list[BomRow]:
    """One row per tool assembly, ordered by tool number. The file is opened read-only."""
    if not path.is_file():
        raise LibraryError(f"Tool library not found: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    try:
        # closing(): `with connect()` alone leaves the file open (and locked on Windows).
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            _harden(conn)
            conn.row_factory = sqlite3.Row
            _check_schema(conn, path)
            _check_unique_ids(conn, path)
            found = conn.execute(ASSEMBLY_QUERY, (MAX_TOOLS + 1,)).fetchall()
    except sqlite3.DatabaseError as error:
        raise LibraryError(f"Not a readable tool library: {path} ({error})") from error
    if len(found) > MAX_TOOLS:
        raise TooManyToolsError()
    return [_to_row(row) for row in found]


def _to_row(row: sqlite3.Row) -> BomRow:
    has_tool = row["tool_id"] is not None
    has_holder = row["holder_id"] is not None
    number = row["tool_number"]
    shank = row["shank_diameter"]
    return BomRow(
        brand=_text(row["tool_manufacturer"]) if has_tool else "",
        # "Manufacturer's Code" (TlToolMill.MfgToolCode) is the vendor part number;
        # CatalogID is usually empty.
        part_number=_text(row["manufacturer_code"])
        or (_text(row["tool_catalog_id"]) if has_tool else ""),
        description=_COMPONENT_ID_PREFIX.sub("", _text(row["tool_name"]))
        if has_tool
        else _text(row["name"]),
        shank=format_shank(
            float(shank) if isinstance(shank, int | float) else None,
            flagged_metric=bool(row["tool_is_metric"]) if has_tool else False,
        ),
        tool_number=number if isinstance(number, int) else None,
        holder_brand=_text(row["holder_manufacturer"]) if has_holder else "",
        holder_part_number=_text(row["holder_catalog_id"]) if has_holder else "",
        holder_description=_text(row["holder_description"]) if has_holder else "",
    )


def _harden(conn: sqlite3.Connection) -> None:
    """Defenses for opening a database someone else made.

    trusted_schema=OFF stops functions embedded in the schema (views, triggers,
    defaults) running with side effects; the progress handler aborts a query
    that runs past QUERY_TIME_LIMIT_S.
    """
    conn.execute("PRAGMA trusted_schema=OFF")
    conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_SQLITE_VALUE_BYTES)
    deadline = time.monotonic() + QUERY_TIME_LIMIT_S
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1_000)


def _check_schema(conn: sqlite3.Connection, path: Path) -> None:
    # Plain tables only: a view, virtual table or generated column can run an
    # arbitrary computation behind an innocent name every time a row is read.
    tables = {
        name: sql or ""
        for (name, sql) in conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'")
    }
    missing = sorted(_REQUIRED_TABLES - tables.keys())
    if missing:
        raise LibraryError(
            f"Not a Mastercam tool library: {path} (missing tables: {', '.join(missing)})"
        )
    for table in sorted(_REQUIRED_TABLES):
        if tables[table].lstrip().upper().startswith("CREATE VIRTUAL"):
            raise LibraryError(f"Not a Mastercam tool library: {path} ({table} is virtual)")
        # table_xinfo's "hidden" column is 2 or 3 for generated columns.
        if any(row[6] != 0 for row in conn.execute(f'PRAGMA table_xinfo("{table}")')):
            raise LibraryError(
                f"Not a Mastercam tool library: {path} ({table} has computed columns)"
            )


def _check_unique_ids(conn: sqlite3.Connection, path: Path) -> None:
    """Reject repeated IDs: they'd make every join multiply the rows."""
    for table in _JOINED_BY_ID:
        query = f'SELECT EXISTS (SELECT 1 FROM "{table}" GROUP BY ID HAVING count(*) > 1)'
        if conn.execute(query).fetchone()[0]:
            raise LibraryError(f"Not a Mastercam tool library: {path} ({table} repeats IDs)")


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
