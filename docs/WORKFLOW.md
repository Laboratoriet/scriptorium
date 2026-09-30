# Workflow — from scan to edition

You don't need to memorise this. `scriptorium next` walks you through it one step at a time. This page is the map
behind it, for when you want to see the whole road or do something out of order.

Run every command inside the book's folder. Record decisions in `STATUS.md`, with dates. **Pilot first:** take one
short chapter all the way through (steps 1–7) before scaling up. That's when conventions are cheap to change.

With Claude, "agent work" below means a subagent working from a brief (`scriptorium brief NAME`) plus the book's
`CONVENTIONS.md`, on a small slice: ≈4 pages to transcribe, one unit to translate. Never an improvised prompt.

---

## 0. Start

`scriptorium new scan.pdf` asks for the title, authors, language and rights, maps printed pages to PDF pages, and
renders page images. Afterwards:

- **Rights** (`book.yaml: rights`). Claude translates books that are public domain, your own work, licensed or used
  with permission. For other books, choose `translation: supplied`: you bring the English (your own, DeepL, a human
  translator) and Scriptorium checks, reviews and publishes it. If an agent declines to translate, don't reword the
  task. Ask the rights holder instead.
- **Page map.** Spot-check three pages across the book: is `source/pages/0100/pdf.png` really printed page 100? An
  off-by-one shifts everything. To redo it: `scriptorium run map_pages 1 <last> <pdf page of p.1> --missing 6,10`.
- **Contents** → `source/toc.yaml`, with English titles in `source/toc_en.yaml`. Each file's header explains the format.
- **Units** → `source/units.yaml`: the chapters as they'll appear on the site, one page each.
- **Conventions** → the book's `CONVENTIONS.md`: heading scheme, numbered items, reference style, figure labels.

## 1. Transcribe (the original)

Agent work, brief `TRANSCRIBE`. Each page becomes `source/pages/NNNN/de.md`: exact text, figure placeholders,
tables, references, and an `uncertain:` list instead of guesses.
Figure-heavy books start with brief `BOXES` (figure regions → `figures.yaml`), checked with
`scriptorium run check_boxes 0012-0040`.

## 2. Join

`scriptorium run join_unit <unit>` joins a unit's pages into `work/<dir>/de.md`, checking page seams and footnotes. Fix
what it reports in the *page* files, then join again. Big units can be split for translation:
`scriptorium run split_parts split work/<dir> "3.1" "3.5"`, then `… merge work/<dir>` afterwards.

## 3. Translate

- `translation: agents`: agent work, brief `TRANSLATE`, one unit (or part) per agent.
- `translation: supplied`: put the English in `work/<dir>/en.md`, laid out like `de.md` (same headings and paragraphs,
  with page anchors and `{{fig:…}}` placeholders copied over).

Then `scriptorium check <unit>`. It must pass: every number, reference, figure and paragraph has to survive the
translation. Legitimate differences (a decimal comma, say) go in `work/<dir>/invariant_exceptions.yaml`, with a reason.

## 4. Review

Agent work: brief `REVIEW` (an independent reader writes `review.md`), then brief `FIX` (a second agent applies it,
logs a `## Resolution`, and reruns the check). Read the resolution. A rejected finding needs a reason you'd accept.

## 5. Figures (optional, per kind)

Until a figure is redrawn, the site shows the original crop with an English label key.
`scriptorium run crop_figures <unit>` crops every figure first.

| Kind | Route | Brief |
|---|---|---|
| Photos, adverts | `upscale_queue` → `upscale_batch` (ImageRouter key in `.env`) → `restored_images`; compare every result with the crop | — |
| Charts | Data read into `figures/charts/<fig>.yaml`; the site draws them | `CHARTS` |
| Simple diagrams | Hand-drawn SVG in `figures/illustrations/<fig>.svg`, in the site's ink colours | — |
| Chemical structures | Two blind readers → `structure_readings` → `verify_compounds` (PubChem) → `render_structures` | `STRUCTURES`, `TWO_READERS` |
| Generic structures (R-groups) | Two blind readers → `compare_generic` | `GENERIC` |
| Schemes, pathways, SAR maps | Two blind readers → `compare_scheme --apply` → you resolve the disagreements | `SCHEMES`, `TWO_READERS` |

The tools run as `scriptorium run <tool>`. Hand-edited specs get `locked: true`. **Never** use generative upscaling on
line art that carries meaning (chemistry, labelled diagrams), because it invents detail.

## 6. References (academic books)

`scriptorium run link_references` finds DOIs through Crossref, with strict matching. Unmatched entries go to agents
(brief `REFERENCES`), and `scriptorium run apply_manual_links` rechecks their proposals before accepting any.

## 7. Publish

```sh
scriptorium build      # the reading site, source and English side by side
scriptorium preview    # opens it in your browser
```
Click through a chapter: contents, figure and reference links, the source-text toggle, search in both languages,
the themes, a phone-width window.

## 8. Proofread

`scriptorium run proofread_list work/<dir>` collects every translator's note into `PROOFREAD.md` for an expert
reader. Their corrections go into `en.md`, followed by `scriptorium check` and `scriptorium build`.

## 9. Share (within the rights)

`scriptorium pdf` (A4), `scriptorium pdf a5`, `scriptorium pdf bilingual` (side by side, for proofreading),
`scriptorium pdf all`, and `scriptorium export` for Markdown.

## 10. Close

`scriptorium status`, a last click-through, and known uncertainties written into `STATUS.md`. Anything that would
help the next book goes back into the kit or `docs/LESSONS.md`.
