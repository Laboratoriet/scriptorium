# Lessons — what the first book taught

Each rule is here because breaking it cost real time on the first book, a ≈1,000-page German chemistry monograph. Read this once
before phase 1.

## Source and transcription
- **Re-transcribe; don't trust old OCR.** The book's OCR layer silently dropped a whole data table and several
  reference entries, and mangled chemical names ("th" read as "ih"). A vision model reading 150 dpi pages, zooming to
  300 dpi for anything small, was far more accurate.
- **Page-break state describes text flow, not layout.** A page ending with a full sentence followed by a figure does
  not continue. Getting this wrong glues sentences onto figure placeholders. `join_pages` now handles this.
- **Footnotes need their own marker convention** (`---` then the notes). Inline leftovers broke alignment.
- **Errors in the original are translated as written, with a TN.** The book's drawings of two compounds had their
  stereochemistry swapped relative to the correct names. Check structures against the drawing, the name and PubChem,
  never just one.

## Translation
- **Hard invariants catch what reviewers miss.** Numbers, item numbers, reference markers, placeholders and page
  anchors must match as sets. A 1:1 paragraph count is what makes source/English side by side possible at all.
- **Exceptions are declared, never hidden.** A legitimate difference goes in `invariant_exceptions.yaml` with a reason.
  An agent that tucks a number into a TN to satisfy the checker has hidden an error.
- **Review and fix are separate agents,** and the fixer logs a `## Resolution` for each finding. A rejected finding
  needs a reason you can check.
- **Copyright:** agents declined a complete translation of an in-copyright book, even for private study of an owned
  copy, and one was stopped by a safety classifier. Settle `rights:` in phase 0. Don't reword around a refusal; use
  `translation: supplied` or ask for permission.

## Figures
- **Two blind readers for anything interpretive** (structures, schemes, class maps). They work independently, a script
  compares them, and the lead resolves only the disagreements. Agreement between two blind readings was the single
  best predictor of a correct figure.
- **Never use generative upscaling on chemistry or labelled line art.** Nano Banana / GPT-image upscales invented
  bonds, reaction steps and labels that looked plausible. Photos and adverts are fine; line art gets classic
  clean-up (contrast/sharpening) or a redraw.
- **Hand edits get `locked: true`.** `compare_scheme --apply` overwrote three hand fixes before the flag existed.
- **A spec field that should be a list must accept a string.** A one-line data field rendered one character per line.
  `as_list()` guards every such field.
- **Crop coordinates need a visual check.** One crop carried a stray rule from the next figure. `check_boxes` renders
  every crop so you can look.
- **Simple schematics are faster to redraw as SVG than to restore,** and they then follow the site's theme.

## Site and PDF
- **Apply persisted UI state before first paint.** Theme, notes-hidden and collapsed-contents preferences go in an
  inline `<head>` script. Otherwise the page flashes and shifts.
- **Chrome evaluates breakpoints differently when printing.** Freeze the responsive layout at the page width before
  printing (what `make_pdf` does), or measured elements like the class-map arrows vanish on A5.
- **Measured SVG overlays need the zoom factor.** Inside a CSS-zoomed figure, `getBoundingClientRect` is scaled:
  k = rect.width / offsetWidth.
- **Test every toggle after CSS changes.** Adding the notes toggle's selector to a shared rule silently broke the
  per-paragraph source toggle.
- **Light theme:** a "paper" tone alongside pure white. Faint ink had to be darkened to keep AA contrast on paper.

## Process
- **Pilot one chapter end to end first.** An 18-page pilot chapter took ≈10 agent runs and ≈1.3 M subagent tokens, which
  was enough to scale the estimate to the whole book.
- **Record decisions with dates** (`STATUS.md`, memory). Several were revisited weeks later (for example, a content
  rule that applied from one chapter on and was later withdrawn), and the date made it clear what applied where.
- **Subagents can't ask the user.** Interviews and confirmations stay in the lead session.
