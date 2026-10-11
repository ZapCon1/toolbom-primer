# Cleaning up brand spellings

Libraries are typed by people over years, so one manufacturer often appears several ways: `NORTHLINE`, `Northline`, `NORHTLINE`. Combining matches brand + part number, so every spelling splits a part that should be one purchase line. The same goes for any join to your item master.

## Suggest, don't decide

Two names one letter apart are usually a typo. Sometimes they're two companies. So the rule is: **find likely duplicates automatically, and let a person decide.** Never merge brands on your own.

## What counts as a likely duplicate

| Reason | Rule | Example |
|---|---|---|
| `case` | Same letters, different capitalization or surrounding spaces | `NORTHLINE`, `Northline`, ` NORTHLINE` |
| `spelling` | Names of **5 or more** letters, **one edit** apart (a letter added, removed or changed, or two neighbouring letters swapped) | `KESTREL` / `KESTERL`, `GRIPWELL` / `GRIPWEL` |

Details that matter:

- **Short names are left alone.** `APEX` and `APEC` are one letter apart and could easily be different companies. Five letters is where typos start to outnumber real look-alikes.
- **Compare after upper-casing and trimming,** so `Northline` and `NORTHLINE ` are the same name before anything else runs.
- **Near matches chain.** If A is one edit from B and B from C, all three are one suggestion, because a person will want to see them together.
- **Look at tool and holder brands together.** A holder maker's name is often misspelled the same way as a tool maker's.
- **Order spellings by use,** most rows first. Ties go to the all-caps spelling, then alphabetical. The first is a sensible default name, but let the person choose any name, including one not in the list.

## Doing it fast

Comparing every pair of brands costs the square of their number, and a hostile or messy library can have thousands. Instead, index every name by each of its **delete-one-letter variants** (plus the name itself). Two names one edit apart always share at least one variant: a changed or swapped letter deletes to the same string, and an inserted letter's shorter name is a variant of the longer. Only compare names that share a variant, and confirm with a real edit distance (one that counts a swap of neighbours as one edit).

Skip any variant shared by more than about 50 names. Real brands have a handful of spellings; a crowd that size is generated data, and comparing it would be slow.

## Keeping the decisions

Once someone says `NORHTLINE` is `NORTHLINE`, remember it, keyed by the upper-cased spelling, and apply it to every later library **before** combining or joining to your item master. Remember the suggestions they rejected too, so they aren't asked again.

Reference: [`src/toolbom_reader/brands.py`](../src/toolbom_reader/brands.py) (`brand_suggestions`). It only suggests; keeping the decisions is up to your system. Test cases: [`conformance/cases.json`](../conformance/cases.json) (`brand_suggestions`).
