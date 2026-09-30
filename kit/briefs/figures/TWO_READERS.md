# Rollout: schemes (two blind readers)

You are reader **A** or **B** (given in your task). Another reader does the same batch independently; the two
readings are compared automatically (`scripts/compare_scheme.py`), so **accuracy beats speed** and **never look at
the other reader's folder**. Layout is not compared; molecules, numbers, data lines, text and arrows are.

1. Read `scriptorium brief SCHEMES` completely (the spec format, incl. "Generic structures"), and rule 3 of
   `scriptorium brief STRUCTURES` (stereo from wedges). Worked examples: your book's first agreed specs of that type (the lead names them in the task once they exist).
2. Your batch file `work/scheme_rollout/batchNN.json` lists figures: `figure`, `unit`, `crop`. For each figure open
   the crop (zoom regions with Pillow, 2–3×) and the placeholder line in `work/<unit>/en.md` and `de.md`
   (search `fig:<figure>`): English/German caption and every printed label. **Use the placeholder's English wording.**
3. Write one spec per figure: `work/scheme_rollout/<READER>/<figure>.yaml` with `id`, `unit`, `nodes`, `grid`, `notes`.

## Conventions (so the two readings match)
- **Every drawn molecule is a node**, numbered or not. `number` as printed, without brackets ("51", "12a").
- `name_en` = the compound's name only ("caffeine", "dopamine", "L-DOPA"). **Everything else printed with a
  compound** — Ki/EC50 values, doses, durations, activity words ("inactive", "weak effect") — goes in
  `data_en`, **one list item per placeholder label** (a statement wrapped over several printed lines is one item), numbers and units exactly as printed ("200-350mg", "8-12h",
  "Ki 5-HT2A = 34nM (16nM)"). Mirror them in `name_de`/`data_de` from the German placeholder.
- Text standing on its own in the scheme (a heading like "2,4,5 pattern", a note, a question) is a **text node**
  (`text_en`/`text_de`), one per printed block.
- Arrows: one arrow cell per printed arrow. Hollow block arrows (SAR steps) are `style: open`; line arrows are
  reactions/steps. Text printed on or beside an arrow ("remove 4-OH", "MAO", "tyrosine hydroxylase", O₂, H₂O,
  CO₂) is that arrow's `label_en` / `label_below_en` — never a node. Equilibrium ⇄ is `both`; an arrow struck
  through with × is `style: blocked`. Deuterium is `[2H]` (drawn as D).
- `name_en`: the name as printed in the placeholder, without surrounding brackets ("(Caffeine, C)" → "Caffeine, C").
- Numbers in labels ("=" under an equilibrium, "x0.25" beside an arrow) belong to that arrow's labels.
- A branching scheme uses more rows; diagonal arrows are `down-right` etc. Keep it close to the printed layout.
- R groups, variable positions, ring numbering, shaded discs: generic node fields (`scriptorium brief SCHEMES`). Generic and real
  nodes can sit in one scheme.
- Charges and radicals explicitly in SMILES (`[NH3+]`, `[O-]`, `[O]`). Stereo only via `stereo_drawing`, and only
  when wedges/hashes are drawn. Double-bond geometry is different: a C=C drawn trans or cis is written with
  `/` `\` in `smiles` (E/Z as drawn).
- A drawing that disagrees with its label or the text: draw the print, say so in `notes`.
- **Skip** (write only `id`, `unit`, `skip: "<why>"`) when the scheme can't be carried honestly: electron-pushing
  mechanism arrows, enzyme/protein drawn as a shape that the reactions attach to, curved co-reactant arrows whose
  meaning would be lost, a polymer, ring or chain of variable size, a 3D picture. No partial specs.

## Check each spec
- `scriptorium run scheme_preview work/scheme_rollout/<READER>/<figure>.yaml` → must say "no problems";
  open `work/scheme_rollout/<READER>/preview/<figure>.png` next to the crop and compare cell by cell.
- Render each molecule and compare atom by atom: `scriptorium run render_spec work/scheme_rollout/<READER>/<figure>.yaml <scratch>/<figure>`
  (a PNG per molecule; Greek letters may not show in the PNG — expected). Fix until right.
- Scratch files only in `<your scratchpad>/scheme_<READER>_<NN>/`. Edit nothing except your own spec files.
  Don't look structures up online.

Final reply (short): figures done, skipped (why), every uncertain reading, anything the format couldn't express,
rough number of tool calls.

## Class maps (batches 17–21)
These figures show classes of compounds, usually with "Kapitel/Chapter x.y" per class. Read the section
**"Class maps"** at the end of `scriptorium brief SCHEMES` and the two examples it names. Decide per figure:
- parent structure with arrows only between the parent and each class → `kind: classmap` (no arrow cells; `role`,
  `chapter`, `arrow`, `arrow_label_en/de` on the nodes);
- anything else (arrows between classes, chains, a flowchart) → a normal scheme with arrow cells, `chapter` still on
  the nodes that print one.
Put "(~60)"-style counts in `name_en` with the class description, as printed. Generic structures (R2, R3 …, ring
numbers, α/β) use the generic node fields.

## Partial figures (batches 22–32)
These figures mix real compounds with generic members (R on N, a floating R, R′, X …). The site already shows the
real ones as structure cards and keeps the scan for the rest; your spec replaces both with the whole figure.
- Write the **whole figure** as `kind: generic`: every drawn molecule is a node, real and generic alike, in print
  order (grid rows as printed; no arrow cells unless arrows are printed — then it's a normal scheme with the
  generic fields on the nodes that need them).
- Real members: plain SMILES as drawn (stereo via `stereo_drawing` only when wedges are drawn), `number` and
  `name_en` as printed. Generic members: the generic node fields (`scriptorium brief SCHEMES`, "Generic structures"), incl.
  `dashed` for bonds printed broken.
- Conventions from the generic rollout apply (`scriptorium brief GENERIC` "Conventions"): ring N–H as `[nH]` without
  `show_h`; "NR₂" printed as one piece is one placeholder; primes as ASCII R' / R''; Greek locants allowed.
- Skip the figure (`skip: "<why>"`) only if a member can't be drawn honestly: a chain or ring of variable size
  ((CH₂)ₙ, [ ]ₙ), a ring drawn as a plain circle/arc of unspecified size, a 3D picture.

## Structure–activity summaries (batches 33–37)
Class maps with a printed **text block (callout)** beside each class, plus free text blocks. Read the "Class maps"
section of `scriptorium brief SCHEMES` first; the additions:
- On a class node (or a free text node, which then has no `smiles`/`text_en`): `callout_en` / `callout_de` = the
  printed block as a **list of lines, one item per placeholder label** (the placeholder in en.md/de.md has the text,
  already translated — use it verbatim, markup included). A bulleted line starts with "- " (dash + space); a line
  like "3,4-Dimethoxy:" is a small heading line without a dash. `callout_side: below | right | left` = where the
  block sits relative to its structure in print.
- Boxes drawn around classes are not reproduced (the layout carries the grouping); say so in `notes`.
- **Two-page figures:** if your batch item has `continues` (and `crop_continued`), the printed figure runs over two
  pages. Write ONE spec for the first figure id with `continues: <second id>` and all nodes of both pages in one
  grid (the second page's elements where they sit, typically further right or below). Don't write a spec for the
  second id.
- Decision trees ("# S atoms? none / one / two …"): a normal scheme — text nodes for questions
  and answers, arrow cells for the branches, structures/names as nodes. Not a class map.
- Chapter references inside callouts stay as text ("chapter 8.4"); the site links them.
