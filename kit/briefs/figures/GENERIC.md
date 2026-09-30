# Rollout: generic structure figures (two blind readers)

You are reader **A** or **B** (given in your task). Another reader does the same batch independently; the two
readings are compared automatically, so **accuracy beats speed** and **never look at the other reader's files**.

1. Read `scriptorium brief SCHEMES` completely — the spec format, and especially **"Generic structures"**
   (rgroups, locants, attach = floating bond, highlight = shaded circles, show_h = an H printed above N).
   Worked examples: your book's first agreed specs of that type (the lead names them in the task once they exist).
2. Your batch file `work/generic/batchNN.json` lists figures: `figure`, `unit`, `crop`. For each figure open the crop,
   and the placeholder lines in `work/<unit>/en.md` and `de.md` (search `fig:<figure>`) — they give the English/German
   caption and labels. Use the English wording from the placeholder for names.
3. Write one spec per figure: `work/generic/<READER>/<figure>.yaml`, with `id`, `unit`, `kind: generic`, `nodes`, `grid`,
   `notes`. One node per drawn molecule in reading order (left→right, top→bottom); `number` as printed (or null);
   `name_en`/`name_de` if printed under it. Arrows only if printed (then use arrow cells as in SCHEMES.md).
4. **If a figure can't be expressed honestly** (a ring or chain of variable size "n", a protein, a 3D picture, a
   reaction mechanism, text only), write the file with just `id`, `unit` and `skip: "<why>"` — don't force it.
5. Check each spec: `scriptorium run scheme_preview work/generic/<READER>/<figure>.yaml` (must say
   "no problems"), then render the real SVGs and look at them next to the crop:
   `scriptorium run render_spec work/generic/<READER>/<figure>.yaml <scratch>/<figure>` (a PNG per molecule; Greek α may not
   show in the PNG — expected). Compare atom by atom; fix until right.
6. Scratch files only in your own folder `<your scratchpad>/generic_<READER>_<NN>/`. Edit nothing except your spec
   files. Don't look structures up online.

## Conventions (from wave 1 — follow these so the two readings match)
- A figure with **any** member that can't be expressed (variable (CH₂)ₙ chain, polymer [ ]ₙ, ring of unspecified size
  drawn as a circle/arc, substituents on a boxed chain, 3D chairs) → **skip the whole figure**; name the drawable members
  in the skip reason. No partial specs, no text nodes standing in for structures.
- N–H: in a ring (pyrrole, imidazole, lactam) write `[nH]`/`[NH]` and **no** `show_h`. On a chain N where the print shows
  the letter H apart from the N (above/below), use `show_h` on that N.
- A condensed label like "NR₂" printed as one piece is one placeholder: `[*:n]` with label `NR<sub>2</sub>`.
- Greek locants on chain atoms (α, β printed at a carbon) go in `locants` like ring numbers; they render correctly.
- Primes: write R' and R'' (ASCII), as in the placeholder labels.
- Floating bond `via`: the ring atom nearest to where the printed bond crosses; `to` = every ring atom that could carry it
  (ring carbons, or as the figure implies).

Final reply: figures done, skipped (why), every uncertain reading, anything the format couldn't express.
