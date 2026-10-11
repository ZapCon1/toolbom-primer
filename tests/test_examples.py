"""The committed examples are what the reader produces from the example libraries.

If this fails after a deliberate change to the reader, rebuild them with
`python examples/build_examples.py` and review the diff.
"""

from pathlib import Path

import pytest

from toolbom_reader import read_library
from toolbom_reader.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"
LIBRARIES = ["mastercam-example.tooldb", "fusion-example.tools"]
OUTPUTS = [
    ("bom.json", []),
    ("purchase-lists.json", ["--combine"]),
    ("bom.csv", ["--csv"]),
    ("check.txt", ["--check"]),
]


@pytest.mark.parametrize("library", LIBRARIES)
@pytest.mark.parametrize(("suffix", "flags"), OUTPUTS)
def test_committed_example_output_is_current(
    tmp_path: Path, library: str, suffix: str, flags: list[str]
) -> None:
    path = EXAMPLES / library
    out = tmp_path / f"out.{suffix}"
    assert main([str(path), *flags, "-o", str(out)]) == 0
    expected = EXAMPLES / f"{path.stem}.{suffix}"
    assert out.read_bytes() == expected.read_bytes()


def test_examples_cover_the_traps_the_docs_describe() -> None:
    mastercam = {row.tool_number: row for row in read_library(EXAMPLES / LIBRARIES[0]).rows}
    assert mastercam[1].shank == "6MM"  # metric stored in inches, IsMetric off
    assert mastercam[3].shank == 0.25  # inch stays a number
    assert mastercam[10].shank == 2.5  # on the metric grid, but an inch size
    assert mastercam[12].brand == "Mastercam"  # CAM placeholder brand
    fusion = {row.tool_number: row for row in read_library(EXAMPLES / LIBRARIES[1]).rows}
    assert (fusion[2].brand, fusion[2].part_number) == ("Blue Ridge", "32257")
    assert (fusion[4].brand, fusion[4].part_number) == ("", "")  # placeholder, never guessed
