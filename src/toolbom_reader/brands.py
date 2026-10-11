"""Find one manufacturer spelled several ways in a library.

"NORTHLINE", "Northline" and "NORHTLINE" in one library split rows that are
really one part, so combining can't merge them. This module only *suggests*
merges: a person decides, because two short names one letter apart are often
two companies. See docs/BRANDS.md.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from toolbom_reader.rows import BomRow

# Near-match only names this long: short names one letter apart ("OSG"/"OSK")
# are too often different companies.
MIN_NEAR_MATCH_LENGTH = 5
# Real brands have a handful of spellings. A one-letter-deleted variant shared by
# more names than this isn't a typo cluster, and comparing them all would cost
# the square of their number.
_MAX_SHARED_VARIANT = 50


@dataclass(frozen=True)
class BrandSuggestion:
    spellings: tuple[str, ...]  # as written in the library, most used first
    reason: Literal["case", "spelling"]  # only capitalization differs, or a letter does


def brand_suggestions(rows: Sequence[BomRow]) -> list[BrandSuggestion]:
    """Groups of tool and holder brand spellings that are probably one manufacturer."""
    counts = Counter(
        name.strip() for row in rows for name in (row.brand, row.holder_brand) if name.strip()
    )
    return suggest(counts)


def suggest(counts: Counter[str]) -> list[BrandSuggestion]:
    """Like brand_suggestions, from spellings and how often each is used."""
    by_key: dict[str, list[str]] = {}
    for name in counts:
        by_key.setdefault(_normalize(name), []).append(name)
    keys = list(by_key)
    parent = list(range(len(keys)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in _near_match_candidates(keys):
        if edit_distance(keys[a], keys[b]) == 1:
            parent[find(b)] = find(a)

    components: dict[int, list[str]] = {}
    for index, key in enumerate(keys):
        components.setdefault(find(index), []).append(key)
    suggestions = []
    for members in components.values():
        spellings = sorted(
            (name for key in members for name in by_key[key]),
            key=lambda name: (-counts[name], not name.isupper(), name),
        )
        if len(spellings) > 1:
            reason: Literal["case", "spelling"] = "spelling" if len(members) > 1 else "case"
            suggestions.append(BrandSuggestion(tuple(spellings), reason))
    return sorted(suggestions, key=lambda s: -sum(counts[name] for name in s.spellings))


def edit_distance(a: str, b: str) -> int:
    """Insertions, deletions, substitutions and swaps of neighbouring letters."""
    previous2: list[int] = []
    previous = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        current = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                current[j] = min(current[j], previous2[j - 2] + 1)
        previous2, previous = previous, current
    return previous[len(b)]


def _near_match_candidates(keys: Sequence[str]) -> Iterable[tuple[int, int]]:
    """Pairs (by index) that might be one edit apart, without comparing every pair.

    Keys one edit apart always share a delete-one-letter variant: a substitution
    or a swap deletes to the same string, and an insertion's shorter key is a
    variant of the longer. Sharing one doesn't prove it, so callers confirm.
    """
    by_variant: dict[str, list[int]] = {}
    for index, key in enumerate(keys):
        if len(key) < MIN_NEAR_MATCH_LENGTH:
            continue
        variants = {key} | {key[:i] + key[i + 1 :] for i in range(len(key))}
        for variant in variants:
            by_variant.setdefault(variant, []).append(index)
    seen: set[tuple[int, int]] = set()
    for members in by_variant.values():
        if len(members) > _MAX_SHARED_VARIANT:
            continue
        for x, a in enumerate(members):
            for b in members[x + 1 :]:
                pair = (min(a, b), max(a, b))
                if pair not in seen:
                    seen.add(pair)
                    yield pair


def _normalize(name: str) -> str:
    return name.strip().upper()
