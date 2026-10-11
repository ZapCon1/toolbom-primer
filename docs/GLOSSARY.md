# Glossary

For developers who haven't worked in a machine shop. These are the terms the rest of the docs use, and the ones you'll hear from the people asking for the integration.

## The physical things

**Cutting tool** (or just **tool**). The part that removes metal: an end mill, drill, tap, reamer, chamfer mill, thread mill or face mill. It wears out, so shops buy it again and again. It has a **brand** (manufacturer) and a **part number** (the manufacturer's catalog number). Those two together identify what to buy.

**Shank.** The plain cylindrical end of the tool that the holder grips. Its **diameter** decides which holder or collet the tool fits, so it's on the BOM. Inch shanks are written as decimals (`0.25`, `0.5`); metric ones in millimetres (`6MM`).

**Holder** (or **tool holder**). What connects the tool to the machine's spindle. One end grips the tool's shank. The other end is the **spindle taper** that locks into the machine. Holders cost far more than most tools and are reused for years. Common kinds:

- **Collet chuck** (ER16, ER32…): grips the shank through a collet, so one holder takes many shank sizes.
- **Hydraulic** or **shrink-fit** chuck: grips one shank size directly, very rigidly.
- **Shell mill arbor**: carries a face mill on a short arbor (`ArborDiameter` in Mastercam, often 0.75", 1", 1.5" or 2.5").

**Collet** (or **sleeve**). A slotted ring that sits inside a collet chuck and squeezes the shank. Each collet fits one shank size, so the same holder needs a different collet for a 6 mm tool than for a 1/4" tool. That's why collets are their own purchase list, keyed by collet part number.

**Spindle taper.** The holder's machine-side shape: `CAT40`, `BT30`, `HSK63A` and so on. A holder only fits machines with the matching spindle. No library format stores it reliably, so a person fills it in.

**Stickout.** How far the tool extends from the holder's face. Longer stickout reaches deeper but deflects more. Programmers care; purchasing usually doesn't. It's on the BOM because setup sheets need it.

**Tool assembly.** One tool in one holder (plus its collet, if any), set up and measured as a unit. **One BOM row is one assembly.**

## The numbers

**T number** (`tool_number`). The pocket number the CNC program calls: `T12` loads assembly 12. It's unique within one machine's setup, not across a shop. The same physical tool can sit at several T numbers in one library (for example, a roughing and a finishing copy), which is why combining lists every T number a part is used at.

**Quantity.** How many of a tool to buy. Libraries don't store it. A blank quantity counts as 1 when combining, because one tool in the library is one physical tool unless someone says otherwise.

## The software

**CAM** (computer-aided manufacturing). The software that turns a part model into toolpaths and CNC programs: Mastercam, Fusion, and many others. Each CAM system keeps a **tool library**: the tools, holders and T numbers a programmer can use.

**Tool library.** Mastercam stores it as a `.tooldb` (a SQLite database). Fusion uses `.tools` (a zip of JSON) or a plain `.json` export. The library is written by programmers for the CAM system, not for purchasing, which is why brand and part number are often missing, misspelled, or stored somewhere surprising.

**BOM** (bill of materials). Here, the list of tools and holders a job or a library needs, in a form purchasing or an ERP can act on. See [BOM.md](BOM.md).

**Purchase list.** The BOM combined so each part appears once with a total quantity. See [COMBINE.md](COMBINE.md).

**ERP / MES / tool crib.** The shop's business systems: ERP for purchasing and inventory, MES for the shop floor, and tool-crib software for issuing and tracking tools. These are the systems most people reading this are integrating with.

## Why the rules are the way they are

- **A wrong part number is worse than a blank one.** A blank gets noticed and filled in. A wrong one gets ordered, arrives a week later, and doesn't fit. So the reader never guesses.
- **Holders count assemblies, tools count quantity.** Buying four spare end mills doesn't mean buying four holders: a holder holds one tool at a time.
- **"Mastercam" isn't a brand.** When nobody entered the real manufacturer, CAM systems fill the brand field with their own name. You can't buy a cutter from Mastercam.
