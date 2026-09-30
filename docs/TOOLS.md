# Tools

The everyday commands (`new`, `next`, `check`, `build`, …) run these for you. To run one directly, use
`scriptorium run <tool> …` inside a book. Each tool's docstring (the first lines of `kit/scripts/<tool>.py`) is its
manual. Tools find the book through `book.yaml`, from `$BOOK_ROOT` or by searching upward from the current folder.

## Scripts

**Setup and source**
| Script | Does |
|---|---|
| `sync_book` | Carries `book.yaml` into `site/src/book.json` and the CLAUDE.md placeholders. |
| `map_pages` | Printed page → PDF page (`source/book_to_pdf.json`), plus the scanned/blank manifest. |
| `render_pages` | Renders pages at 150 dpi → `source/pages/NNNN/pdf.png`. |
| `check_boxes` | Validates figure/table boxes and renders every crop for a visual check. |
| `crop_figures` | Crops a unit's figures → `figures/<dir>/<fig>_orig.png`. |

**Text**
| Script | Does |
|---|---|
| `join_pages` / `join_unit` | Joins verified pages into `work/<dir>/de.md`, checking seams, footnotes and blank pages. |
| `split_parts` | Splits a big unit into translation parts, then merges them back. |
| `check_invariants` | Source vs English: numbers, item numbers, references, placeholders, anchors, paragraph count. |
| `check_references` | Each reference list against the citations before it. |
| `proofread_list` | Every TN of a unit → `PROOFREAD.md` for the expert reader. |
| `omissions_report` | Register of `{{omitted: …}}` passages → `OMISSIONS.md` (books with an omission policy). |
| `coverage` | Progress table per unit (for `STATUS.md`). |

**References**
| Script | Does |
|---|---|
| `link_references` | Finds DOIs through Crossref with strict matching → `work/<dir>/references.yaml`. |
| `apply_manual_links` | Rechecks agents' manual links (brief `REFERENCES.md`) and applies the ones that hold up. |

**Figures: images**
| Script | Does |
|---|---|
| `upscale_queue` | Lists photos and adverts to restore → `figures/upscale_queue.yaml`. |
| `upscale_batch` | Upscales through ImageRouter (`IMAGEROUTER_API_KEY` in `.env`) and checks each result against the crop. |
| `restored_images` | Compresses restored images for the site (`figures/images/map.yaml`). |

**Figures: chemistry** (optional)
| Script | Does |
|---|---|
| `structure_batches` | Splits a unit's structure figures into reading batches. |
| `structure_readings` | Checks and merges two blind readings (A/B) → `compounds_draft.yaml`. |
| `drawing_stereo`, `stereo_from_drawing` | R/S from the drawn wedges. |
| `verify_compounds` | Checks read structures against PubChem. |
| `name_compounds` | Finds names for structures the book shows only by number. |
| `render_structures` | Verified compounds → theme-aware SVGs. |
| `compare_generic` | Compares two blind readings of generic (R-group) figures. |
| `compare_scheme` | Compares two blind readings of schemes; `--apply` copies agreed specs and skips `locked: true` ones. |
| `scheme_preview`, `scheme_check`, `render_spec` | Preview a spec, check its molecules against PubChem, render each molecule to PNG. |

**Outputs**
| Script | Does |
|---|---|
| `build_content` | Unit → `site/content/units/<slug>.json` + `toc.json` (the site's data). |
| `make_pdf` | A4 / A5 / bilingual PDF printed from the built site. |
| `export_markdown` | A unit as portable English Markdown. |

`bookroot.py` is the shared import (`ROOT`, `CONFIG`, `KIT`).

## Briefs

`scriptorium brief CONVENTIONS` is the core markup contract. Each book extends it in its own `CONVENTIONS.md`. The phase
briefs are `BOXES`, `TRANSCRIBE`, `TRANSLATE`, `REVIEW`, `FIX` and `REFERENCES`. For figures: `STRUCTURES`,
`GENERIC`, `SCHEMES`, `CHARTS`, and `TWO_READERS` (how to run any of them as two blind readers). Hand an agent the
brief, the book's CONVENTIONS and a concrete slice (pages, unit or figures).

## Site

`site/` is a Next.js 16 static site (Tailwind v4, Pagefind). It has source/English side by side per paragraph,
sidenotes for TNs, figure blocks (structures, schemes, class maps, charts, illustrations, restored images), search in
both languages, and themes (light, paper, dark). The book's name, authors and language labels come from
`src/book.json`, which `sync_book` writes on every `scriptorium build`. `scriptorium new` copies the site into each
book, so each book can grow its own UI. Improvements worth sharing get ported back to `kit/site` by hand.

## Known limitations

- **`de`/`en` in names:** `de.md`, `title_de`, the JSON keys and some component names say `de` for "source language".
  Renaming would touch every script and the site, so it was left as is. Readers only see the labels from `book.json`.
- **Some German-specific parsing remains:** `build_content` strips a leading "Exkurs:" when matching titles. Source
  reference-list headings are set by `references_heading` in `book.yaml`, and English lists must be titled
  `## References`.
- **Chemistry defaults:**
  - `render_structures` lays aryl–ethylamine skeletons out on a fixed template, and everything else with RDKit's own
    layout. Add a template for your compound class if the book draws one consistently.
  - `name_compounds` prefers the name roots listed in `book.yaml` → `chemistry.familiar_names`.
- **Unit keys:** `build_content` and `crop_figures` take the unit slug, `export_markdown` the slug or dir. Other scripts
  take the unit's `dir`. Each usage line says which.
- **Figure-spec kinds** (scheme, generic, classmap, toc) were shaped by one book. A new figure type means extending
  `build_content` and `scheme-view.tsx` together.
