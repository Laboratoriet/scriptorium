# Reading structures from the book's figures

You transcribe chemical structures from cropped figures of the German book into machine-readable form. Two readers (A and B) do this **independently**; their results are compared by InChIKey. **Accuracy is everything** — a structure you are unsure of must say so in `notes`, never be guessed silently.

## Input
`work/structures_extra/batch<N>.json` — one entry per figure: `figure`, `scope` (the section whose numbering applies), `compounds` (the numbers printed in it, as transcribed), `caption_de` (names as printed), `crop` (the 300 dpi image).

Open each crop with the Read tool. If a detail is small (a wedge, a subscript, a double bond, a substituent position), zoom: crop the region with Pillow and save it to your scratchpad at 2–3× (`scriptorium python -c "from PIL import Image; im=Image.open(...); im.crop((x0,y0,x1,y1)).resize(...).save(...)"`), then Read that. The full-page scan is `source/pages/NNNN/scan.jpg` if you need context (e.g. a number printed outside the crop).

## Output
`work/structures_extra/read_<READER>_batch<N>.yaml` — a YAML list, one entry per compound number per figure:

```yaml
- figure: p0070-1
  number: "12"
  names_de: ["Coffein"]              # names printed for it (caption/figure), as printed; [] if none
  pubchem_query: "caffeine"          # English/INN name to look up in PubChem; null if the book gives no name
  smiles: "Cn1cnc2c1c(=O)n(C)c(=O)n2C" # the structure AS DRAWN, no @/@@
- figure: p0070-1
  number: "15"
  names_de: ["Levodopa"]
  pubchem_query: "levodopa"
  smiles: "NC(Cc1ccc(O)c(O)c1)C(=O)O"
  stereo_drawing:                    # only when wedges/hashes are drawn — see below
    mapped_smiles: "Oc1ccc(cc1O)[CH2:2][CH:1]([NH2:3])[C:4](=O)O"
    centres:
      - {atom: 1, neighbours: {2: ul, 4: ur, 3: d}, wedge: [3, hash]}
- figure: p0069-2
  number: "6"
  generic: true                      # Markush: R, R', X, Ar, n … — no single compound
  names_de: []
  pubchem_query: null
  smiles: null
  notes: "benzene ring with R at C-4"
```

Keep `number` a string, exactly as printed (`"2a"`, `"15"`). Write the file as you go (after each few figures), so nothing is lost.

## Rules
1. **Draw what is printed, not what the name says.** The book has errors; they are found by comparing your drawing with PubChem. Never "correct" a drawing to match a name. If you see a discrepancy, note it.
2. **SMILES:** any valid SMILES of the drawn constitution. Implicit hydrogens are fine. Charges, salts, counter-ions and water only if drawn. Aromatic rings as drawn (Kekulé or aromatic both fine). Double-bond geometry (E/Z) with `/` `\` only if the drawing fixes it (a double bond in a chain with substituents drawn on definite sides).
3. **Stereo from wedges — never assign R/S yourself.** If a stereocentre is drawn with a wedge (solid, bold = toward viewer) or hash (dashed = away), keep `smiles` flat and add `stereo_drawing`: a `mapped_smiles` with atom-map numbers on each stereocentre and every drawn neighbour of it; for each centre, the **direction on the page** of each drawn bond from the centre (`u d l r ul ur dl dr`, hexagon angles: ur/ul/dr/dl are ±30° from horizontal, u/d vertical), and which bond carries the wedge (`[map, wedge]` or `[map, hash]`). The wedge's narrow end must be at the stereocentre; if it isn't (wedge points the other way), say so in notes. Implicit H on the centre is not listed. A **drawn** H with a wedge/hash (e.g. on a bridgehead or ring fusion) is written explicitly in `mapped_smiles` as `[H:n]` and listed as a neighbour like any other atom — don't move its wedge onto another bond. The script derives R/S. A name like "(S)-…" without drawn wedges → no stereo_drawing.
4. **Generic structures** (R, R¹, X, Y, Ar, n, "Hal", dashed "variable" bonds, several substituent options) → `generic: true`, `smiles: null`, a short description in `notes`. A figure that only shows a table skeleton is generic too.
5. **Every number** in `compounds` gets an entry. If the crop shows a number that is not in the list, add it with `extra: true` and a note. If a listed number isn't in the crop, add the entry with `smiles: null` and a note.
6. **pubchem_query:** the English/INN or systematic name of the compound as the *book* names it (caption, label in the figure). Translate German names (Coffein → caffeine, Paracetamol → paracetamol, "N-Methylanilin" → N-methylaniline). Brand names in parentheses don't go here. Include a stereodescriptor/sign if the name has one ("levodopa", "(R)-…") only when PubChem would know it by that name; otherwise the plain name. No name printed → null (don't invent one from the drawing).
7. **Schemes** (reactions): read only the compounds with numbers; reagents/arrows are ignored.

## Self-check (required)
After finishing (and whenever useful), run:
```
scriptorium run structure_readings check work/structures_extra/read_<READER>_batch<N>.yaml
```
It lists problems and renders each figure's readings to `work/structures_extra/preview/<READER>/<figure>.png`. **Look at every preview next to its crop** and compare atom by atom: ring substitution positions, chain length, branch points, N-substituents, heteroatoms, double bonds, ring sizes, fused-ring positions. The layout differs from the book; the connectivity must not. Fix and re-run until clean.

## Don'ts
- Don't read other readers' files, `figures/compounds.yaml`, `compounds_draft.yaml`, or `disagreements.md`.
- Don't edit any file other than your own `read_<READER>_batch<N>.yaml` (and scratch files in your scratchpad).
- Don't look compounds up online to decide what to draw; PubChem comparison happens afterwards.

## Final report (your reply)
Short: how many compounds, how many generic, and a list of every uncertain reading or book discrepancy (figure, number, what and why).

## This batch (unnumbered ring systems, ch. 7)
These five figures carry no compound numbers in the book; `compounds` holds placeholder ids `u1`, `u2`, … in the order
the names appear in `caption_de` (left to right, top to bottom in the drawing). Use them as `number`. Each name is the
ring system as printed, so `pubchem_query` is its English systematic name (e.g. "2,3-dihydrobenzofuran"). Draw exactly
what is printed; if a drawing and its name disagree (ring size, saturation, heteroatom), say so in `notes`.

## Batch 2 (ex-aminoxidasen, Table 1 printed as an image)
`batch2.json`: one figure, a table in three columns (hydrazine, cyclopropylamine and propargylamine derivatives) with
11 numbered structures, each with its name printed underneath. Numbers are real (`"14"`, `"11"` …); take `names_de`
from the name under each structure. Output: `read_<READER>_batch2.yaml`; self-check with the same script.
