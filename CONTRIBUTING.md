# Contributing

Fixes, new traps you've found in a library format, and readers for other CAM systems are welcome.

## The one rule

**Never commit or attach a real tool library**, not even a small one. Libraries can hold a shop's proprietary tooling: which tools it runs, from whom, for which jobs. Describe what you found instead (the table and column, or the JSON path, and what the value looked like), and reproduce it with a synthetic library built by `tests/tooldb_factory.py` or `tests/fusion_factory.py`. Use made-up brands and part numbers.

## Adding a format or a rule

1. Document it first, in `docs/`: where each BOM field comes from, and the traps. The docs are the spec other people implement from; the code is one implementation of it.
2. Implement it in `src/toolbom_reader/`, with no new runtime dependencies.
3. Test it with synthetic files: 0, 1, 2 and many tools, plus one malicious file per defense in [docs/SAFETY.md](docs/SAFETY.md).
4. If the output changes, run `python examples/build_examples.py` and check the diff is what you meant.
5. Add a line to [CHANGELOG.md](CHANGELOG.md).

## Checks

```bash
pip install -e ".[dev]"
pytest
mypy && ruff check . && ruff format --check .
```

CI runs the same on Python 3.12 and 3.14.
