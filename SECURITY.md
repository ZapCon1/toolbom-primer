# Security

`toolbom_reader` is meant to read tool libraries from people you don't trust. [docs/SAFETY.md](docs/SAFETY.md) lists the attacks it defends against. If you find a file that gets past one of them, please report it privately. That includes a file that runs a computation, uses unbounded memory or time, crashes the reader with something other than `LibraryError`, or puts something dangerous in the output.

**GitHub → this repository → Security → Report a vulnerability.**

Please don't open a public issue, and don't attach a real customer library: describe the file, or attach a synthetic one built with the factories in `tests/`. Fixes go into the next release and are noted in [CHANGELOG.md](CHANGELOG.md).

Only the latest release is supported.
