# Scriptorium — rules for Claude working on the kit itself

(Working on a *book*? That book's own `CLAUDE.md` applies. Start with `scriptorium next`.)

## Layout
- `scriptorium` + `kit/cli.py`: the command. Everyday commands stay few and friendly, and everything else is a tool
  behind `scriptorium run`.
- `kit/scripts/`: the tools. Each one works on one book: `from bookroot import ROOT, CONFIG`, and the book's facts
  live in `book.yaml`. Never hard-code a path or a book detail.
- `kit/briefs/`: agent briefs, printed by `scriptorium brief NAME`. They refer to each other the same way.
- `kit/template/`: what `scriptorium new` copies into a book. `kit/site/`: the reading site, copied per book.
- `docs/`: WORKFLOW (the map behind `next`), LESSONS, TOOLS.

## Rules
- **No book content in this repo,** ever: no text, crops, specs or examples taken from a real book. Examples in briefs
  use neutral compounds and made-up pages.
- A change to the phases means updating `next_steps()` in `kit/cli.py` and `docs/WORKFLOW.md` together.
- Test a change end to end on a throwaway book in a scratch directory: `new` → `next` → `check` → `build` → `pdf`.
  Delete it afterwards.
- Keep `docs/TOOLS.md` in step with `kit/scripts/` (a tool's first docstring line is its summary).
