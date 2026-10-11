# Building it into your system

Three common ways to put library-to-BOM conversion into a shop's systems, from least to most work. All three use the same rules; they differ in who triggers the conversion and where the result goes.

## 1. A script over a folder

Good for: a nightly import into an ERP or tool crib, or a one-off audit of every library on a share.

```python
from pathlib import Path

from toolbom_reader import LibraryError, read_library, row_issues, rows_csv

for path in sorted(Path(r"\\cam-server\libraries").glob("*.tooldb")):
    try:
        library = read_library(path)
    except LibraryError as error:
        print(f"skipped {path.name}: {error}")
        continue
    path.with_suffix(".bom.csv").write_text(rows_csv(library.rows), encoding="utf-8-sig")
    flagged = [row for row in library.rows if row_issues(row)]
    print(f"{path.name}: {len(library.rows)} tools, {len(flagged)} need attention")
```

Or with no code at all: `toolbom-reader LIBRARY --csv -o LIBRARY.csv` in a scheduled task.

Things to decide:

- **Where flagged rows go.** Don't import a row with no part number into purchasing. Write the `--check` report somewhere a person will see it.
- **What "changed" means.** Libraries are edited all the time. If you import nightly, key your records by brand + part number, not by T number or row position.

## 2. An upload endpoint

Good for: a web tool where programmers or buyers upload a library and get a BOM back.

```python
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from toolbom_reader import LibraryError, combine, read_library

MAX_UPLOAD = 50 * 1024 * 1024
app = FastAPI()


@app.post("/bom")
async def bom(file: UploadFile) -> dict[str, object]:
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Library too large")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "library"  # never the uploaded file name
        path.write_bytes(data)
        try:
            library = await run_in_threadpool(read_library, path)
        except LibraryError:
            raise HTTPException(422, "Not a Mastercam or Fusion tool library") from None
    return {
        "source": library.source,
        "rows": [r.to_dict() for r in library.rows],
        "purchase_lists": combine(library.rows).to_dict(),
    }
```

This sketch shows the shape, not a finished service. Before it faces the internet, go through [SAFETY.md](SAFETY.md). The parts that matter most here:

- **Cap the upload size** at your proxy or server (nginx `client_max_body_size`, for example) as well as in the handler: most frameworks buffer the whole body before your code runs. The reader's own caps protect the parsing, not your disk or memory.
- **Save under a name you choose,** in a temp directory, and delete it when the request ends. Never use the uploaded file name in a path.
- **Run the reader off the request thread,** with a limit on how many run at once, so one slow file can't stall the server.
- **Don't echo file content in errors.** A generic message is enough; log details only where other users can't see them.
- **Don't keep the library.** It's the shop's tooling data. Convert it and throw it away.

## 3. Join to your own item master

Good for: making the BOM better every time it's used.

No library stores quantity, collet, spindle taper or stickout, and most don't store links. But your ERP or tool crib may already know them, keyed by brand + part number. Join the reader's rows to your item master on those two fields and fill in what you know:

| BOM field | Join on | Typical source |
|---|---|---|
| `hyperlink` | tool brand + part number | item master URL, or the vendor's catalog |
| `holder_hyperlink`, `spindle_taper` | holder brand + part number | item master |
| `collet` | holder brand + part number **and** shank | a holder/collet table: the same holder takes a different collet per shank size |
| `quantity` | (job-specific) | the job or the buyer |
| `stickout` | (setup-specific) | the setup sheet |

Normalize before joining: compare brand and part number ignoring case and surrounding spaces, and clean brand spellings first ([BRANDS.md](BRANDS.md)). A join on raw strings will miss `Northline` vs `NORTHLINE`.

When a person fills in a value the join didn't have, save it back keyed the same way. The next BOM with that part fills itself in.

## Whatever you build

- Run [the conformance cases](../conformance/README.md) against your implementation, in your language.
- Keep the [rules](../README.md#building-it-into-your-own-system) in one place. They're easy to get subtly wrong, and two copies drift.
- Surface flagged rows ([BOM.md](BOM.md#values-that-need-a-persons-attention)); don't silently drop them. A tool missing from the BOM is still in the program.
