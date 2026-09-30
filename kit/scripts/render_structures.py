"""Render verified compounds (figures/compounds.yaml) as theme-aware SVGs.

Black-and-white like the book; the stroke/fill colour becomes `currentColor`
so the site's light/dark theme controls it. Compounds drawn without stereo in
the book are rendered from the flat structure, not PubChem's isomeric one.
"""
import math
import re
import sys
import yaml
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Geometry import Point3D

from bookroot import ROOT  # the book project (book.yaml), not the kit
rdDepictor.SetPreferCoordGen(True)


def orient_like_book(mol: Chem.Mol) -> None:
    """Rotate the 2D depiction so the aromatic ring sits left and the side chain
    points right, as throughout the book. Rotation never changes stereo: wedges
    are recomputed from the chiral tags when drawing."""
    conf = mol.GetConformer()
    pts = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
    ring = [i for i, a in enumerate(mol.GetAtoms()) if a.GetIsAromatic()]
    chain = [i for i in range(mol.GetNumAtoms()) if i not in ring]
    if not ring or not chain:
        return
    centre = lambda idx: (sum(pts[i].x for i in idx) / len(idx), sum(pts[i].y for i in idx) / len(idx))
    (rx, ry), (cx, cy) = centre(ring), centre(chain)
    angle = -math.atan2(cy - ry, cx - rx)
    cos, sin = math.cos(angle), math.sin(angle)
    for i, p in enumerate(pts):
        x, y = p.x - rx, p.y - ry
        conf.SetAtomPosition(i, Point3D(x * cos - y * sin, x * sin + y * cos, 0))


def arylethylamine_template() -> Chem.Mol:
    """A standard layout for aryl–ethylamine skeletons: upright hexagon, ipso carbon at its upper
    right vertex, side chain zig-zagging to the right (ring–CH2 up, –Cα down, –N up)."""
    tpl = Chem.MolFromSmiles("c1ccccc1CCN")
    conf = Chem.Conformer(tpl.GetNumAtoms())
    ring_angles = {5: 30, 0: 90, 1: 150, 2: 210, 3: 270, 4: 330}
    for idx, deg in ring_angles.items():
        conf.SetAtomPosition(idx, Point3D(math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0))
    for idx, (x, y) in {6: (1.732, 1.0), 7: (2.598, 0.5), 8: (3.464, 1.0)}.items():
        conf.SetAtomPosition(idx, Point3D(x, y, 0))
    tpl.AddConformer(conf)
    return tpl


TEMPLATE = arylethylamine_template()


# The same layout for any six-membered aromatic ring (pyridine, diazines …) and a C–C–N side chain.
ANY_RING = Chem.MolFromSmarts("a1aaaaa1CC~[#7]")


def layout(mol: Chem.Mol) -> None:
    if mol.HasSubstructMatch(TEMPLATE):
        rdDepictor.GenerateDepictionMatching2DStructure(mol, TEMPLATE)
    elif mol.HasSubstructMatch(ANY_RING):
        rdDepictor.GenerateDepictionMatching2DStructure(mol, TEMPLATE, refPatt=ANY_RING)
    else:
        rdDepictor.Compute2DCoords(mol)
        orient_like_book(mol)


def render(smiles: str, path: Path) -> None:
    render_mol(Chem.MolFromSmiles(smiles), path)


def _label_deuterium(mol: Chem.Mol) -> None:
    """[2H] is printed as "D" in the book; RDKit would draw "²H"."""
    for a in mol.GetAtoms():
        if a.GetAtomicNum() == 1 and a.GetIsotope() == 2:
            a.SetProp("_displayLabel", "D")


