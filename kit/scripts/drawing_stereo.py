"""Stereochemistry from a description of the printed drawing.

Agents don't assign R/S themselves (easy to get wrong — the book's own 1a/1b are
drawn wrong). They describe each drawn stereocentre instead, and RDKit derives
the configuration:

  stereo_drawing:
    mapped_smiles: "c1cc[c:9]cc1[CH:1]([OH:2])[CH2:3]N"   # atom maps on the centre and its drawn neighbours
    centres:
      - atom: 1                                  # map number of the stereocentre
        neighbours: {9: dl, 2: u, 3: dr}         # direction of each drawn bond from the centre
        wedge: [2, wedge]                        # which bond is wedged ("wedge" = bold, "hash" = dashed)

Directions: u, d, ul, ur, dl, dr, l, r (as seen on the page; hexagon-grid angles).
"""
from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Geometry import Point3D

DIRS = {
    "u": (0, 1), "d": (0, -1), "l": (-1, 0), "r": (1, 0),
    "ur": (0.866, 0.5), "ul": (-0.866, 0.5), "dr": (0.866, -0.5), "dl": (-0.866, -0.5),
}


def _chiral_tag(base: Chem.Mol, idx: dict, centre: dict) -> tuple[Chem.ChiralType, list[int]]:
    """Chiral tag of one drawn centre, derived on its own copy of the molecule.

    One centre per copy: when two drawn centres are bonded, placing the second one
    would move the first (it is the second's neighbour) and corrupt its geometry.
    Returns the tag and the neighbour order it refers to."""
    mol = Chem.RWMol(base)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    c = idx[centre["atom"]]
    for nb_map in centre["neighbours"]:
        if mol.GetBondBetweenAtoms(c, idx[int(nb_map)]) is None:
            raise ValueError(f"neighbour {nb_map} is not bonded to stereocentre {centre['atom']}")
    conf.SetAtomPosition(c, Point3D(0, 0, 0))
    for nb_map, direction in centre["neighbours"].items():
        dx, dy = DIRS[direction]
        conf.SetAtomPosition(idx[int(nb_map)], Point3D(dx, dy, 0))

    target, kind = centre["wedge"]
    t = idx[int(target)]
    bond = mol.GetBondBetweenAtoms(c, t)
    if bond.GetBeginAtomIdx() != c:  # wedge must start at the stereocentre
        order = bond.GetBondType()
        mol.RemoveBond(c, t)
        mol.AddBond(c, t, order)
        bond = mol.GetBondBetweenAtoms(c, t)
    bond.SetBondDir(Chem.BondDir.BEGINWEDGE if kind == "wedge" else Chem.BondDir.BEGINDASH)

    mol = mol.GetMol()
    Chem.AssignChiralTypesFromBondDirs(mol)
    atom = mol.GetAtomWithIdx(c)
    return atom.GetChiralTag(), [n.GetIdx() for n in atom.GetNeighbors()]


def _odd_permutation(a: list[int], b: list[int]) -> bool:
    """True if reordering a into b takes an odd number of swaps."""
    a, swaps = list(a), 0
    for i, x in enumerate(b):
        j = a.index(x)
        if j != i:
            a[i], a[j] = a[j], a[i]
            swaps += 1
    return swaps % 2 == 1


def mol_from_drawing(mapped_smiles: str, centres: list[dict]) -> Chem.Mol:
    # Keep explicit hydrogens: a drawn, wedged H (e.g. "[H:11]" on a bridgehead) is a neighbour too.
    params = Chem.SmilesParserParams()
    params.removeHs = False
    base = Chem.MolFromSmiles(mapped_smiles, params)
    idx = {a.GetAtomMapNum(): a.GetIdx() for a in base.GetAtoms() if a.GetAtomMapNum()}
    tags = {idx[centre["atom"]]: _chiral_tag(base, idx, centre) for centre in centres}

    # A chiral tag refers to the atom's neighbour order; re-adding the wedge bond in a copy
    # can change that order, so flip the tag when the orders differ by an odd permutation.
    mol = Chem.Mol(base)
    flip = {Chem.ChiralType.CHI_TETRAHEDRAL_CW: Chem.ChiralType.CHI_TETRAHEDRAL_CCW,
            Chem.ChiralType.CHI_TETRAHEDRAL_CCW: Chem.ChiralType.CHI_TETRAHEDRAL_CW}
    for c, (tag, order) in tags.items():
        atom = mol.GetAtomWithIdx(c)
        here = [n.GetIdx() for n in atom.GetNeighbors()]
        atom.SetChiralTag(flip.get(tag, tag) if _odd_permutation(order, here) else tag)
    # Atom maps take part in RDKit's atom ranking — clear them before assigning R/S.
    for a in mol.GetAtoms():
        a.SetAtomMapNum(0)
    mol = Chem.RemoveHs(mol)  # chiral tags are carried over to the implicit H
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    return mol


def cip_labels(mol: Chem.Mol) -> list[str]:
    return [f"{a.GetSymbol()}{a.GetIdx()}:{a.GetProp('_CIPCode')}" for a in mol.GetAtoms() if a.HasProp("_CIPCode")]


if __name__ == "__main__":
    # Self-test against chapter 2's verified findings (run after any change here).
    cases = [
        # 1a as printed: CH2 up-left, NH2 up-right, CH3 straight down on a hash → R (book says S)
        ("1a as printed", "c1ccccc1[CH2:2][CH:1]([CH3:3])[NH2:4]",
         [{"atom": 1, "neighbours": {2: "ul", 4: "ur", 3: "d"}, "wedge": [3, "hash"]}], ["R"]),
        # 3 ephedrine as printed → (1R,2S)
        ("3 ephedrine", "c1cccc[c:9]1[CH:1]([OH:2])[CH:3]([CH3:4])[NH:5]C",
         [{"atom": 1, "neighbours": {9: "dl", 2: "u", 3: "dr"}, "wedge": [2, "wedge"]},
          {"atom": 3, "neighbours": {1: "ul", 5: "ur", 4: "d"}, "wedge": [4, "wedge"]}], ["R", "S"]),
        # ch03 23a cis-(4S,5R)-4-methylaminorex: two bonded centres (regression: placing one moved the other)
        ("ch03 23a 4-methylaminorex", "NC1=[N:5][CH:2]([CH3:6])[CH:1]([c:4]2ccccc2)[O:3]1",
         [{"atom": 1, "neighbours": {3: "u", 4: "dl", 2: "dr"}, "wedge": [4, "wedge"]},
          {"atom": 2, "neighbours": {1: "ul", 5: "ur", 6: "d"}, "wedge": [6, "wedge"]}], ["S", "R"]),
    ]
    for name, smiles, centres, expected in cases:
        got = [label[-1] for label in cip_labels(mol_from_drawing(smiles, centres))]
        print(f"{name}: {got} {'ok' if got == expected else f'FAIL (expected {expected})'}")
