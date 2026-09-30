"""Check and merge the structure readings of a unit (two blind readers, A and B).

Usage:
  scriptorium run structure_readings check <reading.yaml>   # validate + preview sheets
  scriptorium run structure_readings merge <unit-dir>        # A vs B → compounds_draft.yaml

Readings live in work/<unit-dir>/structures/read_<A|B>_batch<N>.yaml (format: scriptorium brief STRUCTURES).
`check` renders every reading of a figure to preview/<reader>/<figure>.png so the reader can
compare it with the crop. `merge` compares A and B per compound on the InChIKey (full key when
wedges are drawn) and writes figures/<unit-dir>/compounds_draft.yaml for verify_compounds.py,
plus work/<unit-dir>/structures/disagreements.md for the cases a human has to settle.
"""
import json
import sys
from pathlib import Path

import yaml
from rdkit import Chem, RDLogger
from rdkit.Chem import Draw, rdDepictor

sys.path.insert(0, str(Path(__file__).parent))
from drawing_stereo import mol_from_drawing

RDLogger.DisableLog("rdApp.*")
from bookroot import ROOT  # the book project (book.yaml), not the kit


def num(n) -> str:
    """Compound number as printed: "2a", never '"2a"' (placeholders sometimes quote them)."""
    return str(n).strip().strip('"').strip("'")


def load_tasks(sdir: Path) -> list[dict]:
    tasks = [t for b in sorted(sdir.glob("batch*.json")) for t in json.loads(b.read_text())]
    for t in tasks:
        t["compounds"] = [num(c) for c in t["compounds"]]
    return tasks


def mol_of(entry: dict) -> Chem.Mol | None:
    """The structure as drawn: from the wedge description if there is one, else the flat SMILES."""
    sd = entry.get("stereo_drawing")
    if sd:
        return mol_from_drawing(sd["mapped_smiles"], sd["centres"])
    return Chem.MolFromSmiles(entry.get("smiles") or "") if entry.get("smiles") else None


def key_of(entry: dict) -> str | None:
    mol = mol_of(entry)
    return Chem.MolToInchiKey(mol) if mol else None


def check(path: Path) -> None:
    unit_dir = path.parent.parent
    reader = path.stem.split("_")[1]
    tasks = {t["figure"]: t for t in load_tasks(path.parent)}
    readings = yaml.safe_load(path.read_text()) or []
    preview = path.parent / "preview" / reader
    preview.mkdir(parents=True, exist_ok=True)
    problems, by_fig = [], {}
    for e in readings:
        fig = e.get("figure")
        label = f"{fig} #{e.get('number')}"
        if fig not in tasks:
            problems.append(f"{label}: unknown figure")
            continue
        if num(e.get("number")) not in tasks[fig]["compounds"] and not e.get("extra"):
            problems.append(f"{label}: number not in the figure's compound list (set extra: true if it is really printed)")
        if e.get("generic"):
            continue
        try:
            mol = mol_of(e)
        except Exception as ex:  # noqa: BLE001 — report any drawing-description error
            problems.append(f"{label}: stereo_drawing fails: {ex}")
            continue
        if mol is None:
            problems.append(f"{label}: SMILES doesn't parse: {e.get('smiles')!r}")
            continue
        if e.get("stereo_drawing") and e.get("smiles"):
            flat = Chem.MolFromSmiles(e["smiles"])
            if flat is None or Chem.MolToInchiKey(flat)[:14] != Chem.MolToInchiKey(mol)[:14]:
                problems.append(f"{label}: smiles and stereo_drawing.mapped_smiles are different compounds")
        by_fig.setdefault(fig, []).append((num(e["number"]), mol))
    for fig, t in tasks.items():
        got = {num(e.get("number")) for e in readings if e.get("figure") == fig}
        if fig in {e.get("figure") for e in readings}:
            for n in t["compounds"]:
                if n not in got:
                    problems.append(f"{fig} #{n}: no reading")
    for fig, mols in by_fig.items():
        drawn = []
        for _, m in mols:  # fresh layout; chiral tags survive, wedges are redrawn from them
            m = Chem.Mol(m)
            rdDepictor.Compute2DCoords(m)
            drawn.append(m)
        img = Draw.MolsToGridImage(drawn, legends=[n for n, _ in mols], molsPerRow=4,
                                   subImgSize=(420, 320))
        img.save(preview / f"{fig}.png")
    print(f"{len(readings)} readings, {len(by_fig)} preview sheets in {preview.relative_to(ROOT)}")
    print("\n".join(problems) if problems else "no problems")


