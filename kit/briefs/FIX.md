# Fix brief (phase 4b) — apply an independent review to a translation

Context: see the book's `book.yaml` and `CLAUDE.md`. Files: `work/<dir>/review.md` (findings R1…Rn), `work/<dir>/en.md`
(to fix), `work/<dir>/de.md` (source), `work/<dir>/source_notes.md` (if present), the conventions, `glossary.yaml`.

1. For every finding, re-check it against the source yourself, then fix `en.md`. Use the reviewer's suggestion unless
   it's wrong or reads badly — then write your own faithful fix. Change only the affected phrase/sentence.
2. Never merge or split paragraphs; never touch item numbers, `[n]` references, page anchors (keep their position),
   placeholder ids, or the reference list.
3. Findings that point out an error **in the original** get a `<!-- TN: … -->` on the same line (translate as written).
4. If you disagree with a finding after checking, don't apply it — mark it rejected with a one-line reason. Follow any
   decisions given in your task prompt.
5. Numbers the English must write differently go into `work/<dir>/invariant_exceptions.yaml` with a reason — never bend
   the English or hide numbers in TNs.
6. Append `## Resolution` to `review.md`: one line per finding, `R<n>: applied | rejected (<reason>) | flagged for
   proofreader`.
7. Run `scriptorium run check_invariants work/<dir>/de.md work/<dir>/en.md`; it must print "all hard invariants match".

Final report (short): applied / rejected / flagged counts and the checker's result line.
