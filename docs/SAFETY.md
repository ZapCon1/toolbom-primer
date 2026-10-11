# Reading library files safely

If your system accepts tool libraries from users, by upload, email or a shared folder, treat every file as hostile until it has been read. Both formats have well-known ways to hurt a naive reader. The reference reader defends against all of the following, and the tests prove each defense.

## Mastercam `.tooldb` (SQLite)

| Attack | What it does | Defense |
|---|---|---|
| Schema-embedded functions | Views, triggers and default expressions run when rows are read | Open read-only (`?mode=ro`); `PRAGMA trusted_schema=OFF` |
| Generated or virtual columns | A column named `Name` defined as `printf('%.*c', 200000000, 'x')` builds 200 MB per row | Require the four tables to be plain tables, and reject any generated column (`PRAGMA table_xinfo`, hidden ≠ 0) **before** selecting |
| Repeated IDs | 3,000 assemblies × 3,000 items sharing one `ID` make the joins explode | Check `GROUP BY ID HAVING count(*) > 1` on each joined table first |
| Huge values | One stored string of hundreds of MB | `sqlite3.setlimit(SQLITE_LIMIT_LENGTH, 100_000)` |
| Slow queries | Anything that still runs long | A progress handler that aborts after a deadline (3 s; a real 5,000-tool library reads in well under 1 s) |
| Too many rows | Memory and time grow with the row count | `LIMIT max + 1` and refuse past the max |

## Fusion `.tools` (zip of JSON)

| Attack | What it does | Defense |
|---|---|---|
| Zip bomb | A few KB inflates to gigabytes | Check `ZipInfo.file_size` before reading (40 MB cap). Python's `zipfile` stops at the declared size, so a lying header can't get past it. |
| JSON bomb | A few MB of `{},{},…` parses into millions of objects | Before parsing, count `{` + `[` (cap 200,000) and `,` (cap 820,000) in the raw bytes. A real library averages ~28 containers and ~117 commas per tool, so the caps leave ~40% headroom over 5,000 real tools. |
| Deep nesting | Stack exhaustion in the parser | Catch `RecursionError` as "not a library" |
| Huge integers | `1` followed by 100,000 digits takes quadratic time to convert | Catch `ValueError` (Python's int-string limit) |
| Wrong types everywhere | `"number": true`, `"geometry": []` | Read every field defensively. Anything not the expected type counts as blank. |

## Both formats

- **Detect the format from content, not the extension.** Renamed files are normal and so are wrong extensions.
- **Clean the output.** Strip control characters (spreadsheets refuse them), cap text lengths, and drop impossible numbers (non-finite shanks, negative tool numbers).
- **Process in a temp directory and delete the file afterwards.** Tool libraries can hold a shop's proprietary data, so don't keep them longer than the request.
- **Never echo file content in error messages** shown to other users or written to shared logs.
- **Run the reader off your request thread** (a worker pool) with a concurrency limit, so a slow file can't stall the rest of your service.
