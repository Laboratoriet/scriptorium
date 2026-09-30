# Translation brief (phase 3) — read fully before starting

Context: see the book's `book.yaml` and `CLAUDE.md`. Goal: a scholarly English edition that an expert reader of the
source language will proofread. **Faithfulness and completeness first**, then fluent academic American English.

Book root: the folder with `book.yaml`. Your unit's folder is `work/<dir>/`.

## Read first
1. `work/<dir>/de.md` — the verified source text. Read it completely before translating.
2. `scriptorium brief CONVENTIONS` (translation section) and the book's `CONVENTIONS.md` — binding.
3. `glossary.yaml` — follow it; reuse its renderings.
4. `work/<dir>/source_notes.md` if it exists — known errors in the original: add a `<!-- TN: … -->` at each listed spot.
5. `source/toc_en.yaml` — English wording for headings in the table of contents.
6. The style reference the task names (an already reviewed unit).

## Hard requirements (a script checks them)
1. Same headings/levels and paragraphs in the same order — one English paragraph per source paragraph, never merged or
   split. The reference list heading becomes `## References`; entries copied **verbatim**.
2. Every bold item number, reference marker (keep `[21, 33-38]` style), footnote ref, page anchor `<!-- p.N -->` (same
   position in the sentence as far as English allows), `{{fig:…}}` placeholder and `<sub>`/`<sup>` content appears
   exactly as often as in the source.
3. Numbers and units exactly as written. Where English needs another form (decimal comma, "100mal" → "100-fold"), add
   an entry to `work/<dir>/invariant_exceptions.yaml` (`numbers_missing_in_en` / `numbers_extra_in_en`, each with a
   reason) instead of bending the English.
4. `{{fig:…}}`: keep id, kind, compounds; translate `label:`, `caption:` and every `labels:` entry (atom labels,
   formulae, units unchanged; names in standard English).
5. English quotations stay verbatim; source-language translations of them are dropped with a TN.
6. Emphasis carries over, including letter games that spell a name.
7. Where the source is ambiguous, seems wrong, or you made a non-obvious choice: translate as written and add
   `<!-- TN: … -->` on the same line right after the sentence (never as its own paragraph).

## Omitted passages
`{{omitted: …}}` markers are copied into `en.md` unchanged, as their own paragraphs (only if the book has a policy).

## Check
Run `scriptorium run check_invariants work/<dir>/de.md work/<dir>/en.md` from the book root and fix every hard failure until it
prints "all hard invariants match". For length-ratio warnings re-read that paragraph against the source. Never hide a
number inside a TN to satisfy the checker.

## Output
Write only `work/<dir>/en.md` (and `invariant_exceptions.yaml` if needed).

## Final report (short)
Checker result; list of TNs; new glossary terms (source → EN) you decided on; anything unsure.
