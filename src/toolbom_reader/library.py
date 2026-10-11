"""Pick the reader for a tool library by its content, not its file extension."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from toolbom_reader import fusion, mastercam
from toolbom_reader.errors import LibraryError
from toolbom_reader.rows import BomRow, clean_row

_SQLITE_MAGIC = b"SQLite format 3\x00"  # Mastercam .tooldb
_ZIP_MAGIC = b"PK\x03\x04"  # Fusion .tools
_UTF8_BOM = b"\xef\xbb\xbf"  # Windows editors prepend this to saved .json

Source = Literal["mastercam", "fusion"]
# Enough for every signature (the SQLite one is the longest).
HEAD_BYTES = len(_SQLITE_MAGIC)


@dataclass(frozen=True)
class Library:
    source: Source
    rows: list[BomRow]

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "rows": [row.to_dict() for row in self.rows]}


def read_library(path: str | Path) -> Library:
    """BOM rows from a Mastercam .tooldb or a Fusion .tools/.json library."""
    path = Path(path)
    if not path.is_file():
        raise LibraryError(f"Tool library not found: {path}")
    with path.open("rb") as file:
        head = file.read(HEAD_BYTES)
    source = detect_format(head)
    if source is None:
        raise LibraryError(
            f"Unrecognized tool library: {path} (expected a Mastercam .tooldb or Fusion .tools)"
        )
    rows = mastercam.read_rows(path) if source == "mastercam" else fusion.read_rows(path)
    return Library(source, [clean_row(row) for row in rows])


def detect_format(head: bytes) -> Source | None:
    """Which reader a file needs, from its first HEAD_BYTES bytes; None if neither."""
    if head.startswith(_SQLITE_MAGIC):
        return "mastercam"
    if head.startswith(_ZIP_MAGIC) or head.removeprefix(_UTF8_BOM).lstrip().startswith(b"{"):
        return "fusion"
    return None
