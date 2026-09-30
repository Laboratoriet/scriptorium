# Figure-box brief (phase 1a) — record where figures and tables are on a page

You mark the regions of figures and tables on book pages so they can be cropped before the page is transcribed. You do **not** transcribe text. Precision matters: a box that cuts off part of a structure, a compound number or a table column makes the crop useless.

Book root: the folder with `book.yaml` (run commands from there).

## Input
A list of page numbers (in your prompt). For each page NNNN: `source/pages/NNNN/pdf.png` (the page photo). Use the Read tool on it. Zoom into edges when unsure: crop with Pillow into your scratchpad and Read that.

## Output
`source/pages/NNNN/figures.yaml` — a YAML list, in **reading order** (top to bottom; left before right when side by side):

```yaml
- {id: p0460-1, kind: structure, bbox_pct: [8.5, 31.0, 91.0, 52.5]}
- {id: p0460-t1, kind: table, bbox_pct: [7.0, 55.0, 93.0, 88.0]}
- {id: p0460-2, kind: advert, bbox_pct: [10.0, 12.0, 90.0, 80.0], note: "toothpaste ad, 1950s"}
```

- **id:** figures `p<NNNN>-<k>` (k = 1, 2, … over all non-table figures on the page); tables `p<NNNN>-t<k>` (k counts tables separately).
- **kind:** `structure` (one or more molecules with compound numbers) · `scheme` (reaction/synthesis, arrows) · `photo` (photograph, drawing, painting, packaging, magazine cover) · `advert` (advertisement) · `chart` (bar/line/scatter data plot) · `diagram` (schematic, flow, receptor/brain diagram, overview map) · `table` (a table of text/numbers, including its title line ("Table n." in the source language) and its footnotes directly below).
- **bbox_pct:** `[x0, y0, x1, y1]` in **percent of the page image** (0–100), x to the right, y down. **Percent, not fractions** (`8.5`, never `0.085`). Figures include everything that belongs to the drawing: compound numbers and names under structures, axis labels, legends, labels inside the figure. They do not include the running caption paragraph ("Fig. 3. …") — except for `advert`/`photo`, where a credit line inside the frame is included. Leave ~0.5% air on every side.
- **note:** for `photo` and `advert` only — a few words on what it shows (these go on an upscaling list).
- A page with no figures and no tables: write `[]`.
- Running headers, page numbers, decorative rules and marginal bars are **not** figures.

## Pages that are already transcribed
If your prompt says "tables only" for a page, `source/pages/NNNN/de.md` exists and its figures already have boxes: record **only the tables** (`p<NNNN>-t<k>`), nothing else.

## Check (required)
After writing a few pages, run:
```
scriptorium run check_boxes 0460 0461 0462      # or a range: 0460-0480
```
It reports format problems and writes `work/boxes/preview/NNNN.png` (page with boxes outlined) and one crop per box (`work/boxes/preview/<id>.png`, exactly as it will be cut). **Look at every crop**: nothing cut off at any edge (structure bonds, NH₂ at the right end, compound numbers below, table columns, footnotes), and no neighbouring paragraph included unnecessarily. Fix and re-run until clean.

## Don't
- Don't create or modify `de.md` files, or any file other than the `figures.yaml` of your pages (and scratch files).
- Don't skip a page silently: a page whose `pdf.png` is missing or unreadable goes in your final report.

## Final report (your reply)
Short: pages done, counts per kind, the list of `photo`/`advert` ids with their notes, and anything odd (pages that look out of order, damaged photos, figures spanning two pages).
