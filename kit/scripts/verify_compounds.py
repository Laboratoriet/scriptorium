"""Verify the structures read from a unit's figures against PubChem.

Usage: scriptorium run verify_compounds <unit-dir>      e.g. ex-naturstoffe

Input:  figures/<unit-dir>/compounds_draft.yaml — written by the structure agents:
  - number: "16a"
    figure: p0027-3
    names_de: ["(-)-[1R,2S]-Ephedrin"]
    pubchem_query: "(-)-ephedrine"   # English/INN name to look up; null if the book gives no name
    smiles: "C[C@H](NC)[C@@H](O)c1ccccc1"   # as DRAWN in the book (stereo only if wedges are drawn)
    stereo_drawn: true

Output: entries merged into figures/compounds.yaml as "<unit-dir>-<number>", each with a status:
  verified    drawing matches PubChem (full InChIKey if stereo is drawn, else connectivity)
  mismatch    drawing and PubChem disagree → needs a human decision (see figures/<unit-dir>/verify_report.md)
  read-twice  no name to check against, but two blind readers drew the same structure
  unverified  no name to check against (and not confirmed by a second reading)
  generic     a Markush drawing (R, X, n …) — no single structure; the original is shown
  not-found   PubChem doesn't know the name (read-twice if both readers agree)
The structure rendered is always the one DRAWN; mismatches are resolved by hand (and get a TN).
"""
import sys
import time
from pathlib import Path

import json
import requests
import yaml
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

sys.path.insert(0, str(Path(__file__).parent))
from drawing_stereo import mol_from_drawing

RDLogger.DisableLog("rdApp.*")
from bookroot import ROOT  # the book project (book.yaml), not the kit
API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/IsomericSMILES,SMILES,InChIKey,MolecularFormula/JSON"
# Answers are kept on disk, so a rerun after PubChem throttling doesn't start over (404s are cached as null).
CACHE = ROOT / "work" / "pubchem_cache.json"
_cache: dict[str, dict | None] = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def pubchem(name: str) -> dict | None:
    if name in _cache:
        return _cache[name]
    for attempt in range(6):
        r = requests.get(API.format(requests.utils.quote(name)), timeout=30)
        if r.status_code == 404:
            _cache[name] = None
            break
        if r.status_code in (429, 503):
            time.sleep(3 + attempt * 5)
            continue
        r.raise_for_status()
        time.sleep(0.25)
        _cache[name] = r.json()["PropertyTable"]["Properties"][0]
        break
    else:
        raise RuntimeError(f"PubChem busy for {name}")
    CACHE.write_text(json.dumps(_cache))
    return _cache[name]


def formula(mol: Chem.Mol) -> str:
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula
    return CalcMolFormula(mol)


def main(unit: str) -> None:
    draft = yaml.safe_load((ROOT / "figures" / unit / "compounds_draft.yaml").read_text())
    registry_path = ROOT / "figures" / "compounds.yaml"
    registry = yaml.safe_load(registry_path.read_text()) or {}
    report = [f"# Structure verification — {unit}", ""]
    counts: dict[str, int] = {}

    for c in draft:
        scope = c.get("scope")
        key = f"{unit}-{scope}-{c['number']}" if scope else f"{unit}-{c['number']}"
        # Wedges are described, not written as @/@@: RDKit derives the configuration (see drawing_stereo.py).
        sd = c.get("stereo_drawing")
        mol = mol_from_drawing(sd["mapped_smiles"], sd["centres"]) if sd else Chem.MolFromSmiles(c["smiles"] or "")
        pc = None
        if c.get("generic"):
            status, detail, mol = "generic", "Markush drawing", None
        elif mol is None:
            status, detail, pc = "invalid", f"drawn SMILES doesn't parse: {c['smiles']!r}", None
        elif not c.get("pubchem_query"):
            status = "read-twice" if c.get("double_read") == "agree" else "unverified"
            detail = "no name in the book" + ("" if status == "read-twice" else f" (double read: {c.get('double_read')})")
        else:
            pc = pubchem(c["pubchem_query"])
            if pc is None:
                # Named, but PubChem doesn't know the name: as good as unnamed.
                status = "read-twice" if c.get("double_read") == "agree" else "not-found"
                detail = f"PubChem doesn't know {c['pubchem_query']!r}"
            else:
                drawn_key = Chem.MolToInchiKey(mol)
                pc_key = pc["InChIKey"]
                # PubChem often stores the salt (e.g. "….Cl"): compare the parent compound.
                pc_smiles = pc.get("IsomericSMILES") or pc["SMILES"]
                if "." in pc_smiles and "." not in Chem.MolToSmiles(mol):
                    parent = rdMolStandardize.LargestFragmentChooser().choose(Chem.MolFromSmiles(pc_smiles))
                    pc_key = Chem.MolToInchiKey(parent)
                # A PubChem entry without stereo (…-UHFFFAOYSA-…) can only confirm connectivity.
                full = bool(c.get("stereo_drawn")) and "-UHFFFAOYSA-" not in pc_key
                # The key's last character is the protonation state: a carboxylate drawn as COO⁻ is the
                # same compound as PubChem's neutral acid, so it is left out of the comparison.
                same = drawn_key[:25] == pc_key[:25] if full else drawn_key[:14] == pc_key[:14]
                if not same:
                    # Tautomers (e.g. a hydroxy-quinone imine drawn for dopachrome) are the same compound.
                    te = rdMolStandardize.TautomerEnumerator()
                    parent = Chem.MolFromSmiles(pc_smiles.split(".")[0] if "." not in Chem.MolToSmiles(mol) else pc_smiles)
                    n = 25 if full else 14
                    same = (Chem.MolToInchiKey(te.Canonicalize(mol))[:n]
                            == Chem.MolToInchiKey(te.Canonicalize(parent))[:n])
                status = "verified" if same else "mismatch"
                detail = (f"{'full' if full else 'connectivity'} · drawn {formula(mol)} {drawn_key} "
                          f"· PubChem CID {pc['CID']} {pc['MolecularFormula']} {pc_key}")
        counts[status] = counts.get(status, 0) + 1

        entry = {
            "number": str(c["number"]), "figure": c.get("figure"), "names_de": c.get("names_de") or [],
            "pubchem_query": c.get("pubchem_query"), "status": status,
            "render_smiles": Chem.MolToSmiles(mol) if mol else None,
            "stereo_drawn": bool(c.get("stereo_drawn")),
            "compared_on": "full stereo" if c.get("stereo_drawn") else "connectivity",
            "double_read": c.get("double_read"),
        }
        if pc:
            entry.update(cid=pc["CID"], smiles=pc.get("IsomericSMILES") or pc["SMILES"], inchikey=pc["InChIKey"])
        # Keep a human resolution made earlier (e.g. a redraw after a confirmed book error).
        if registry.get(key, {}).get("resolution"):
            entry["resolution"] = registry[key]["resolution"]
            entry["render_smiles"] = registry[key]["render_smiles"]
            entry["status"] = registry[key]["status"]
        # Figures where the book prints this number under a different structure keep their printed original.
        if registry.get(key, {}).get("keep_original_in"):
            entry["keep_original_in"] = registry[key]["keep_original_in"]
        registry[key] = entry
        if status != "verified":
            report.append(f"- **{c['number']}** ({', '.join(entry['names_de']) or 'no name'}) — {status}: {detail}")

    registry_path.write_text(yaml.safe_dump(registry, allow_unicode=True, sort_keys=False))
    report.insert(2, "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "\n")
    (ROOT / "figures" / unit / "verify_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(sys.argv[1])
