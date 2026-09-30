# Redrawing a scheme (pilot)

A scheme in the book (a metabolic pathway, a biosynthesis, a structure–activity comparison) is redrawn on the site as a
**grid that mirrors the printed layout**: structure cells (drawn from SMILES), arrow cells (with their labels) and text
cells. You turn one printed scheme into a YAML spec. **Accuracy is everything**: draw what is printed; anything you
are unsure of goes into `notes`, never guessed.

## Input
Your figure (given in your task): its crop `figures/<unit>/<figure>_orig.png` (300 dpi), the placeholder line in
`work/<unit>/en.md` (English caption and every label, already translated — use this wording) and the same line in
`work/<unit>/de.md` (German). Open the crop with Read; zoom regions with Pillow (crop + resize 2–3×, save to your
scratchpad, Read it).

## Output — `work/schemes/<figure>.yaml`

```yaml
id: p0951-1
unit: ex-molekulare-pharmakologie
nodes:                         # every drawn molecule, and free text that sits in the scheme as its own element
  n1:
    number: "6"                # compound number as printed, or null
    name_en: "tryptophan"      # label under/next to it, English (from the placeholder labels); null if none
    name_de: "Trp"             # as printed
    pubchem_query: "L-tryptophan"   # English name to look it up; null if no name printed
    smiles: "N[C@@H](Cc1c[nH]c2ccccc12)C(=O)O"   # AS DRAWN; stereo only via stereo_drawing (see below)
    stereo_drawing: null       # exactly as in `scriptorium brief STRUCTURES` rule 3, when wedges are drawn
  t1:
    text_en: "Cofactors: iron, oxygen, tetrahydrobiopterin"   # a text-only element (no smiles)
    text_de: "Cofaktoren: Eisen, Sauerstoff, Tetrahydrobiopterin"
grid:                          # rows top to bottom, cells left to right, as laid out in print
  - [n1, {arrow: right, label_en: "tryptophan hydroxylase", label_de: "Tryptophanhydroxylase"}, n2]
  - [null, t1, null]           # null = empty cell
notes: ""                      # uncertainties, book errors, anything simplified
```

Arrow cells: `{arrow: right|left|down|up|down-right|down-left|up-right|up-left|both, label_en, label_de,
label_below_en, label_below_de}` — `both` is an equilibrium/⇄; labels above and below the arrow as printed.
Optional on an arrow cell:
- `style: open` — the book's hollow block arrow (a structural change / SAR step rather than a reaction); default `line`.
- `heads: both` — a head at each end (⇔ drawn diagonally or as a block arrow: a relation both ways, not an equilibrium).
- `style: blocked` — a line arrow struck through with an × (the reaction does not take place / is hindered).
- `label_side: right | left` — the label is printed beside the arrow, not above/below (typical for vertical arrows).
- `span: N` — the cell covers N columns; `rows: N` — it runs down N rows (e.g. one long time axis). Cells the
  arrow covers in later rows are written as `null`.
Node and text cells can span too: `{node: n4, span: 2}` / `{node: t1, span: 3}` instead of the bare key.
`data_en`/`data_de` and all labels may carry the same light markup as the placeholder labels
(`*K*<sub>i</sub> 5-HT<sub>2A</sub> = 18nM`, `BH<sub>4</sub>`). Keep the grid as small as the print allows; branching schemes use more
rows. Reagents or small molecules written beside an arrow (O₂, H₂O, CO₂, SAM …) go into the arrow's label, not as nodes.
Radicals or charged species: draw with explicit charges/radicals in SMILES (`[O-]`, `[NH3+]`, `[O]` for a radical O).

## Generic structures (R groups, ring numbering, variable positions)
A figure of generic (Markush) structures is a spec with `kind: generic` at the top and a grid of molecule nodes (no
arrows needed). A generic molecule node uses atom maps in `smiles` and three optional fields:

