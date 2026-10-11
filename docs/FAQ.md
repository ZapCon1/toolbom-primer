# FAQ

The questions people ask after their first BOM.

### Why is the part number blank?

The library doesn't have one where the reader looks, and the reader never guesses.

- **Mastercam:** the part number is the tool's *Manufacturer's Code* (`TlToolMill.MfgToolCode`), with `CatalogID` as a fallback. If the programmer never filled in either, it's blank. Fill it in Mastercam's tool manager and every later BOM has it.
- **Fusion:** the part number is parsed from the description, `<tool ID> - <BRAND>_<PART> (<spec>)`. A description in any other shape gives a blank. Fusion's own placeholder, "Milling Tool-5 Parameters", always does. Rename the tool in that pattern. (Filling in Fusion's Product ID field gives the part number, but not the brand.)
- **A turning tool in Mastercam:** not supported yet; see [MASTERCAM.md](MASTERCAM.md#turning-tools).

### Why does the shank say `6MM` when Mastercam shows 0.2362?

Mastercam stores every shank in inches, even on metric tools, and usually leaves the metric flag off. 0.23622" is 6 mm, so the reader shows it as `6MM`. A value is treated as metric when it lands on a half-millimetre step and isn't also a 1/64" size. See [the metric shank trap](MASTERCAM.md#the-metric-shank-trap).

### Why is my 1/4" shank still `0.25`, not `6.35MM`?

Because it's an inch tool. 6.35 mm isn't a metric size anyone sells; 0.25" is. Inch shanks stay numbers.

### Why is the same tool on two rows?

Each row is one tool assembly at one T number. If the library has the same end mill at T1 and T2 (say, one for roughing and one for finishing), that's two rows. Use `--combine` (or `combine()` in code) to get one line per part with a total quantity and both T numbers.

### Why didn't two rows for the same tool combine?

Combining matches brand + part number, ignoring case and surrounding spaces. Common reasons it doesn't:

- **The brand is spelled differently** (`NORTHLINE` and `NORHTLINE`). Clean brands first: see [BRANDS.md](BRANDS.md).
- **One row has no part number.** Rows without a part number never merge, on purpose: Fusion's placeholder tools share a description but are different tools.
- **The part numbers really differ** (`NL-1550` and `NL1550`). The reader won't decide those are the same; a person should.

### Why is "Mastercam" flagged as a brand?

Because it isn't one. When nobody entered the real manufacturer, CAM systems fill the brand field with their own name. You can't order a cutter from Mastercam, so the row needs a person to put in the real brand. The same goes for Fusion, Autodesk, hyperMILL and other CAM systems.

### Why aren't quantity, collet, spindle taper and stickout filled in?

No library format stores them reliably. Plan for a person to fill them in, or join them from your own item master. See [INTEGRATION.md](INTEGRATION.md#3-join-to-your-own-item-master).

### Why is the holder blank?

The assembly has no holder assigned in the library, or the holder has no brand or part number. In Fusion, the holder's identity comes from its description in the form `<BRAND>_<PART>`.

### My library is rejected as "not readable" or "not a tool library". Why?

- It may not be a Mastercam `.tooldb` or a Fusion `.tools`/`.json` file. The reader decides by the file's content, not its name.
- It may be from an older Mastercam that used a different format. See [VERSIONS.md](VERSIONS.md).
- It may trip a safety check: more than 5,000 tools, a JSON document much larger than any real library, or a database with views or computed columns where plain tables should be. See [SAFETY.md](SAFETY.md).

If you think it's a real library that should work, open an issue describing it. **Don't attach the library:** it can hold your shop's proprietary data.

### Can I use this commercially?

Yes. It's MIT licensed: use it, change it and ship it, keeping the license notice.
