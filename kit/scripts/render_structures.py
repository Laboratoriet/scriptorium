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
    label = label.replace("‴", "'''").replace("″", "''").replace("′", "'")
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


def _pin(mol: Chem.Mol, cmap: dict) -> None:
    """2D coordinates with some atoms fixed. RDKit's depictor occasionally gives up on a pin set and silently lays the
    molecule out freely; then release one pin at a time (last first) until the rest hold."""
    from rdkit.Geometry import Point2D

    def attempt(pins: dict) -> float:
        rdDepictor.SetPreferCoordGen(False)  # coordMap is honoured by RDKit's own depictor
        rdDepictor.Compute2DCoords(mol, coordMap=pins)
        rdDepictor.SetPreferCoordGen(True)
        conf = mol.GetConformer()
        return max(abs(conf.GetAtomPosition(i).x - q.x) + abs(conf.GetAtomPosition(i).y - q.y) for i, q in pins.items())

    if attempt(cmap) < 0.05:
        return
    # Release the pin whose atom then lands nearest to where it was meant to be.
    best = None
    for drop in cmap:
        pins = {i: q for i, q in cmap.items() if i != drop}
        if attempt(pins) < 0.05:
            p = mol.GetConformer().GetAtomPosition(drop)
            miss = math.hypot(p.x - cmap[drop].x, p.y - cmap[drop].y)
            if best is None or miss < best[0]:
                best = (miss, drop)
    if best:
        attempt({i: q for i, q in cmap.items() if i != best[1]})
        print(f"  pins: released atom {best[1]} (RDKit could not honour all of them; lands {best[0] / 1.5:.2f} bonds off)",
              file=sys.stderr)
    else:
        attempt(cmap)


def _subtree(mol: Chem.Mol, start: int, blocked: int) -> set[int]:
    """Atoms reachable from `start` without passing through `blocked` (the substituent hanging off a bond)."""
    seen, todo = {start}, [start]
    while todo:
        for n in mol.GetAtomWithIdx(todo.pop()).GetNeighbors():
            if n.GetIdx() != blocked and n.GetIdx() not in seen:
                seen.add(n.GetIdx())
                todo.append(n.GetIdx())
    return seen


def _shift_out(mol: Chem.Mol, frm: int, via: int, factor: float) -> None:
    """Move a floating substituent further out along its bond, so the bond can reach into a box or arc as printed."""
    conf = mol.GetConformer()
    a, b = conf.GetAtomPosition(frm), conf.GetAtomPosition(via)
    dx, dy = a.x - b.x, a.y - b.y
    for i in _subtree(mol, frm, via):
        p = conf.GetAtomPosition(i)
        conf.SetAtomPosition(i, Point3D(p.x + dx * factor, p.y + dy * factor, 0))


def _horizontal(mol: Chem.Mol, a: int, b: int) -> None:
    """Rotate so a → b runs left to right, with the rest of the molecule hanging below that line (polymer backbones)."""
    conf = mol.GetConformer()
    pa, pb = conf.GetAtomPosition(a), conf.GetAtomPosition(b)
    angle = -math.atan2(pb.y - pa.y, pb.x - pa.x)
    cos, sin = math.cos(angle), math.sin(angle)
    pts = []
    for i in range(mol.GetNumAtoms()):
        p = conf.GetAtomPosition(i)
        x, y = p.x - pa.x, p.y - pa.y
        pts.append((x * cos - y * sin, x * sin + y * cos))
    others = [y for i, (_, y) in enumerate(pts) if i not in (a, b)]
    flip = -1 if others and sum(others) / len(others) > 0 else 1  # RDKit's y points up; "below" is negative y
    for i, (x, y) in enumerate(pts):
        conf.SetAtomPosition(i, Point3D(x, y * flip, 0))