```yaml
  a:
    smiles: "[*:1]C(N([*:2])[*:3])[CH2:20][c:13]1[c:14][c:15][c:16][n:11][n:12]1"
    rgroups: {1: "R<sub>α</sub>", 2: "R′", 3: "R″"}          # label of each placeholder atom [*:n], as printed
    locants: {11: "1", 12: "2", 13: "3", 14: "4", 15: "5", 16: "6"}   # ring numbering printed at atoms
    attach: {from: 20, to: [13, 14, 15, 16], via: 13}         # floating bond (see below)
```
- **R groups:** every R, R′, R″, R<sub>α</sub>, R2, R4, X, Y, Ar, Hal … is a placeholder atom `[*:n]` bonded where
  it is drawn; its printed label goes in `rgroups` (markup: `R<sub>α</sub>`, `R′`, `R″`, `R<sub>4</sub>` or `R4` as
  printed). Keep ring atoms that carry labels or R groups as `[c:n]` / `[n:n]` so they can be referenced.
- **locants:** small ring numbers printed next to ring atoms (map number → text).
- **attach:** a substituent drawn with a bond that *crosses into the ring* (its position is not fixed). Bond the
  substituent in `smiles` to the ring atom nearest to where the printed bond crosses the ring (`via`); `to` lists the
  ring positions it may occupy (ring atoms that can carry it — usually the ring carbons), `from` is the substituent
  atom the bond starts at. The renderer hides the `via` bond and draws the crossing bond like the book.
- Several floating bonds on one structure: `attach` as a list, one entry per bond: `attach: [{from: 20, to: [...], via: 13}, {from: 21, to: [...], via: 15}]`.
- **highlight:** a shaded circle printed behind part of a structure (the site the text is about): list the map numbers
  under it: `highlight: [1]` for a disc behind one atom, `highlight: [4, 5, 6]` for three separate discs,
  `highlight: [[5, 6]]` for one disc around several atoms. The renderer draws soft discs beneath the structure.
- **dashed:** bonds printed broken/dashed (e.g. positions "combined with" a parent pattern): `dashed: [[3, 20], [6, 23]]`
  (pairs of map numbers, one per bond).
- **show_h:** an H printed as its own atom (e.g. "H" above an N, with R to the right): give that atom a map number
  and list it, `show_h: [7]`; the layout then follows the print.
- `n` in a ring or chain ("(CH₂)ₙ", a ring of variable size) can't be drawn yet: note it in `notes`; the lead decides.

## Rules
1. Draw what is printed, not what a name implies. If a drawing and its name disagree, draw the print and say so.
2. Every numbered compound in the scheme becomes a node with its number. Unnumbered drawn molecules are nodes too.
3. Generic parts (R, R', X, "Enzym", a protein drawn as a blob) can't be SMILES: use a text node or put it in `notes`
   and say how you'd show it; don't force it.
4. Don't look structures up online to decide what to draw.

## When the grid can't carry it
Some schemes don't fit a grid honestly (curved side-arrows for co-reactants, many crossing arrows, a molecule with a
substituent at an unfixed position). Don't force them: write what you can, and say in `notes` exactly what is lost —
the lead decides whether the scheme stays a printed image.

## Self-check (required)
`scriptorium run scheme_preview work/schemes/<figure>.yaml` validates the spec and renders
`work/schemes/preview/<figure>.png`. Compare it with the crop, cell by cell and atom by atom. Fix and re-run until clean.

## Final reply
Keep it short: nodes/arrows count, anything that couldn't be expressed in this format (and what you'd need), every
uncertain reading, and **how long it took you** (rough number of tool calls) — this is a pilot to judge the effort.

## Class maps (`kind: classmap`)
A parent structure with arrows out to classes, each class headed "Chapter 7.1" (or "Kapitel 7.1." in print). Layout:
put the nodes in `grid` at their printed positions (no arrow cells — the site draws each arrow on the true line
between the parent and the class). Node fields:
- `role: core` on the parent structure (or key it `core`).
- `chapter: "7.1"` on each class that names its section (the site links it). A class without a printed chapter
  reference has no `chapter`.
