# {{title_en}} — a Scriptorium book

English edition of {{authors}}, *{{title}}* ({{year}}), translated from {{source_name}}.
Rights: **{{rights}}** · translation: **{{translation}}** (see `book.yaml`).

## How to work on this book
1. Run `scriptorium next`. It inspects the book and names the one next step; do that step, then run it again.
2. Agent work always uses a brief: `scriptorium brief <NAME>` prints it (TRANSCRIBE, TRANSLATE, REVIEW, FIX, BOXES,
   REFERENCES, CONVENTIONS; for figures STRUCTURES, GENERIC, SCHEMES, CHARTS, TWO_READERS). Give each agent the brief,
   this book's `CONVENTIONS.md` and a small slice (≈4 pages, one unit). Never an improvised prompt.
3. Nothing is done until `scriptorium check` passes for it. After content changes: `scriptorium build`.
4. Log decisions with dates in `STATUS.md`.

The full guide is `scriptorium docs` (workflow, lessons, tools).

## Rules
- Respect `rights:`. If an agent declines to translate, stop — don't reword the task. Suggest `translation: supplied`
  or asking the rights holder.
- Unless the rights allow it, the book stays local: no deploys, uploads or sharing.
- Never use generative upscaling on chemistry or labelled line art — it invents detail.
- Hand-edited figure specs carry `locked: true`.
- Visual or UX decisions about the edition are the user's; propose, then ask.
