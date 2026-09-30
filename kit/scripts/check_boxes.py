"""Validate figure/table boxes of pages and render them for a visual check.

Usage: scriptorium run check_boxes 0460 0461 …   (or a range: 0460-0470)

Reads source/pages/NNNN/figures.yaml (format: `scriptorium brief BOXES`) and writes
work/boxes/preview/NNNN.png — the page with every box outlined and labelled — plus one
crop per box (work/boxes/preview/<id>.png) exactly as crop_figures.py will cut it.
"""
import re
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

from bookroot import ROOT  # the book project (book.yaml), not the kit
PAD = 1.5  # same padding as crop_figures.py
KINDS = {"structure", "scheme", "photo", "chart", "diagram", "advert", "table"}


def pages(args: list[str]) -> list[str]:
    out = []
    for a in args:
        if "-" in a:
            lo, hi = (int(x) for x in a.split("-"))
            out += [f"{p:04d}" for p in range(lo, hi + 1)]
        else:
            out.append(f"{int(a):04d}")
    return out


def check(page: str, preview: Path) -> list[str]:
    path = ROOT / "source" / "pages" / page / "figures.yaml"
    if not path.exists():
        return []
    problems = []
    boxes = yaml.safe_load(path.read_text()) or []
    im = Image.open(ROOT / "source" / "pages" / page / "pdf.png").convert("RGB")
    w, h = im.size
    sheet = im.copy()
    draw = ImageDraw.Draw(sheet)
    fig_n = tab_n = 0
    for b in boxes:
        fid, kind, bb = b.get("id", "?"), b.get("kind"), b.get("bbox_pct") or []
        if kind not in KINDS:
            problems.append(f"{fid}: unknown kind {kind!r}")
        if kind == "table":
            tab_n += 1
            expected = f"p{page}-t{tab_n}"
        else:
            fig_n += 1
            expected = f"p{page}-{fig_n}"
        if fid != expected:
            problems.append(f"{fid}: expected id {expected} (reading order, figures and tables counted separately)")
        if len(bb) != 4 or not all(isinstance(v, (int, float)) for v in bb):
            problems.append(f"{fid}: bbox_pct must be 4 numbers")
            continue
        x0, y0, x1, y1 = bb
        if not (0 <= x0 < x1 <= 100 and 0 <= y0 < y1 <= 100):
            problems.append(f"{fid}: bbox_pct {bb} must be percent (0–100), x0<x1, y0<y1")
            continue
        if x1 - x0 < 5 or y1 - y0 < 3:
            problems.append(f"{fid}: box is tiny ({bb}) — percent, not fractions?")
        px = (int(w * x0 / 100), int(h * y0 / 100), int(w * x1 / 100), int(h * y1 / 100))
        draw.rectangle(px, outline=(220, 30, 30), width=4)
        draw.text((px[0] + 6, px[1] + 4), fid, fill=(220, 30, 30))
        crop = (max(0, int(w * (x0 - PAD) / 100)), max(0, int(h * (y0 - PAD) / 100)),
                min(w, int(w * (x1 + PAD) / 100)), min(h, int(h * (y1 + PAD) / 100)))
        im.crop(crop).save(preview / f"{fid}.png")
    sheet.thumbnail((1400, 1400))
    sheet.save(preview / f"{page}.png")
    return problems


def main() -> None:
    preview = ROOT / "work" / "boxes" / "preview"
    preview.mkdir(parents=True, exist_ok=True)
    total = 0
    for page in pages(sys.argv[1:]):
        for p in check(page, preview):
            print(f"{page}: {p}")
            total += 1
    print("no problems" if total == 0 else f"{total} problems")


if __name__ == "__main__":
    main()