def render_mol(mol: Chem.Mol, path: Path) -> None:
    """Draw a molecule as given (scheme nodes keep drawn stereo and "R" labels on dummy atoms)."""
    layout(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(-1, -1)  # size to fit
    opts = drawer.drawOptions()
    opts.useBWAtomPalette()
    opts.clearBackground = False
    opts.bondLineWidth = 1.5
    opts.fixedBondLength = 30
    opts.padding = 0.08
    opts.fontFile = ""  # system sans
    _label_deuterium(mol)
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    svg = re.sub(r"#000000", "currentColor", svg)
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    path.write_text(svg)


GREEK = re.compile(r"<sub>([αβγδ])</sub>|([αβγδ])")


def _ascii_label(label: str) -> tuple[str, str]:
    """'R<sub>α</sub>' → ('R', 'α'): RDKit can't draw non-ASCII text, so Greek suffixes are added afterwards.
    Primes are written as ASCII ' and '' (as printed in the book)."""
    label = label.replace("′", "'").replace("″", "''")
    greek = "".join(a or b for a, b in GREEK.findall(label))
    return GREEK.sub("", label), greek


def _apply_drawn_stereo(mol: Chem.Mol, drawing: dict) -> None:
    """Give a generic molecule the configuration its wedges show: derive R/S from the drawing (drawing_stereo) and
    set the matching chiral tag on the same atoms here (matched by structure, placeholders included)."""
    from rdkit.Chem import rdCIPLabeler

    from drawing_stereo import mol_from_drawing

    ref = Chem.RemoveHs(mol_from_drawing(drawing["mapped_smiles"], drawing["centres"]))
    for a in ref.GetAtoms():
        a.SetAtomMapNum(0)
    rdCIPLabeler.AssignCIPLabels(ref)
    plain = Chem.Mol(mol)
    for a in plain.GetAtoms():
        a.SetAtomMapNum(0)
    match = plain.GetSubstructMatch(ref, useChirality=False)
    if not match:
        return
    for ref_idx, idx in enumerate(match):
        ref_atom = ref.GetAtomWithIdx(ref_idx)
        if not ref_atom.HasProp("_CIPCode"):
            continue
        want = ref_atom.GetProp("_CIPCode")
        for tag in (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW):
            mol.GetAtomWithIdx(idx).SetChiralTag(tag)
            rdCIPLabeler.AssignCIPLabels(mol)
            if mol.GetAtomWithIdx(idx).GetPropsAsDict().get("_CIPCode") == want:
                break


def render_generic(node: dict, path: Path) -> None:
    """A generic (Markush) structure as printed: R groups on placeholder atoms, ring locants, and optionally the
    book's floating bond (a substituent that may sit at any of several ring positions).

    node: smiles with atom maps ([*:1] for R groups, [c:5] for locant/attachment atoms), rgroups {map: label},
    locants {map: text}, dashed [[map, map] per bond printed broken], highlight [one disc per entry: a map or a list of maps], show_h [maps of atoms whose H is
    drawn as its own atom, e.g. an N–H printed with H above], attach {from: map of the chain atom,
    to: [maps of the possible ring positions],
    via: map of the ring atom the chain is bonded to in `smiles` (where the printed bond crosses into the ring)}.
    """
    from rdkit.Chem import rdchem

    mol = Chem.MolFromSmiles(node["smiles"])
    by_map = {a.GetAtomMapNum(): a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum()}
    greek = {}
    # each entry is one shaded disc: a map number (one atom) or a list of map numbers (one disc around them)
    highlight = [[by_map[int(m)] for m in (h if isinstance(h, list) else [h])] for h in node.get("highlight") or []]
    for m, label in (node.get("rgroups") or {}).items():
        text, suffix = _ascii_label(label)
        mol.GetAtomWithIdx(by_map[int(m)]).SetProp("_displayLabel", text)
        if suffix:
            greek[by_map[int(m)]] = suffix
    greek_notes = {}
    for m, text in (node.get("locants") or {}).items():
        if str(text).isascii():
            mol.GetAtomWithIdx(by_map[int(m)]).SetProp("atomNote", str(text))
        else:  # α, β … : RDKit's font has no Greek, so these are drawn afterwards as text beside the atom
            greek_notes[by_map[int(m)]] = str(text)
    for a in mol.GetAtoms():
        if a.GetAtomicNum() == 0 and a.GetAtomMapNum():
            # Keep differently labelled placeholders distinct once the maps are gone: otherwise a C=N/C=C whose
            # E/Z rests only on R vs R'' looks symmetric and loses its drawn geometry. (The label hides the isotope.)
            a.SetIsotope(a.GetAtomMapNum())
        if a.GetAtomMapNum() and a.GetAtomicNum() and not a.GetFormalCharge():
            # "[c:14]" is a bracket atom: without this it would count as H-less (a radical, drawn as dots)
            a.SetNoImplicit(False)
            a.SetNumRadicalElectrons(0)
        a.SetAtomMapNum(0)
    mol.UpdatePropertyCache(strict=False)
    Chem.SanitizeMol(mol)
    if node.get("stereo_drawing"):
        _apply_drawn_stereo(mol, node["stereo_drawing"])
    show_h = [by_map[int(m)] for m in node.get("show_h") or []]
    if show_h:
        # "H above N, R to the right" as printed: the hydrogen becomes a drawn atom, so the layout places three
        # substituents around N instead of two (same molecule, just an explicit H)
        mol = Chem.AddHs(mol, onlyOnAtoms=show_h)
    layout(mol)

    # One floating bond, or several (a list): each substituent may sit anywhere on its ring.
    attach = node.get("attach")
    floats = []  # (chain atom, via atom, ring atoms, candidate positions)
    for att in (attach if isinstance(attach, list) else [attach] if attach else []):
        chain, via = by_map[int(att["from"])], by_map[int(att["via"])]
        ring = next(r for r in mol.GetRingInfo().AtomRings() if via in r)
        floats.append((chain, via, ring, [by_map[int(m)] for m in att["to"]]))
    if floats:
        rw = Chem.RWMol(mol)
        for chain, via, _, _ in floats:
            rw.RemoveBond(chain, via)
            for i in (chain, via):  # the bond is only hidden, not broken: no radical dots, no extra H
                a = rw.GetAtomWithIdx(i)
                a.SetNumRadicalElectrons(0)
                a.SetNoImplicit(True)
        mol = rw.GetMol()
        Chem.SanitizeMol(mol)
        for a in mol.GetAtoms():
            a.SetNumRadicalElectrons(0)

    drawer = rdMolDraw2D.MolDraw2DSVG(-1, -1)
    opts = drawer.drawOptions()
    opts.useBWAtomPalette()
    opts.clearBackground = False
    opts.bondLineWidth = 1.5
    opts.fixedBondLength = 30
    opts.padding = 0.12
    opts.fontFile = ""
    opts.annotationFontScale = 0.6
    _label_deuterium(mol)
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    # Bonds printed broken/dashed (e.g. "combined with" positions): [[map, map], …] → dashed strokes.
    for pair in node.get("dashed") or []:
        bond = mol.GetBondBetweenAtoms(by_map[int(pair[0])], by_map[int(pair[1])])
        if bond is not None:
            svg = re.sub(rf"(<path class='bond-{bond.GetIdx()} [^']*' d='[^']*' style=')", r"\1stroke-dasharray:3,2.5;", svg)
    extra = []
    width = re.search(r"stroke-width:([\d.]+)px", svg)
    stroke = width.group(1) if width else "2.0"
    font = drawer.FontSize()
    for idx, suffix in greek.items():
        p = drawer.GetDrawCoords(idx)
        # after the drawn "R": about half a glyph right of the atom centre, dropped as a subscript
        extra.append(f"<text x='{p.x + font * 0.30:.1f}' y='{p.y + font * 0.72:.1f}' font-size='{font * 0.68:.1f}' "
                     f"font-family='sans-serif' fill='#000000'>{suffix}</text>")
    for idx, text in greek_notes.items():
        p = drawer.GetDrawCoords(idx)
        extra.append(f"<text x='{p.x + font * 0.35:.1f}' y='{p.y - font * 0.45:.1f}' font-size='{font * 0.62:.1f}' "
                     f"font-family='sans-serif' fill='#000000'>{text}</text>")
    for chain, via, ring, candidates in floats:
        pts = {i: drawer.GetDrawCoords(i) for i in ring}
        cx = sum(p.x for p in pts.values()) / len(ring)
        cy = sum(p.y for p in pts.values()) / len(ring)
        c = drawer.GetDrawCoords(chain)
        # the ring edge the printed bond crosses: from `via` to its neighbouring candidate nearest the chain atom
        nbrs = [n.GetIdx() for n in mol.GetAtomWithIdx(via).GetNeighbors() if n.GetIdx() in candidates and n.GetIdx() in ring]
        other = min(nbrs, key=lambda n: (pts[n].x - c.x) ** 2 + (pts[n].y - c.y) ** 2) if nbrs else via
        mx, my = (pts[via].x + pts[other].x) / 2, (pts[via].y + pts[other].y) / 2
        ex, ey = mx + (cx - mx) * 0.38, my + (cy - my) * 0.38
        extra.append(f"<path d='M {c.x:.1f},{c.y:.1f} L {ex:.1f},{ey:.1f}' "
                     f"style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:butt' />")
    svg = svg.replace("</svg>", "\n".join(extra) + "\n</svg>")
    if highlight:
        # The book's shaded circles (the part a text is about): soft discs under the atoms, drawn before the
        # bonds so the structure sits on top. Text colour at low opacity keeps them right in both themes.
        discs, bounds = [], []
        for group in highlight:
            pts = [drawer.GetDrawCoords(i) for i in group]
            cx, cy = sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)
            r = max(((p.x - cx) ** 2 + (p.y - cy) ** 2) ** 0.5 for p in pts) + font * 1.1
            discs.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r:.1f}' fill='#000000' fill-opacity='0.13' />")
            bounds.append((cx - r, cy - r, cx + r, cy + r))
        svg = re.sub(r"(<!-- END OF HEADER -->)", lambda m: m.group(1) + "\n" + "\n".join(discs), svg, count=1)
        # grow the canvas so no disc is clipped at the edge
        w, h = (float(v) for v in re.search(r"viewBox='0 0 ([\d.]+) ([\d.]+)'", svg).groups())
        x0 = min([0.0] + [b[0] - 2 for b in bounds]); y0 = min([0.0] + [b[1] - 2 for b in bounds])
        x1 = max([w] + [b[2] + 2 for b in bounds]); y1 = max([h] + [b[3] + 2 for b in bounds])
        svg = re.sub(r"width='[\d.]+px' height='[\d.]+px' viewBox='0 0 [\d.]+ [\d.]+'",
                     f"width='{x1 - x0:.0f}px' height='{y1 - y0:.0f}px' viewBox='{x0:.1f} {y0:.1f} {x1 - x0:.1f} {y1 - y0:.1f}'", svg)
    # Like render_mol: follow the page's ink colour (dark mode), and drop the XML header (it declares iso-8859-1,
    # but the Greek overlays are UTF-8).
    svg = re.sub(r"#000000", "currentColor", svg)
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    path.write_text(svg)


def main() -> None:
    compounds = yaml.safe_load((ROOT / "figures" / "compounds.yaml").read_text())
    out_dir = ROOT / "figures" / "structures"
    out_dir.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None  # optional unit prefix, e.g. "ex-naturstoffe"
    for key, c in compounds.items():
        if only and not key.startswith(f"{only}-"):
            continue
        if not c.get("render_smiles"):
            print(f"{key}: no structure to render ({c.get('status')})")
            continue
        render(c["render_smiles"], out_dir / f"{key}.svg")
    print(f"rendered {'all' if not only else only}")
    (ROOT / "figures" / "compounds.yaml").write_text(yaml.safe_dump(compounds, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
