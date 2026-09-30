"""Split a unit's structure figures into reading batches → work/<unit-dir>/structures/batchN.json.

Usage: scriptorium run structure_batches <unit-dir> [--size 45] [--scan]

Walks work/<unit-dir>/de.md in reading order and collects every structure figure with its compounds.
The compound scope (section number) is tracked the way build_content.py does it, so it only matters
for units with `compound_scopes: per-section` in source/units.yaml. Batches hold about --size
compounds and never split a figure.

--scan only reports: figures, compounds, and numbers that occur in figures of more than one section
(the sign that a chapter restarts its numbering and needs `compound_scopes: per-section`).
"""
import json
import re
import sys
from pathlib import Path

import yaml

from bookroot import ROOT  # the book project (book.yaml), not the kit
FIG = re.compile(r"\{\{fig:(p\d{4}-\d+)\s*\|(.*?)\}\}")
HEADING = re.compile(r"^(#+)\s+(.*)$")


def field(body: str, name: str) -> str | None:
    m = re.search(rf"\b{name}:\s*(\"(?:[^\"\\]|\\.)*\"|\[[^\]]*\]|[^|]+)", body)
    return m.group(1).strip() if m else None


def figures(unit_dir: str) -> list[dict]:
    out, scope = [], None
    for line in (ROOT / "work" / unit_dir / "de.md").read_text().splitlines():
        h = HEADING.match(line)
        if h:
            number = re.match(r"^([\d.]+)\s", h.group(2) + " ")
            num_id = number.group(1).rstrip(".") if number else None
            if num_id and (len(h.group(1)) == 1 or re.fullmatch(r"\d+\.\d+", num_id)):
                scope = num_id
        for m in FIG.finditer(line):
            body = m.group(2)
            if (field(body, "kind") or "").strip() != "structure":
                continue
            compounds = [c.strip().strip("\"'") for c in (field(body, "compounds") or "[]").strip("[]").split(",") if c.strip()]
            if not compounds:
                continue
            caption = (field(body, "caption") or "").strip('"')
            out.append({"figure": m.group(1), "kind": "structure", "scope": scope, "compounds": compounds,
                        "caption_de": caption, "crop": f"figures/{unit_dir}/{m.group(1)}_orig.png"})
    return out


def main() -> None:
    unit_dir = sys.argv[1]
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 45
    units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
    unit = next(u for u in units if u["dir"] == unit_dir)
    per_section = unit.get("compound_scopes") == "per-section"
    figs = figures(unit_dir)
    missing = [f["figure"] for f in figs if not (ROOT / f["crop"]).exists()]
    seen: dict[str, set] = {}
    for f in figs:
        for c in f["compounds"]:
            seen.setdefault(c, set()).add(f["scope"])
    restarts = sorted((c for c, s in seen.items() if len(s) > 1), key=lambda c: (len(c), c))
    total = sum(len(f["compounds"]) for f in figs)
    print(f"{unit_dir}: {len(figs)} figures · {total} compound slots · per-section: {per_section} · "
          f"missing crops: {', '.join(missing) or 'none'}")
    if restarts:
        print(f"  numbers in more than one section ({len(restarts)}): {', '.join(restarts[:30])}"
              + (" …" if len(restarts) > 30 else ""))
    if "--scan" in sys.argv:
        return
    if not per_section:
        for f in figs:
            f["scope"] = None
    batches, current = [], []
    for f in figs:
        if current and sum(len(x["compounds"]) for x in current) + len(f["compounds"]) > size:
            batches.append(current)
            current = []
        current.append(f)
    if current:
        batches.append(current)
    sdir = ROOT / "work" / unit_dir / "structures"
    sdir.mkdir(parents=True, exist_ok=True)
    for i, b in enumerate(batches, 1):
        (sdir / f"batch{i}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1))
    print(f"  → {len(batches)} batches: " + ", ".join(str(sum(len(f['compounds']) for f in b)) for b in batches))


if __name__ == "__main__":
    main()
