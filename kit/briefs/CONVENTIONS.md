# Conventions (kit core)

Rules every pipeline step follows, for every book. A book adds its own rules in its `CONVENTIONS.md` (heading scheme,
special markup, content policy) — **the book's file wins where they differ**. Change a rule here or there first, then
the scripts.

Terms: **source** = the original language (`book.yaml: source.code`, e.g. `de`), **target** = English. For historical
reasons the files are named `de.md` (verified source transcription) and `en.md` (translation) whatever the source
language is.

## `source/pages/NNNN/de.md` — verified transcription, one file per printed page (phase 1)

Transcribed from `pdf.png` (150 dpi render), with 300 dpi crops for anything small or uncertain, and `scan.jpg` /
`ocr_old.txt` as cross-checks if they exist.

- **Exact source text.** Correct OCR errors (diacritics, ß, Greek letters, ®), never the authors' wording or spelling.
- **Skip running headers and page numbers** — they go in the front matter only.
- **Join lines within a paragraph**; undo end-of-line hyphenation, keep real hyphens.
- **Page-break state:** a page starting mid-sentence begins with `…` and `continues_from_previous: true`; a page
  ending mid-sentence sets `continues_on_next: true`. It describes the **text flow**: a page that ends with a complete
  sentence followed by a figure does not continue.
- **Headings** as Markdown with their printed number (`## 2.3.1. Title`); `#` only for top-level titles, worded exactly
  as in `source/toc.yaml`. Unnumbered sub-headings and boxed headings are `##`.
- **Numbered items the book refers to by number** (compounds, equations, cases …): bold `**12a**`; ranges
  `**100**–**103**`. **Reference markers** `[42]` exactly as printed.
- **Sub/superscripts** `<sub>`/`<sup>`; **italics** `*…*`; bold run-in lead words stay inline `**…**`.
- **Figures:** a placeholder where they appear, bounding box in the front matter:
  `{{fig:p0049-1 | kind: structure | label: "Abb. 1" | caption: "…" | compounds: [1, 2] | labels: ["…"]}}`
  `kind`: `structure`, `scheme`, `chart`, `diagram`, `photo`, `advert`, `table-image`. Captions exact; schemes, charts
  and diagrams also list every printed text in `labels:`.
- **Tables** as Markdown tables, every cell exact. **Literature:** one entry per line, exactly as printed.
- **Footnotes:** marker as printed; the text at the end of the page after `---`. Table footnotes under their table.
- **Dashes:** en dash for ranges, as printed. **Unreadable:** `⟦?⟧` plus an `uncertain:` entry — never guess silently.

Front matter:
```yaml
---
page: 49
pdf_page: 67
running_header: "2. Chapter title"
continues_from_previous: false
continues_on_next: true
figures:
  - {id: p0049-1, bbox_pct: [x0, y0, x1, y1]}   # % of page width/height, from pdf.png
uncertain: []
---
```

## `work/<unit>/en.md` — the translation (phase 3)

Translated from the joined `work/<unit>/de.md`. Terms follow `glossary.yaml`.

- **Complete and faithful.** Every sentence; nothing summarised, merged, added or "improved". Where the source is
  ambiguous or seems wrong: translate as written and add `<!-- TN: … -->` (translator's note) on the same line.
- **Structure mirrors the source 1:1:** same headings (numbers unchanged), same paragraphs in the same order, same
  placeholders, page anchors `<!-- p.N -->` in the same positions, same footnote refs.
- **Keep untouched:** bold item numbers, reference markers, `{{fig:…}}` placeholders (translate only `caption:` and
  `labels:`), page anchors, `<sub>`/`<sup>` contents, brand names, numbers and units exactly as written.
- **Quotes already in English** stay verbatim; a source-language translation of them is dropped with a TN.
- **Titles of source-language works** in running text: keep the title, add an English translation in [brackets].
- **Literature lists:** copied verbatim; the book's own editorial words (e.g. "personal communication", "eds.",
  "and" between names) become English; problems in an entry get a TN at the end of its line.
- **Emphasis** carries over to the matching English words (also letter games that spell a name).
- American English, academic register; cross-references lowercase mid-sentence ("see chapter 3.5").

## Invariants (checked by `check_invariants`)
Between source and English these must match exactly, as sets and counts: numbers with units, bold item numbers,
reference markers, figure placeholders, page anchors, sub/superscript values. Legitimate differences (a decimal comma,
"100mal" → "100-fold") go in `work/<unit>/invariant_exceptions.yaml` with a reason — never bend the English and never
hide a number in a TN.

## Omitted passages (only if the book's policy asks for it)
A book may decide to leave passages out (policy in its own CONVENTIONS.md). Then: `{{omitted: <reason> | pages: N |
note: "…"}}` in both files in place of the passage, and `omissions_report` keeps the register (`OMISSIONS.md`).
Without such a policy: nothing is omitted.
