"""Validate a scheme spec (work/schemes/<figure>.yaml) and render a rough preview PNG of its grid.

Usage: scriptorium run scheme_preview work/schemes/p0951-1.yaml

The preview is for checking connectivity and layout against the printed crop, not the final look (the site renders
the same spec with its own structure SVGs). Format: scriptorium brief SCHEMES.
"""
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw
from rdkit import Chem, RDLogger
from rdkit.Chem import Draw

sys.path.insert(0, str(Path(__file__).parent))
from drawing_stereo import mol_from_drawing

RDLogger.DisableLog("rdApp.*")
CELL_W, CELL_H = 300, 260
# ASCII, so the preview font can draw them.
ARROWS = {"right": "-->", "left": "<--", "down": "v", "up": "^", "down-right": "\\>", "down-left": "</",
          "up-right": "/>", "up-left": "<\\", "both": "<=>"}


def node_mol(node: dict):
    sd = node.get("stereo_drawing")
    if sd:
        return Chem.RemoveHs(mol_from_drawing(sd["mapped_smiles"], sd["centres"]))
    return Chem.MolFromSmiles(node["smiles"])


def main(path: Path) -> None:
    spec = yaml.safe_load(path.read_text())
    problems = []
    nodes = spec.get("nodes") or {}
    mols = {}
    for key, n in nodes.items():
        if n.get("smiles"):
            try:
                m = node_mol(n)
            except Exception as e:  # noqa: BLE001 — report any parse problem
                m, err = None, str(e)
            else:
                err = ""
            if m is None:
                problems.append(f"{key}: SMILES/stereo does not parse {err}")
            mols[key] = m
        elif not n.get("text_en") and not n.get("callout_en"):
            problems.append(f"{key}: neither smiles, text_en nor callout_en")
    used = set()
    grid = spec.get("grid") or []
    width = max((sum(c.get("span", 1) if isinstance(c, dict) else 1 for c in row) for row in grid), default=1)
    for r, row in enumerate(grid):
        for c in row:
            ref = c if isinstance(c, str) else c.get("node") if isinstance(c, dict) else None
            if ref:
                if ref not in nodes:
                    problems.append(f"row {r + 1}: unknown node {ref}")
                used.add(ref)
            elif isinstance(c, dict) and c.get("arrow") not in ARROWS:
                problems.append(f"row {r + 1}: arrow direction {c.get('arrow')!r}")
            if isinstance(c, dict) and c.get("style") not in (None, "line", "open", "blocked"):
                problems.append(f"row {r + 1}: arrow style {c.get('style')!r}")
    for key, n in nodes.items():
        for fld in ("data_en", "data_de"):
            if isinstance(n.get(fld), str):
                problems.append(f"{key}: {fld} is a string — write a list (one item per printed line)")
    for key in nodes:
        if key not in used:
            problems.append(f"{key}: not placed in the grid")

    img = Image.new("RGB", (width * CELL_W, max(1, len(grid)) * CELL_H), "white")
    draw = ImageDraw.Draw(img)
    for r, row in enumerate(grid):
        x = 0
        for c in row:
            span = c.get("span", 1) if isinstance(c, dict) else 1
            box = (x * CELL_W, r * CELL_H)
            if isinstance(c, dict) and c.get("node"):
                c = c["node"]
            if isinstance(c, str) and c in nodes:
                n = nodes[c]
                if mols.get(c) is not None:
                    img.paste(Draw.MolToImage(mols[c], size=(CELL_W - 20, CELL_H - 60)), (box[0] + 10, box[1] + 5))
                else:
                    txt = n.get("text_en") or " / ".join(str(x) for x in (n.get("callout_en") or [])) or "?"
                    draw.multiline_text((box[0] + 10, box[1] + 60), txt[:120], fill="black")
                label = " ".join(str(v) for v in (n.get("number"), n.get("name_en")) if v)
                draw.text((box[0] + 10, box[1] + CELL_H - 45), label[:45], fill="black")
            elif isinstance(c, dict):
                cx = box[0] + span * CELL_W // 2
                draw.text((box[0] + 10, box[1] + CELL_H // 2 - 40), (c.get("label_en") or "")[:45], fill="black")
                glyph = ARROWS.get(c.get("arrow"), "?") + (" (open)" if c.get("style") == "open" else "")
                glyph += f" x{c['rows']} rows" if c.get("rows") else ""
                draw.text((cx - 20, box[1] + CELL_H // 2 - 10), glyph, fill="black")
                draw.text((box[0] + 10, box[1] + CELL_H // 2 + 20), (c.get("label_below_en") or "")[:45], fill="black")
            x += span
    out = path.parent / "preview" / f"{path.stem}.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(f"{len(nodes)} nodes, {len(grid)} rows → {out}")
    print("\n".join(problems) if problems else "no problems")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
