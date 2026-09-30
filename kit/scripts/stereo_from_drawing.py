"""Derive CIP labels (R/S) from a structure as drawn in the book.

Each drawing is described by the positions of the stereocentre's neighbours
(in hexagon-grid directions) and which bond is wedged (toward viewer) or
hashed (away). RDKit then assigns R/S, so we can check the book's own label.
"""
from rdkit import Chem
from rdkit.Chem import AllChem, rdDepictor
from rdkit.Geometry import Point3D

DIRS = {  # unit steps on the drawing
    "ur": (0.866, 0.5), "dr": (0.866, -0.5), "ul": (-0.866, 0.5),
    "dl": (-0.866, -0.5), "u": (0, 1), "d": (0, -1),
}


def cip_from_drawing(smiles: str, centres: dict) -> dict:
    """centres: {atom_idx: {neighbour_idx: direction, ...}, 'wedge': (i, j, 'wedge'|'hash')}"""
    mol = Chem.MolFromSmiles(smiles)
    rdDepictor.Compute2DCoords(mol)
    conf = mol.GetConformer()
    for centre, spec in centres.items():
        conf.SetAtomPosition(centre, Point3D(0, 0, 0))
        for nb, direction in spec["neighbours"].items():
            x, y = DIRS[direction]
            conf.SetAtomPosition(nb, Point3D(x, y, 0))
        i, j, kind = spec["wedge"]
        bond = mol.GetBondBetweenAtoms(i, j)
        if bond.GetBeginAtomIdx() != i:
            raise ValueError("wedge must start at the stereocentre; reorder SMILES")
        bond.SetBondDir(Chem.BondDir.BEGINWEDGE if kind == "wedge" else Chem.BondDir.BEGINDASH)
    Chem.AssignChiralTypesFromBondDirs(mol)
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    labels = {a.GetIdx(): a.GetProp("_CIPCode") for a in mol.GetAtoms() if a.HasProp("_CIPCode")}
    return labels, Chem.MolToSmiles(mol), Chem.MolToInchiKey(mol)


# SMILES atom order is chosen so each stereocentre is written before its wedged partner.
DRAWINGS = {
    # 1a: Ph–CH2 (up-left of C*), NH2 up-right, CH3 straight down, hashed
    "1a": ("c1ccccc1CC(C)N", {7: {"neighbours": {6: "ul", 9: "ur", 8: "d"}, "wedge": (7, 8, "hash")}}),
    "1b": ("c1ccccc1CC(C)N", {7: {"neighbours": {6: "ul", 9: "ur", 8: "d"}, "wedge": (7, 8, "wedge")}}),
    # 2: aryl down-left of C*, OH straight up (wedge), CH2 down-right
    "2": ("Oc1ccc(cc1O)C(O)CNC", {8: {"neighbours": {4: "dl", 9: "u", 10: "dr"}, "wedge": (8, 9, "wedge")}}),
    # 3: C1 like 2; C2: C1 up-left, N up-right, CH3 straight down (wedge)
    "3": ("c1ccccc1C(O)C(C)NC", {
        6: {"neighbours": {5: "dl", 7: "u", 8: "dr"}, "wedge": (6, 7, "wedge")},
        8: {"neighbours": {6: "ul", 10: "ur", 9: "d"}, "wedge": (8, 9, "wedge")},
    }),
    "8": ("Oc1ccc(cc1O)C(O)CN", {8: {"neighbours": {4: "dl", 9: "u", 10: "dr"}, "wedge": (8, 9, "wedge")}}),
}

if __name__ == "__main__":
    for key, (smi, centres) in DRAWINGS.items():
        labels, can, ikey = cip_from_drawing(smi, centres)
        print(f"{key:3} CIP={labels}  {can}  {ikey}")
