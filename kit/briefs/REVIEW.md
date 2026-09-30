# Review brief (phase 4a) — independent review of a translation

Context: see the book's `book.yaml` and `CLAUDE.md`. You are the **independent reviewer**: you did not write the
translation. Find every place where the English is not a complete, faithful rendering of the source. An expert
proofreads later; your findings focus them. Be rigorous; don't flag pure style preferences.

Files: source `work/<dir>/de.md`; English `work/<dir>/en.md`; known source errors `work/<dir>/source_notes.md` (if
present); rules `scriptorium brief CONVENTIONS` + the book's `CONVENTIONS.md`; `glossary.yaml`. Documented choices (TNs,
placeholders, the verbatim reference list, `invariant_exceptions.yaml`) are not errors — but check each TN is accurate.
**Do not edit de.md or en.md**; write findings only to `work/<dir>/review.md`.

## Method
Paragraph by paragraph (aligned 1:1; page anchors help), sentence by sentence:
- **Omissions:** clauses, qualifiers, hedges ("probably", "about"), negations, numbers, names.
- **Additions:** explanations or certainty the source doesn't have.
- **Meaning shifts:** wrong sense, negation, subject/object, causality, modality, tense of historical facts, direction
  of comparisons, and the field's own terms (in a chemistry book: stereodescriptors, receptors, agonist vs.
  antagonist, substrate vs. product, units; in another field, its equivalents).
- **Terminology:** deviations from `glossary.yaml`, or one source term rendered inconsistently.
- **Markup:** italics, bold item numbers and run-in words, sub/superscripts.
- **Figures & tables:** captions, every `labels:` entry, table cells.
- **TN accuracy**, and errors in the original that still lack a TN.
- A quick fluency pass for genuinely wrong or unclear English.

## Output (`review.md`)
Header with counts per severity. Then per finding:
```
### R<n> — <critical | major | minor> — para <index> (p.<page>)
**SRC:** exact snippet
**EN:** exact snippet
**Issue:** what's wrong
**Suggested EN:** corrected wording (only the changed phrase)
```
critical = meaning changed / factually wrong / content missing; major = noticeable inaccuracy or wrong term; minor =
nuance, markup or fluency. End with "Checked and fine" listing the TNs you verified.

## Final report (short)
Counts per severity and the 3–5 most important findings, one line each.
