"""Compare two blind readings of generic structure figures (work/generic/A|B/<figure>.yaml).

Usage: scriptorium run compare_generic [--apply]

Per figure, nodes are paired in reading order and compared on a signature that ignores drawing choices:
the molecule with every placeholder carrying its printed label (the `via` bond of a floating substituent removed),
the labels, ring locants, floating-bond positions, highlights and drawn H — each tied to canonical atom classes.
Agreeing figures are listed; with --apply they are copied to work/schemes/<figure>.yaml (reader A's layout).
Disagreements go to work/generic/disagreements.md.
"""
import shutil
import sys
from pathlib import Path

import yaml
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
from bookroot import ROOT  # the book project (book.yaml), not the kit
DIR = ROOT / "work" / "generic"


def signature(node: dict):
    if not node.get("smiles"):
        return ("text", (node.get("text_en") or "").strip().lower())
    mol = Chem.MolFromSmiles(node["smiles"])
    if mol is None:
        return ("unparsable", node["smiles"])
    rw = Chem.RWMol(mol)
    by_map = {a.GetAtomMapNum(): a.GetIdx() for a in rw.GetAtoms() if a.GetAtomMapNum()}
    labels = {int(k): v for k, v in (node.get("rgroups") or {}).items()}
    norm = lambda s: str(s).replace("′", "'").replace("″", "''").replace("<sub>", "").replace("</sub>", "").replace(" ", "")
    for m, text in labels.items():  # placeholder atoms become distinguishable by their label
        rw.GetAtomWithIdx(by_map[m]).SetIsotope(1 + sum(ord(ch) for ch in norm(text)) % 997)
    att = node.get("attach")
    atts = att if isinstance(att, list) else [att] if att else []
    for a_ in atts:  # one floating bond, or several
        b = rw.GetBondBetweenAtoms(by_map[int(a_["from"])], by_map[int(a_["via"])])
        if b:
            rw.RemoveBond(b.GetBeginAtomIdx(), b.GetEndAtomIdx())
    for a in rw.GetAtoms():
        a.SetAtomMapNum(0)
        if a.GetAtomicNum():  # "[c:14]" would otherwise count as an H-less radical
            a.SetNoImplicit(False)
            a.SetNumRadicalElectrons(0)
    m2 = rw.GetMol()
    try:
        Chem.SanitizeMol(m2)
    except Exception:  # noqa: BLE001
        return ("unsanitizable", node["smiles"])
    ranks = list(Chem.CanonicalRankAtoms(m2, breakTies=False))
    cls = lambda mapnum: ranks[by_map[int(mapnum)]]
    return (
        Chem.MolToSmiles(m2),
        tuple(sorted((cls(m), str(t)) for m, t in (node.get("locants") or {}).items())),
        tuple(sorted((cls(a_["from"]), tuple(sorted(cls(x) for x in a_["to"]))) for a_ in atts)) or None,
        tuple(sorted(tuple(sorted(cls(x) for x in (h if isinstance(h, list) else [h]))) for h in node.get("highlight") or [])),
        (),  # drawn H (show_h) is presentation, not chemistry — not compared
        str(node.get("number") or ""),
    )


def nodes_in_order(spec: dict) -> list[dict]:
    seen, out = set(), []
    for row in spec.get("grid") or []:
        for c in row:
            key = c if isinstance(c, str) else (c.get("node") if isinstance(c, dict) else None)
            if key and key not in seen and key in spec["nodes"]:
                seen.add(key)
                out.append(spec["nodes"][key])
    return out


def main(apply: bool) -> None:
    agree, differ, missing, skipped = [], [], [], []
    for a_path in sorted((DIR / "A").glob("*.yaml")):
        b_path = DIR / "B" / a_path.name
        if not b_path.exists():
            missing.append(a_path.stem)
            continue
        a, b = yaml.safe_load(a_path.read_text()), yaml.safe_load(b_path.read_text())
        if a.get("skip") and b.get("skip"):
            skipped.append(a_path.stem)
            continue
        if a.get("skip") or b.get("skip"):
            # convention: a figure with any member that can't be drawn is skipped whole — one skip is enough
            skipped.append(a_path.stem)
            continue
        na, nb = nodes_in_order(a), nodes_in_order(b)
        issues = []
        if len(na) != len(nb):
            issues.append(f"node count {len(na)} vs {len(nb)}")
        for i, (x, y) in enumerate(zip(na, nb)):
            sx, sy = signature(x), signature(y)
            if sx != sy:
                what = ["structure", "locants", "floating bond", "highlight", "drawn H", "number"]
                parts = [w for w, p, q in zip(what, sx, sy) if p != q] if len(sx) == len(sy) == 6 else ["structure"]
                issues.append(f"node {i + 1} ({x.get('number') or ''}): {', '.join(parts)} — A {x.get('smiles')} / B {y.get('smiles')}")
        (differ if issues else agree).append((a_path.stem, issues))
    report = ["# Generic figures — reader disagreements", ""]
    for fid, issues in differ:
        report += [f"## {fid}"] + [f"- {i}" for i in issues] + [""]
    (DIR / "disagreements.md").write_text("\n".join(report))
    (DIR / "skipped.txt").write_text("\n".join(skipped) + "\n")
    print(f"agree {len(agree)} · both skipped {len(skipped)} · differ {len(differ)} · waiting for B {len(missing)}")
    if apply:
        for fid, _ in agree:
            spec = yaml.safe_load((DIR / "A" / f"{fid}.yaml").read_text())
            spec["kind"] = "generic"
            for node in spec.get("nodes", {}).values():  # ring N–H stays "NH" (the drawn-H option is for chain N)
                if node.get("show_h") and node.get("smiles"):
                    mol = Chem.MolFromSmiles(node["smiles"])
                    ring = {a.GetAtomMapNum() for a in mol.GetAtoms() if a.IsInRing() and a.GetAtomMapNum()}
                    node["show_h"] = [m for m in node["show_h"] if int(m) not in ring] or None
                    if not node["show_h"]:
                        node.pop("show_h")
            spec["read"] = "two blind readings agree"
            (ROOT / "work" / "schemes" / f"{fid}.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, width=140))
        print(f"applied {len(agree)} → work/schemes/")


if __name__ == "__main__":
    main("--apply" in sys.argv)