def _float_line(start, end, labelled: bool, font: float, stroke: str) -> str:
    """A bond drawn from a substituent to a free end point (into a box or arc); starts clear of the atom label."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    d = math.hypot(dx, dy) or 1
    off = font * 0.62 if labelled else 0
    x0, y0 = start[0] + dx / d * off, start[1] + dy / d * off
    return (f"<path d='M {x0:.1f},{y0:.1f} L {end[0]:.1f},{end[1]:.1f}' "
            f"style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:butt' />")


def _bracket(inside, outside, shape: str, half: float, stroke: str, upright: bool = False) -> tuple[str, tuple]:
    """A repeat-unit bracket across the bond inside → outside: '( )' or '[ ]', bowing away from the unit.
    upright: drawn vertical whatever the bond's angle (polymer brackets). Returns the path and its two end points."""
    mx, my = (inside[0] + outside[0]) / 2, (inside[1] + outside[1]) / 2
    dx, dy = outside[0] - inside[0], outside[1] - inside[1]
    d = math.hypot(dx, dy) or 1
    dx, dy = dx / d, dy / d
    if upright:
        dx, dy = (1.0 if dx >= 0 else -1.0), 0.0
    nx, ny = -dy, dx
    e1 = (mx + nx * half, my + ny * half)
    e2 = (mx - nx * half, my - ny * half)
    if shape == "square":
        s = half * 0.32  # serifs point back into the unit
        path = (f"M {e1[0] - dx * s:.1f},{e1[1] - dy * s:.1f} L {e1[0]:.1f},{e1[1]:.1f} "
                f"L {e2[0]:.1f},{e2[1]:.1f} L {e2[0] - dx * s:.1f},{e2[1] - dy * s:.1f}")
    else:
        cx, cy = mx + dx * half * 0.7, my + dy * half * 0.7
        e1 = (e1[0] - dx * half * 0.12, e1[1] - dy * half * 0.12)
        e2 = (e2[0] - dx * half * 0.12, e2[1] - dy * half * 0.12)
        path = f"M {e1[0]:.1f},{e1[1]:.1f} Q {cx:.1f},{cy:.1f} {e2[0]:.1f},{e2[1]:.1f}"
    return (f"<path d='{path}' style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:round;"
            f"stroke-linejoin:round' />"), (e1, e2)


def _labelled(node: dict):
    """A node's molecule with its printed labels: R groups (Greek suffixes kept apart), locants; maps cleared.
    Returns (mol, by_map, greek suffixes by atom, greek locants by atom)."""
    mol = Chem.MolFromSmiles(node["smiles"])
    by_map = {a.GetAtomMapNum(): a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum()}
    greek, greek_notes = {}, {}
    for m, label in (node.get("rgroups") or {}).items():
        text, suffix = _ascii_label(str(label))
        mol.GetAtomWithIdx(by_map[int(m)]).SetProp("_displayLabel", text)
        if suffix:
            greek[by_map[int(m)]] = suffix
    for m, text in (node.get("locants") or {}).items():
        if str(text).isascii():
            mol.GetAtomWithIdx(by_map[int(m)]).SetProp("atomNote", str(text))
        else:
            greek_notes[by_map[int(m)]] = str(text)
    for a in mol.GetAtoms():
        if a.GetAtomicNum() == 0 and a.GetAtomMapNum():
            a.SetIsotope(a.GetAtomMapNum())
        if a.GetAtomMapNum() and a.GetAtomicNum() and not a.GetFormalCharge():
            a.SetNoImplicit(False)
            a.SetNumRadicalElectrons(0)
        a.SetAtomMapNum(0)
    mol.UpdatePropertyCache(strict=False)
    Chem.SanitizeMol(mol)
    return mol, by_map, greek, greek_notes