- `arrow: out` (default for classes with a chapter: parent → class), `in` (class → parent), or `none` (no arrow
  printed, e.g. a text block); `arrow_label_en/de` = text printed on that arrow ("remove R2").
- The class's printed description ("2,3-Disubstituted (~60)") is its `name_en`/`name_de`; text blocks beside the
  structures are text nodes (`text_en`/`text_de`, `arrow: none`).
- Arrows between two classes (not from/to the parent) can't be drawn in a class map: then use a normal scheme
  (arrow cells), and still put `chapter` on the nodes — it links there too.
Worked examples: your book's first agreed specs of that type (the lead names them in the task once they exist).

## Marks for scaffolds a single structure can't show
Don't skip a figure just because it has one of these. Each is a node field (maps refer to atom-map numbers in `smiles`):

- **Repeat units** — `(CH2)n` on a chain or a polymer `[ ]n`:
  `repeat: [{atoms: [3], label: n}]` (round brackets across the bonds leaving the unit), or for a unit with side
  chains `repeat: [{bonds: [[3, 1], [4, 2]], label: n, shape: square, upright: true, size: 0.75}]` (`[in, out]` per
  bond). Polymer end marks are R groups labelled `*`. A bridge printed as text, like "(CH2)n" between two rings, is
  simply an R group labelled `(CH<sub>2</sub>)<sub>n</sub>`.
- **Variable box** — a rounded box around part of a chain ("any position in here"), with substituents whose bond
  reaches into it: `box: {atoms: [3, 4], float: [{from: 6, via: 3}]}`. In `smiles`, the substituent is bonded to `via`.
- **Ring of unspecified size** drawn as an arc: write a concrete ring in `smiles`, then
  `arc: {atoms: [fusion atom, …ring atoms in order…, fusion atom], float: [{from: N, via: ring atom}]}`.
- **Overlay** of two structures printed on top of each other: the analogue in `smiles`, the reference in
  `under: {smiles, rgroups, coords, align: {map here: map under}, ring: {top: […], under: […], toward: map}}`
  (a five-membered ring over a six-membered one). The reference is drawn faint.
- **Ring of unspecified size as a full circle** (a cyclic amine drawn as a circle through N): a concrete ring in
  `smiles`, then `circle: {atoms: [ring maps], float: [{from, via}]}`. Labelled atoms on the circle (N) keep a gap.
  Two arcs around one ring (a dibenzo ring of any size): `arc: [{atoms: […], center: [all ring maps]}, {…}]`.
- **"Any ring"** as a rounded square: a blank R group (`" "`) with `box: {atoms: [it], size: [1.5, 1.5], float: […]}`.
- **Dashed symmetry axis**: `axis: {through: [map, map], extend: 1.5}`.
- **Resonance forms**: `kekule: as_written` keeps the double bonds where the SMILES puts them; `inner_circle: [[ring
  maps]]` draws benzene with a circle.
- **( )n at a bend**, brackets either side of the CH2 rather than across its bonds: `repeat: [{atoms: [m], around: true, label: n}]`.
- **Conformation pictures**: `lone_pairs: {map: [degrees]}` (Lewis bars), `lobes: {map: [degrees]}` (orbital lobes),
  `clash: [{at, toward}]` (steric repulsion half-circles), `wavy: [[a, b]]` (configuration left open).
- **Binding models**: `decor: [{from: map, bar | line (dash) | arc (fill) | text …}]` places receptor bars, H-bond lines,
  interaction regions and labels relative to an atom, in bond lengths.
- **Scheme size**: `wide: true` (use the margin column), `scale: 1.5` (mostly-label figures) or `0.7` (big maps), `tight: true`.
- **Printed orientation** — `coords: {map: [x, y]}` pins atoms (bond lengths, y up). Pin the atoms that set the
  shape (backbone, the first atom of each side chain); if a render warns that a pin was released, pin one more
  neighbouring atom rather than fewer.

Check every one with `scriptorium run render_spec <spec> <scratch>` against the crop.
