from toolbom_reader.rows import MAX_TOOLS


class LibraryError(Exception):
    """A tool library is missing, unreadable, or not a supported format."""


class TooManyToolsError(LibraryError):
    def __init__(self, count: int | None = None) -> None:
        shown = f"{count:,} tools" if count is not None else f"more than {MAX_TOOLS:,} tools"
        super().__init__(f"This library has {shown}; the reader handles up to {MAX_TOOLS:,}.")
