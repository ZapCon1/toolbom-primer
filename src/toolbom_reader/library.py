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
        head = file.read(len(_SQLITE_MAGIC))
    source: Source
    if head.startswith(_SQLITE_MAGIC):
        source, rows = "mastercam", mastercam.read_rows(path)
    elif head.startswith(_ZIP_MAGIC) or head.removeprefix(_UTF8_BOM).lstrip().startswith(b"{"):
        source, rows = "fusion", fusion.read_rows(path)
    else:
        raise LibraryError(
            f"Unrecognized tool library: {path} (expected a Mastercam .tooldb or Fusion .tools)"
        )
    return Library(source, [clean_row(row) for row in rows])
