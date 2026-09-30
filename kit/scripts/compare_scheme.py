"""Compare two blind readings of schemes (work/scheme_rollout/A|B/<figure>.yaml).

Usage: scriptorium run compare_scheme [--apply]

Layout is a drawing choice, so it isn't compared. What is compared, as multisets (order-free):
- molecules: structure signature (as in compare_generic: canonical, R labels, locants, floating bonds, highlights),
  printed number, and every data line (Ki, doses, durations) — character for character after whitespace/markup
  normalisation, because the numbers are the point of these schemes;
- text elements: their English text, normalised;
- arrows: direction, style and labels, normalised.
Agreeing figures go to work/schemes/<figure>.yaml with --apply (reader A's layout, `read:` set, so the site shows
them as checked instead of pilot). Disagreements → work/scheme_rollout/disagreements.md; skips → skipped.txt.
"""
import html
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from compare_generic import signature
from rdkit import Chem
from scheme_preview import node_mol

from bookroot import ROOT  # the book project (book.yaml), not the kit
DIR = ROOT / "work" / "scheme_rollout"


def norm(text) -> str:
    """Wording-level comparison: markup, spacing, quotes, dashes and case don't count."""
    t = html.unescape(str(text or ""))
    t = re.sub(r"<[^>]+>", "", t).replace("*", "")
    t = t.replace("′", "'").replace("″", "''").replace("’", "'").replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", "", t).lower()


def molecules(spec: dict) -> Counter:
    out = Counter()
    for n in (spec.get("nodes") or {}).values():
        if n.get("smiles"):
            # stereo drawn with wedges: compare the resulting configuration, not the readers' atom numbering
            stereo = ""
            if n.get("stereo_drawing"):
                try:
                    stereo = Chem.MolToSmiles(node_mol(n))
                except Exception:  # noqa: BLE001
                    stereo = "unreadable stereo"
            data = tuple(sorted(norm(d) for d in n.get("data_en") or []))
            # class maps: the section a class links to, and its arrow (direction + label), are content too
            arrow = n.get("arrow") or ("out" if n.get("chapter") and n.get("role") != "core" else "none")
            cm = (str(n.get("chapter") or ""), n.get("role") or "", arrow if spec.get("kind") == "classmap" else "", norm(n.get("arrow_label_en")),
                  norm(" ".join(str(x) for x in (n.get("callout_en") or []))))
            out[(repr(signature(n)), stereo, norm(n.get("number")), data, cm)] += 1
    return out


def texts(spec: dict) -> Counter:
    # text elements and free callout blocks (compared as running text: line breaks and bullets don't count)
    return Counter(norm(str(n.get("text_en") or "") + " ".join(str(x) for x in (n.get("callout_en") or [])))
                   for n in (spec.get("nodes") or {}).values() if not n.get("smiles"))


def arrows(spec: dict) -> Counter:
    out = Counter()
    if spec.get("kind") == "classmap":  # class maps draw their own arrows (per node, compared in molecules/texts)
        return out
    for row in spec.get("grid") or []:
        for c in row:
            if isinstance(c, dict) and c.get("arrow"):
                # which side of the arrow a label sits on is layout; its text is compared
                out[(c["arrow"], c.get("style") or "line", c.get("heads"), tuple(sorted(norm(c.get(k)) for k in ("label_en", "label_below_en"))))] += 1
    return out


def diff(name: str, a: Counter, b: Counter) -> list[str]:
    if a == b:
        return []
    only_a, only_b = a - b, b - a
    show = lambda c: "; ".join(str(k)[:160] for k in c.elements())
    return [f"{name}: only A — {show(only_a) or '∅'} | only B — {show(only_b) or '∅'}"]


def main(apply: bool) -> None:
    agree, differ, missing, skipped = [], [], [], []
    for a_path in sorted((DIR / "A").glob("*.yaml")):
        b_path = DIR / "B" / a_path.name
        if not b_path.exists():
            missing.append(a_path.stem)
            continue
        a, b = yaml.safe_load(a_path.read_text()), yaml.safe_load(b_path.read_text())
        if (a.get("continues") or None) != (b.get("continues") or None):
            differ.append((a_path.stem, [f"continues: A {a.get('continues')} / B {b.get('continues')}"]))
            continue
        if a.get("skip") or b.get("skip"):
            skipped.append(f"{a_path.stem}\tA: {a.get('skip') or '-'}\tB: {b.get('skip') or '-'}")
            continue
        issues = diff("molecules", molecules(a), molecules(b)) + diff("text", texts(a), texts(b)) + diff("arrows", arrows(a), arrows(b))
        (differ if issues else agree).append((a_path.stem, issues))
    report = ["# Schemes — reader disagreements", ""]
    for fid, issues in differ:
        report += [f"## {fid}"] + [f"- {i}" for i in issues] + [""]
    (DIR / "disagreements.md").write_text("\n".join(report))
    (DIR / "skipped.txt").write_text("\n".join(skipped) + ("\n" if skipped else ""))
    print(f"agree {len(agree)} · skipped {len(skipped)} · differ {len(differ)} · waiting for B {len(missing)}")
    if apply:
        for fid, _ in agree:
            target = ROOT / "work" / "schemes" / f"{fid}.yaml"
            if target.exists() and (yaml.safe_load(target.read_text()) or {}).get("locked"):
                continue  # edited by hand after the readings agreed (e.g. a format feature added later): keep it
            spec = yaml.safe_load((DIR / "A" / f"{fid}.yaml").read_text())
            spec["read"] = "two blind readings agree"
            (ROOT / "work" / "schemes" / f"{fid}.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False, width=140))
        print(f"applied {len(agree)} → work/schemes/")


if __name__ == "__main__":
    main("--apply" in sys.argv)
