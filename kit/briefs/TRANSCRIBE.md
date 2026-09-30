# Transcription brief (phase 1) — read fully before starting

Context: see the book's `book.yaml` and `CLAUDE.md` (title, source language, ownership, privacy). Your job: turn page
images into **verified source-language Markdown**. Accuracy is paramount — the text is translated next and proofread
by an expert; every OCR error you miss propagates.

Book root: the folder with `book.yaml` (given in your task).

## Before you start
1. Read `scriptorium brief CONVENTIONS` (section "`source/pages/NNNN/de.md`") and the book's `CONVENTIONS.md`; follow both.
2. Study the verified example pages the task names (a text page, a table, a reference list, a figure page).
3. Look up the chapter/section titles in your range in `source/toc.yaml` — headings use that exact wording.

## For each page NNNN
- Read `source/pages/NNNN/pdf.png` (primary) and `ocr_old.txt` if present (old OCR is a hint only: it drops diacritics,
  italics, sub-/superscripts, and has **silently dropped whole tables and reference entries** before).
- **Zoom** into anything small or uncertain with a 300 dpi crop:
  `pdftoppm -f <pdf_page> -l <pdf_page> -r 300 -x <X> -y <Y> -W <W> -H <H> -png source/<source_pdf> <scratch>/crop`
  (PDF page = `source/book_to_pdf.json["NNNN"]`; 300 dpi coords = 2× the pdf.png pixel coords). Crops go only to your
  scratchpad. Zoom generously: numbers, units, labels, names with diacritics, every reference entry, table cells.
- Write `source/pages/NNNN/de.md` per the conventions: placeholders for every figure (bbox in front matter, captions,
  `compounds: [...]`, `labels: [...]`), bold item numbers, tables cell by cell, one reference per line, page-break
  state describing the **text flow**, the authors' own spelling kept, `⟦?⟧` + `uncertain:` instead of guessing.
- Pages the manifest marks as blank (`source/page_manifest.json`) aren't photographed; a page before one usually ends a
  section.

## Figure boxes that already exist
If `source/pages/NNNN/figures.yaml` exists (the figure-box pass), reuse its ids and `bbox_pct` values; its `table`
entries are not figures (tables stay Markdown).

## Don't
Modify any file other than your pages' `de.md`. Translate.

## Final report (short)
Per page: figures/tables/references counts, ⟦?⟧ items, notable OCR corrections. Then every numbered item seen in
figures with the name printed under it, and any **inconsistency in the original** (text vs. figure numbering, wrong
cross-references, apparent slips) — these become translator's notes.
