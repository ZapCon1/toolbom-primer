# Conformance cases

[`cases.json`](cases.json) holds input and expected output for every rule in the docs. It's plain JSON, so you can load it from C#, JavaScript, Go or anything else and run your own implementation against the same cases the Python reader passes ([`tests/test_conformance.py`](../tests/test_conformance.py)).

The cases were written from the docs, not generated from the code. When the two disagree, that's a bug in one of them, and it's worth an issue.

## Groups

| Group | Your function takes | It returns | Spec |
|---|---|---|---|
| `format_detection` | the file's first bytes (`first_bytes_hex`, hex-encoded; 16 bytes is enough) | `"mastercam"`, `"fusion"`, or `null` | [README](../README.md#building-it-into-your-own-system) |
| `tool_description` | a Fusion tool `description` and its `vendor` | `brand`, `part_number`, `spec` | [FUSION.md](../docs/FUSION.md) |
| `holder_description` | a Fusion holder `description` | `brand`, `part_number` | [FUSION.md](../docs/FUSION.md) |
| `shank` | the stored value and whether the library flags it metric | a number (inches), `"<n>MM"`, or `null` | [MASTERCAM.md](../docs/MASTERCAM.md#the-metric-shank-trap) |
| `row_issues` | a row | the issue kinds, in order | [BOM.md](../docs/BOM.md#values-that-need-a-persons-attention) |
| `combine` | a list of rows | tool, holder and collet lists | [COMBINE.md](../docs/COMBINE.md) |
| `csv_cell` | one value | the text to write in a CSV cell | [BOM.md](../docs/BOM.md#csv) |
| `brand_suggestions` | the brand of each row | groups of spellings, most used first | [BRANDS.md](../docs/BRANDS.md) |

## Reading a case

- Every case has a `name` saying what it checks. Use it as the test name.
- A `row` lists only the fields that case needs. Fill the rest in as blank: `""` for text, `null` for `shank`, `tool_number`, `quantity` and `stickout`.
- Numbers compare as numbers: `2.5` and `2.50` are the same expected shank.
- `combine` expects every field of every line, in the order lines first appear.

## Running them

Python (this repo):

```bash
pytest tests/test_conformance.py
```

Elsewhere, the loop is the same in any language. In JavaScript or TypeScript:

```javascript
// Vitest or Jest
import cases from "./conformance/cases.json";

describe("shank", () => {
  for (const c of cases.shank) {
    test(c.name, () => expect(formatShank(c.stored, c.flagged_metric)).toEqual(c.expected));
  }
});
```

`version` at the top changes only when a case's meaning changes, not when cases are added.