def merge(unit: str) -> None:
    sdir = ROOT / "work" / unit / "structures"
    tasks = load_tasks(sdir)
    reads = {r: {} for r in "AB"}
    for r in "AB":
        for f in sorted(sdir.glob(f"read_{r}_batch*.yaml")):
            for e in yaml.safe_load(f.read_text()) or []:
                reads[r][(e["figure"], num(e["number"]))] = e
    renumber_path = sdir / "renumber.yaml"
    renumber = yaml.safe_load(renumber_path.read_text()) if renumber_path.exists() else {}
    # PubChem names that resolve to the wrong entry: {number: better query}, each with a comment why.
    queries_path = sdir / "queries.yaml"
    queries = {num(k): v for k, v in (yaml.safe_load(queries_path.read_text()) or {}).items()} if queries_path.exists() else {}
    draft, report, counts = [], [f"# Reader disagreements — {unit}", ""], {}
    for t in tasks:
        for n in t["compounds"]:
            a, b = reads["A"].get((t["figure"], n)), reads["B"].get((t["figure"], n))
            if not a or not b:
                verdict, detail = "missing", f"A {'ok' if a else '—'} / B {'ok' if b else '—'}"
            elif a.get("generic") or b.get("generic"):
                verdict = "agree" if a.get("generic") and b.get("generic") else "disagree"
                detail = "generic" if verdict == "agree" else "one reader says generic"
            else:
                ka, kb = key_of(a), key_of(b)
                stereo = bool(a.get("stereo_drawing") or b.get("stereo_drawing"))
                same = ka == kb if stereo else (ka or "")[:14] == (kb or "")[:14]
                verdict = "agree" if ka and same else "disagree"
                detail = f"A {a.get('smiles')} / B {b.get('smiles')}"
            counts[verdict] = counts.get(verdict, 0) + 1
            base = a or b or {}
            entry = {
                "number": (renumber.get(t["figure"]) or {}).get(n, n), "figure": t["figure"], "scope": t["scope"],
                "names_de": base.get("names_de") or [],
                "pubchem_query": queries.get(n) or (a or {}).get("pubchem_query") or (b or {}).get("pubchem_query"),
                "smiles": base.get("smiles"), "stereo_drawing": base.get("stereo_drawing"),
                "stereo_drawn": bool(base.get("stereo_drawing")), "generic": bool(base.get("generic")),
                "double_read": verdict,
            }
            draft.append(entry)
            if verdict != "agree":
                report.append(f"- **{t['scope']} / {n}** ({t['figure']}) — {verdict}: {detail}"
                              + (f"\n  - A: {a.get('notes')}" if a and a.get("notes") else "")
                              + (f"\n  - B: {b.get('notes')}" if b and b.get("notes") else ""))
    out = ROOT / "figures" / unit / "compounds_draft.yaml"
    out.write_text(yaml.safe_dump(draft, allow_unicode=True, sort_keys=False))
    report.insert(2, "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "\n")
    (sdir / "disagreements.md").write_text("\n".join(report) + "\n")
    print(report[2])
    print(f"→ {out.relative_to(ROOT)}, {(sdir / 'disagreements.md').relative_to(ROOT)}")


if __name__ == "__main__":
    {"check": lambda a: check(Path(a).resolve()), "merge": merge}[sys.argv[1]](sys.argv[2])