def render_generic(node: dict, path: Path) -> None:
    """A generic (Markush) structure as printed: R groups on placeholder atoms, ring locants, and optionally the
    book's floating bond (a substituent that may sit at any of several ring positions).

    node: smiles with atom maps ([*:1] for R groups, [c:5] for locant/attachment atoms), rgroups {map: label},
    locants {map: text}, dashed [[map, map] per bond printed broken], highlight [one disc per entry: a map or a list of maps], show_h [maps of atoms whose H is
    drawn as its own atom, e.g. an N–H printed with H above], attach {from: map of the chain atom,
    to: [maps of the possible ring positions],
    via: map of the ring atom the chain is bonded to in `smiles` (where the printed bond crosses into the ring)}.

    Marks for scaffolds a single structure can't show:
    repeat [{atoms: [maps] or bonds: [[in, out], …], label: n, shape: round | square, label_at: bottom | top}]: a repeat unit — brackets
      across the two bonds leaving it, "(CH2)n" on a chain or "[ ]n" on a polymer (end groups: R groups labelled *).
    box {atoms: [maps], float: [{from, via}]}: a rounded box around part of a chain ("any position in here"); each
      float substituent is bonded to `via` in `smiles` but drawn reaching into the box instead.
    arc {atoms: [maps around the variable ring, fusion atom … fusion atom], float: [{from, via}]}: a ring of
      unspecified size, drawn as an arc from fusion atom to fusion atom; a float substituent reaches into it.
    lone_pairs {map: [degrees]}: lone pairs as bars beside the atom label (0 = right, 90 = up).
    clash [{at, toward, size}]: steric repulsion — an open half-circle round `at`, facing `toward`.
    lobes {map: [degrees]}: lone-pair orbital lobes out of the atom.
    wavy [[map, map]]: a wavy bond (configuration left open), drawn from the first atom.
    decor [{from: map, bar | line | arc | text …}]: receptor bars, H-bond lines, open arcs and labels placed relative
      to an atom in bond lengths (x right, y up) — binding-model figures.
    horizontal [map, map]: rotate so this axis runs left to right with the rest hanging below.
    coords {map: [x, y]}: pin atoms (bond lengths, y up) so the drawing keeps the printed orientation.
    repeat entries also take size (bracket half-height in bonds, default 0.34) and upright: true (vertical brackets).
    under {smiles, rgroups, coords, align {map in this node: map in under}}: a second structure drawn faint underneath,
      superimposed on the aligned atoms (e.g. bioisostere overlays); ring {top: [attach, …ring maps in
      order], under: [the six ring maps underneath, in order], toward: under map the second top atom sits next to}
      lays a five-membered ring over the six-membered one.
    """
    from rdkit.Chem import rdchem

    kekule = node.get("kekule") == "as_written"  # draw the double bonds where the SMILES puts them (resonance forms)
    mol = Chem.MolFromSmiles(node["smiles"], sanitize=not kekule)
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
    Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_SETAROMATICITY) if kekule else Chem.SanitizeMol(mol)
    if node.get("stereo_drawing"):
        _apply_drawn_stereo(mol, node["stereo_drawing"])
    show_h = [by_map[int(m)] for m in node.get("show_h") or []]
    if show_h:
        # "H above N, R to the right" as printed: the hydrogen becomes a drawn atom, so the layout places three
        # substituents around N instead of two (same molecule, just an explicit H)
        mol = Chem.AddHs(mol, onlyOnAtoms=show_h)
    under = node.get("under")
    if under:
        # The faint structure is laid out as usual; this one takes its aligned atoms' positions.
        from rdkit.Geometry import Point2D
        umol, u_by_map, u_greek, _ = _labelled(under)
        if under.get("coords"):
            _pin(umol, {u_by_map[int(m)]: Point2D(x * 1.5, y * 1.5) for m, (x, y) in under["coords"].items()})
        else:
            layout(umol)
        uconf = umol.GetConformer()
        upos = lambda m: uconf.GetAtomPosition(u_by_map[int(m)])
        cmap = {by_map[int(a)]: Point2D(upos(b).x, upos(b).y) for a, b in under["align"].items()}
        ring = under.get("ring")
        if ring:
            # A five-membered ring laid over the six-membered one underneath: it shares the attachment vertex and
            # turns towards the hexagon's centre; its first atom after the attachment sits next to `toward`.
            top = [by_map[int(m)] for m in ring["top"]]
            hexagon = [upos(m) for m in ring["under"]]
            px, py = cmap[top[0]].x, cmap[top[0]].y
            hx, hy = sum(q.x for q in hexagon) / 6, sum(q.y for q in hexagon) / 6
            b = math.hypot(hexagon[0].x - hexagon[1].x, hexagon[0].y - hexagon[1].y)
            rc = b / (2 * math.sin(math.radians(36)))
            ux, uy = hx - px, hy - py
            un = math.hypot(ux, uy)
            cx, cy = px + ux / un * rc, py + uy / un * rc
            a0 = math.atan2(py - cy, px - cx)
            tw = upos(ring["toward"])
            step = min((1, -1), key=lambda s: math.hypot(cx + rc * math.cos(a0 + s * math.radians(72)) - tw.x,
                                                         cy + rc * math.sin(a0 + s * math.radians(72)) - tw.y))
            for k, i in enumerate(top[1:], 1):
                a = a0 + step * math.radians(72) * k
                cmap[i] = Point2D(cx + rc * math.cos(a), cy + rc * math.sin(a))
        _pin(mol, cmap)
    elif node.get("coords"):
        # Pinned atoms, in bond lengths (x right, y up), so the drawing keeps the printed orientation.
        from rdkit.Geometry import Point2D
        _pin(mol, {by_map[int(m)]: Point2D(x * 1.5, y * 1.5) for m, (x, y) in node["coords"].items()})
    else:
        layout(mol)
    if node.get("horizontal"):
        _horizontal(mol, *(by_map[int(m)] for m in node["horizontal"]))

    # Box and arc substituents: pushed out a little, then their bond is hidden and redrawn reaching in.
    box = node.get("box")
    as_list_ = lambda v: v if isinstance(v, list) else [v] if v else []
    rings_drawn = [("arc", k, a) for k, a in enumerate(as_list_(node.get("arc")))] + \
                  [("circle", k, c) for k, c in enumerate(as_list_(node.get("circle")))]
    free = []  # (from atom, via atom, "box" | ("arc"|"circle", index))
    for f in (box or {}).get("float") or []:
        frm, via = by_map[int(f["from"])], by_map[int(f["via"])]
        _shift_out(mol, frm, via, f.get("extend", 0.45))
        free.append((frm, via, "box"))
    for kind, k, mark in rings_drawn:
        for f in mark.get("float") or []:
            frm, via = by_map[int(f["from"])], by_map[int(f["via"])]
            _shift_out(mol, frm, via, f.get("extend", 0.45))
            free.append((frm, via, (kind, k)))
    if free:
        rw = Chem.RWMol(mol)
        for frm, via, _ in free:
            rw.RemoveBond(frm, via)
            for i in (frm, via):
                rw.GetAtomWithIdx(i).SetNumRadicalElectrons(0)
                rw.GetAtomWithIdx(i).SetNoImplicit(True)
        mol = rw.GetMol()
        Chem.SanitizeMol(mol)
        for a in mol.GetAtoms():
            a.SetNumRadicalElectrons(0)

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

    if node.get("inner_circle"):
        # Benzene drawn with a circle: its ring bonds are drawn plain, the circle is added after drawing
        rw = Chem.RWMol(mol)
        for ring_maps in node["inner_circle"]:
            ring = [by_map[int(m)] for m in ring_maps]
            for a, b in zip(ring, ring[1:] + ring[:1]):
                bond = rw.GetBondBetweenAtoms(a, b)
                if bond is not None:
                    bond.SetBondType(Chem.BondType.SINGLE)
                    bond.SetIsAromatic(False)
            for i in ring:
                rw.GetAtomWithIdx(i).SetIsAromatic(False)
                rw.GetAtomWithIdx(i).SetNoImplicit(True)
        mol = rw.GetMol()
        mol.UpdatePropertyCache(strict=False)
    for a_, b_ in node.get("wavy") or []:  # stereo left open: drawn as a wavy bond
        bond = mol.GetBondBetweenAtoms(by_map[int(a_)], by_map[int(b_)])
        if bond is not None:
            if bond.GetBeginAtomIdx() != by_map[int(a_)]:
                rw = Chem.RWMol(mol); rw.RemoveBond(by_map[int(b_)], by_map[int(a_)])
                rw.AddBond(by_map[int(a_)], by_map[int(b_)], Chem.BondType.SINGLE); mol = rw.GetMol()
                mol.UpdatePropertyCache(strict=False)
                bond = mol.GetBondBetweenAtoms(by_map[int(a_)], by_map[int(b_)])
            bond.SetBondDir(Chem.BondDir.UNKNOWN)
    n_atoms, n_bonds = mol.GetNumAtoms(), mol.GetNumBonds()
    if under:
        mol = Chem.CombineMols(mol, umol)
        for i, s in u_greek.items():
            greek[i + n_atoms] = s

    drawer = rdMolDraw2D.MolDraw2DSVG(-1, -1)
    opts = drawer.drawOptions()
    opts.useBWAtomPalette()
    opts.clearBackground = False
    opts.bondLineWidth = 1.5
    opts.fixedBondLength = 30
    opts.padding = 0.12
    opts.fontFile = ""
    opts.annotationFontScale = 0.6
    opts.flagCloseContactsDist = -1  # overlays and pinned layouts put atoms close on purpose
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
        # from the edge of a label ("MeO", "X"), not through it
        extra.append(_float_line((c.x, c.y), (ex, ey), mol.GetAtomWithIdx(chain).HasProp("_displayLabel")
                                 or mol.GetAtomWithIdx(chain).GetAtomicNum() != 6, font * (1.2 if len(
                                     mol.GetAtomWithIdx(chain).GetPropsAsDict().get("_displayLabel", "")) > 2 else 1), stroke))
    bond_px = 30.0  # fixedBondLength
    marks = []  # bounding boxes of the drawn marks (box, arc, brackets), to fit the canvas around them
    labelled = lambda i: mol.GetAtomWithIdx(i).GetAtomicNum() not in (6,) or mol.GetAtomWithIdx(i).HasProp("_displayLabel")
    xy = lambda i: (drawer.GetDrawCoords(i).x, drawer.GetDrawCoords(i).y)
    if box:
        pts = [xy(by_map[int(m)]) for m in box["atoms"]]
        if box.get("size"):  # a fixed box (in bond lengths) centred on its atoms: "any ring" as a rounded square
            w, h = (s * bond_px for s in box["size"])
            mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            x0, y0, x1, y1 = mx - w / 2, my - h / 2, mx + w / 2, my + h / 2
        else:
            pad_x, pad_y = font * box.get("pad", 1.0), font * box.get("pad", 1.0) * 1.1
            x0, y0 = min(p[0] for p in pts) - pad_x, min(p[1] for p in pts) - pad_y
            x1, y1 = max(p[0] for p in pts) + pad_x, max(p[1] for p in pts) + pad_y
        marks.append((x0, y0, x1, y1))
        extra.append(f"<rect x='{x0:.1f}' y='{y0:.1f}' width='{x1 - x0:.1f}' height='{y1 - y0:.1f}' rx='{font * box.get('radius', 0.55):.1f}' "
                     f"style='fill:none;stroke:#000000;stroke-width:{stroke}px' />")
        for frm, via, kind in free:
            if kind != "box":
                continue
            (ax, ay), (bx, by) = xy(frm), xy(via)
            dx, dy = bx - ax, by - ay
            d = math.hypot(dx, dy) or 1
            # where the bond meets the box, then half a bond inside it
            ts = [t for t in ((x0 - ax) / dx if dx else None, (x1 - ax) / dx if dx else None,
                              (y0 - ay) / dy if dy else None, (y1 - ay) / dy if dy else None) if t and t > 0]
            t_in = min(t for t in ts if x0 - 0.5 <= ax + dx * t <= x1 + 0.5 and y0 - 0.5 <= ay + dy * t <= y1 + 0.5)
            depth = bond_px * 0.5 / d
            end_t = min(t_in + depth, 1.0)
            extra.append(_float_line((ax, ay), (ax + dx * end_t, ay + dy * end_t), labelled(frm), font, stroke))
    # Label positions on the drawing: arcs and circles leave a gap where they pass through one (the N of a ring).
    label_pts = [xy(i) for i in range(n_atoms) if labelled(i)]

    def curve(cx, cy, r, a0, span, steps=60):
        segs, cur = [], []
        for k in range(steps + 1):
            a = a0 + span * k / steps
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if any(math.hypot(x - lx, y - ly) < font * 0.62 for lx, ly in label_pts):
                if len(cur) > 1:
                    segs.append(cur)
                cur = []
            else:
                cur.append((x, y))
        if len(cur) > 1:
            segs.append(cur)
        return " ".join("M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in s) for s in segs)

    for kind, k, mark in rings_drawn:
        ring = [by_map[int(m)] for m in mark["atoms"]]
        pts = [xy(i) for i in ring]
        ctr = [xy(by_map[int(m)]) for m in mark.get("center") or mark["atoms"]]
        cx, cy = sum(p[0] for p in ctr) / len(ctr), sum(p[1] for p in ctr) / len(ctr)
        r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in pts) / len(pts)
        # hide the ring's own bonds (and, for a circle, its closing bond); the curve stands in for them
        pairs = list(zip(ring, ring[1:])) + ([(ring[-1], ring[0])] if kind == "circle" else [])
        for a, b in pairs:
            bond = mol.GetBondBetweenAtoms(a, b)
            if bond is not None:
                svg = re.sub(rf"<path class='bond-{bond.GetIdx()} [^>]*/>\n?", "", svg)
        # and RDKit's unclassed corner patches at the hidden atoms (they'd show as ticks on the curve)
        hidden = [xy(i) for i in ring if not labelled(i)]

        def drop_join(m: re.Match) -> str:
            x, y = float(m.group(1)), float(m.group(2))
            return "" if any(math.hypot(x - hx, y - hy) < 3 for hx, hy in hidden) else m.group(0)
        svg = re.sub(r"<path d='M [\d.]+,[\d.]+ L ([\d.]+),([\d.]+) L [\d.]+,[\d.]+' [^>]*/>\n?", drop_join, svg)
        if kind == "circle":
            d = curve(cx, cy, r, 0.0, 2 * math.pi, 96)
        else:
            ang = lambda p: math.atan2(p[1] - cy, p[0] - cx)
            a0, a1, amid = ang(pts[0]), ang(pts[-1]), ang(pts[len(pts) // 2])
            span = (a1 - a0) % (2 * math.pi)
            if not (0 < (amid - a0) % (2 * math.pi) < span):  # go round the other way, through the ring's middle atom
                span -= 2 * math.pi
            d = curve(cx, cy, r, a0, span)
        extra.append(f"<path d='{d}' style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:butt' />")
        marks.append((cx - r, cy - r, cx + r, cy + r))
        for frm, via, tag in free:
            if tag != (kind, k):
                continue
            ax, ay = xy(frm)
            dx, dy = ax - cx, ay - cy
            d0 = math.hypot(dx, dy) or 1
            end_ = (cx + dx / d0 * r * mark.get("depth", 0.72), cy + dy / d0 * r * mark.get("depth", 0.72))
            extra.append(_float_line((ax, ay), end_, labelled(frm), font, stroke))
    # An aromatic ring drawn with a circle inside (the book's benzene notation)
    for ring_maps in node.get("inner_circle") or []:
        pts = [xy(by_map[int(m)]) for m in ring_maps]
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        r = sum(math.hypot(p[0] - cx, p[1] - cy) for p in pts) / len(pts) * 0.6
        extra.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r:.1f}' style='fill:none;stroke:#000000;stroke-width:{stroke}px' />")
    # Lone pairs drawn as bars beside an atom label (Lewis style): {map: [angles in degrees, 0 = right, 90 = up]}
    for m, angles in (node.get("lone_pairs") or {}).items():
        ax, ay = xy(by_map[int(m)])
        for deg in angles:
            ux, uy = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
            cx, cy = ax + ux * font * 0.8, ay + uy * font * 0.8
            h = font * 0.3
            extra.append(f"<path d='M {cx - uy * h:.1f},{cy + ux * h:.1f} L {cx + uy * h:.1f},{cy - ux * h:.1f}' "
                         f"style='fill:none;stroke:#000000;stroke-width:{float(stroke) * 0.9:.2f}px;stroke-linecap:round' />")
    # Lone-pair lobes (orbital drawings): {map: [degrees]} — a teardrop out of the atom label per lone pair
    for m, angles in (node.get("lobes") or {}).items():
        ax, ay = xy(by_map[int(m)])
        for deg in angles:
            dx, dy = math.cos(math.radians(deg)), -math.sin(math.radians(deg))
            nx, ny = -dy, dx
            L, W = bond_px * 0.62, bond_px * 0.24
            bx_, by_ = ax + dx * font * 0.55, ay + dy * font * 0.55
            P = lambda a, b: f"{bx_ + dx * a + nx * b:.1f},{by_ + dy * a + ny * b:.1f}"
            extra.append(f"<path d='M {bx_:.1f},{by_:.1f} C {P(L * 0.3, W)} {P(L, W * 0.95)} {P(L * 1.02, 0)} "
                         f"C {P(L, -W * 0.95)} {P(L * 0.3, -W)} {bx_:.1f},{by_:.1f} Z' "
                         f"style='fill:none;stroke:#000000;stroke-width:{float(stroke) * 0.9:.2f}px;stroke-linejoin:round' />")
            marks.append((min(bx_, bx_ + dx * L) - W, min(by_, by_ + dy * L) - W, max(bx_, bx_ + dx * L) + W, max(by_, by_ + dy * L) + W))
    # Decoration placed relative to an atom, in bond lengths (x right, y up): receptor bars, H-bond lines, labels, arcs
    for d in node.get("decor") or []:
        ax, ay = xy(by_map[int(d["from"])])
        P = lambda q: (ax + q[0] * bond_px, ay - q[1] * bond_px)
        if "bar" in d:
            (cx, cy), (w, h) = P(d["bar"]), (d.get("size", [2.2, 0.35])[0] * bond_px, d.get("size", [2.2, 0.35])[1] * bond_px)
            extra.append(f"<rect x='{cx - w / 2:.1f}' y='{cy - h / 2:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{min(w, h) * 0.3:.1f}' "
                         f"style='fill:#000000;fill-opacity:0.28;stroke:#000000;stroke-width:{stroke}px' />")
            marks.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        elif "line" in d:
            pts = [P(q) for q in d["line"]]
            dash = "stroke-dasharray:4,3;" if d.get("dash") else ""
            extra.append("<path d='M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                         f"' style='fill:none;stroke:#000000;stroke-width:{stroke}px;{dash}stroke-linecap:round' />")
            marks.append((min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)))
        elif "arc" in d:
            (cx, cy), r = P(d["arc"]), d.get("r", 1.0) * bond_px
            a0, a1 = math.radians(d.get("from_deg", 90)), math.radians(d.get("to_deg", 270))
            pts = [(cx + r * math.cos(a0 + (a1 - a0) * k / 40), cy - r * math.sin(a0 + (a1 - a0) * k / 40)) for k in range(41)]
            if d.get("fill"):  # a shaded region behind the arc, as some binding models print it
                extra.insert(0, f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r:.1f}' fill='#000000' fill-opacity='0.1' />")
            extra.append("<path d='M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                         f"' style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:round' />")
            marks.append((cx - r, cy - r, cx + r, cy + r))
        elif "text" in d:
            (tx, ty), size = P(d["at"]), font * d.get("size", 1.0)
            anchor = d.get("anchor", "middle")
            lines_ = str(d["text"]).split("\n")
            for k, line in enumerate(lines_):
                y_ = ty + (k - (len(lines_) - 1) / 2) * size * 1.2 + size * 0.35
                extra.append(f"<text x='{tx:.1f}' y='{y_:.1f}' font-size='{size:.1f}' text-anchor='{anchor}' "
                             f"font-family='sans-serif' fill='#000000'>{line}</text>")
            w = max(len(l) for l in lines_) * size * 0.55
            x0_ = tx - w if anchor == "end" else tx - w / 2 if anchor == "middle" else tx
            marks.append((x0_, ty - len(lines_) * size * 0.7, x0_ + w, ty + len(lines_) * size * 0.7))
    # Steric repulsion: an open half-circle round an atom, on the side facing the group it collides with
    for c in node.get("clash") or []:
        (ax, ay), (bx, by) = xy(by_map[int(c["at"])]), xy(by_map[int(c["toward"])])
        a0 = math.atan2(by - ay, bx - ax)
        r = bond_px * c.get("size", 0.5)
        pts = [(ax + r * math.cos(a0 + math.radians(s)), ay + r * math.sin(a0 + math.radians(s))) for s in range(-75, 76, 5)]
        extra.append("<path d='M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                     f"' style='fill:none;stroke:#000000;stroke-width:{stroke}px;stroke-linecap:round' />")
        marks.append((ax - r, ay - r, ax + r, ay + r))
    # A dashed axis through two atoms, running on past both (a symmetry line)
    axis = node.get("axis")
    if axis:
        (ax, ay), (bx, by) = (xy(by_map[int(m)]) for m in axis["through"])
        ext = axis.get("extend", 1.0) * bond_px
        dx, dy = bx - ax, by - ay
        d0 = math.hypot(dx, dy) or 1
        p0 = (ax - dx / d0 * ext, ay - dy / d0 * ext)
        p1 = (bx + dx / d0 * ext, by + dy / d0 * ext)
        extra.append(f"<path d='M {p0[0]:.1f},{p0[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f}' "
                     f"style='fill:none;stroke:#000000;stroke-width:{float(stroke) * 0.8:.2f}px;stroke-dasharray:4,3' />")
        marks.append((min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])))
    for unit in node.get("repeat") or []:
        if unit.get("bonds"):  # [[inside, outside], …]: the bonds the brackets cross, when the unit has side chains
            crossing = [(by_map[int(a)], by_map[int(b)]) for a, b in unit["bonds"]]
            inside = {a for a, _ in crossing}
        else:
            inside = {by_map[int(m)] for m in unit["atoms"]}
            crossing = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()
                        if (b.GetBeginAtomIdx() in inside) != (b.GetEndAtomIdx() in inside)]
        ends = []
        if unit.get("around"):
            # "( )n" drawn either side of the repeating atom itself, upright, as the book prints a CH2 unit at a bend
            cx_ = sum(xy(i)[0] for i in inside) / len(inside)
            cy_ = sum(xy(i)[1] for i in inside) / len(inside)
            w_ = bond_px * unit.get("width", 0.42)
            crossing = []
            for sgn in (-1, 1):
                bracket, e = _bracket((cx_, cy_), (cx_ + sgn * 2 * w_, cy_), unit.get("shape", "round"),
                                      bond_px * unit.get("size", 0.34), stroke, True)
                extra.append(bracket)
                ends.append((cx_ + sgn * w_, e))
                marks.append((min(e[0][0], e[1][0]), min(e[0][1], e[1][1]), max(e[0][0], e[1][0]) + font, max(e[0][1], e[1][1]) + font))
        for a, b in crossing:
            i, o = (a, b) if a in inside else (b, a)
            bracket, e = _bracket(xy(i), xy(o), unit.get("shape", "round"), bond_px * unit.get("size", 0.34), stroke,
                                  unit.get("upright", False))
            extra.append(bracket)
            ends.append((xy(o)[0], e))
            marks.append((min(e[0][0], e[1][0]), min(e[0][1], e[1][1]), max(e[0][0], e[1][0]) + font, max(e[0][1], e[1][1]) + font))
        if unit.get("label") and ends:
            _, (e1, e2) = max(ends)  # the bracket on the right carries the subscript
            at = min((e1, e2), key=lambda e: e[1]) if unit.get("label_at") == "top" else max((e1, e2), key=lambda e: e[1])
            extra.append(f"<text x='{at[0] + font * 0.3:.1f}' y='{at[1] + (font * 0.05 if unit.get('label_at') == 'top' else font * 0.6):.1f}' "
                         f"font-size='{font * 0.72:.1f}' font-family='sans-serif' fill='#000000'>{unit['label']}</text>")
    svg = svg.replace("</svg>", "\n".join(extra) + "\n</svg>")
    if under:
        # The superimposed reference structure: same drawing, faint, so the overlaid analogue reads on top of it.
        def fade(m: re.Match) -> str:
            ids = m.group(1).split()
            b = [int(c[5:]) for c in ids if c.startswith("bond-")]
            a = [int(c[5:]) for c in ids if c.startswith("atom-")]
            under_part = (b and b[0] >= n_bonds) or (not b and a and a[0] >= n_atoms)
            return m.group(0) + (" opacity='0.3'" if under_part else "")
        svg = re.sub(r"class='([^']*)'", fade, svg)
        # RDKit's little corner patches at ring vertices carry no class: fade the ones on the faint structure's atoms
        centres = [xy(i) for i in range(mol.GetNumAtoms())]

        def fade_join(m: re.Match) -> str:
            x, y = float(m.group(2)), float(m.group(3))
            nearest = min(range(len(centres)), key=lambda i: (centres[i][0] - x) ** 2 + (centres[i][1] - y) ** 2)
            return m.group(0).replace("<path ", "<path opacity='0.3' ", 1) if nearest >= n_atoms else m.group(0)
        svg = re.sub(r"<path d='M [\d.]+,[\d.]+ L ([\d.]+),([\d.]+) L [\d.]+,[\d.]+'".replace("([\d.]+),([\d.]+)", "(([\d.]+),([\d.]+))"),
                     fade_join, svg)
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
    if marks:
        # Boxes, arcs and brackets can reach past RDKit's canvas: grow it so nothing is clipped.
        vx, vy, vw, vh = (float(v) for v in re.search(r"viewBox='([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)'", svg).groups())
        x0 = min([vx] + [b[0] - 3 for b in marks]); y0 = min([vy] + [b[1] - 3 for b in marks])
        x1 = max([vx + vw] + [b[2] + 3 for b in marks]); y1 = max([vy + vh] + [b[3] + 3 for b in marks])
        svg = re.sub(r"width='[\d.]+px' height='[\d.]+px' viewBox='[-\d.]+ [-\d.]+ [\d.]+ [\d.]+'",
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
