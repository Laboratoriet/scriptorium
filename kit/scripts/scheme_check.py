"""Check the molecules of a scheme spec against PubChem (by printed name) → status per node.

Usage: scriptorium run scheme_check work/schemes/p0951-1.yaml [...]
Status: verified (full InChIKey when stereo is drawn, else connectivity) · mismatch · not-found · unnamed · generic.
Answers are cached with the structure pass's cache (work/pubchem_cache.json).
"""
import sys
from pathlib import Path

import yaml
from rdkit import Chem, RDLogger

sys.path.insert(0, str(Path(__file__).parent))
from verify_compounds import pubchem  # noqa: E402
from scheme_preview import node_mol  # noqa: E402

RDLogger.DisableLog("rdApp.*")


def check(path: Path) -> dict:
    spec = yaml.safe_load(path.read_text())
    out = {}
    for key, n in (spec.get("nodes") or {}).items():
        if not n.get("smiles"):
            continue
        mol = node_mol(n)
        if mol is None or any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
            out[key] = {"status": "generic"}
            continue
        if not n.get("pubchem_query"):
            out[key] = {"status": "unnamed"}
            continue
        hit = pubchem(n["pubchem_query"])
        if not hit:
            out[key] = {"status": "not-found"}
            continue
        ik = Chem.MolToInchiKey(mol)
        # Full key only when both sides carry stereo (PubChem's entry for a name may be the racemate).
        full = bool(n.get("stereo_drawing")) and hit["InChIKey"][15:25] != "UHFFFAOYSA"
        same = hit["InChIKey"] == ik if full else hit["InChIKey"][:14] == ik[:14]
        out[key] = {"status": "verified" if same else "mismatch", "cid": hit.get("CID"),
                    **({} if same else {"pubchem_smiles": hit.get("SMILES") or hit.get("IsomericSMILES")})}
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        res = check(Path(arg))
        print(Path(arg).stem, {k: v["status"] for k, v in res.items()})
        for k, v in res.items():
            if v["status"] == "mismatch":
                print("   MISMATCH", k, v)
