"""Crop every figure of a unit from its page renders → figures/<dir>/<fig-id>_orig.png.

Usage: scriptorium run crop_figures <slug> [--redo p0073-1,p0101-1 --pad 6]
  --redo  re-crop these figures even if a crop exists (e.g. the bbox cut off part of a structure)
  --pad   padding in % of the page for this run (default 1.5)

Uses the bbox_pct recorded in each page's de.md front matter; renders the page at
300 dpi for the crop (sharper than the 150 dpi pdf.png). Existing crops are kept.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image

from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
args = sys.argv[1:]
REDO = set(args[args.index("--redo") + 1].split(",")) if "--redo" in args else set()
PAD = float(args[args.index("--pad") + 1]) if "--pad" in args else 1.5  # % of page, so edge strokes aren't clipped

units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
unit = next(u for u in units if u["slug"] == args[0])
book_to_pdf = {int(k): v for k, v in json.loads((ROOT / "source" / "book_to_pdf.json").read_text()).items()}
out_dir = ROOT / "figures" / unit["dir"]
out_dir.mkdir(parents=True, exist_ok=True)

made = 0
for a, b in unit.get("ranges") or [[unit["first"], unit["last"]]]:
    for page in range(a, b + 1):
        de = ROOT / "source" / "pages" / f"{page:04d}" / "de.md"
        boxes = re.findall(r"\{id: (p\d+-\d+), bbox_pct: \[([^\]]+)\]\}", de.read_text()) if de.exists() else []
        # Boxes from the figure-box pass (untranscribed pages, and tables everywhere); de.md wins on a shared id.
        extra = ROOT / "source" / "pages" / f"{page:04d}" / "figures.yaml"
        if extra.exists():
            known = {fid for fid, _ in boxes}
            boxes += [(f["id"], ",".join(str(v) for v in f["bbox_pct"]))
                      for f in yaml.safe_load(extra.read_text()) or [] if f["id"] not in known]
        todo = [(fid, bb) for fid, bb in boxes if fid in REDO or not (out_dir / f"{fid}_orig.png").exists()]
        if not todo:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["pdftoppm", "-f", str(book_to_pdf[page]), "-l", str(book_to_pdf[page]), "-r", "300",
                            "-png", str(ROOT / "source" / CONFIG["source_pdf"]), f"{tmp}/p"], check=True)
            im = Image.open(next(Path(tmp).glob("p-*.png")))
            w, h = im.size
            for fid, bb in todo:
                x0, y0, x1, y1 = (float(v) for v in bb.split(","))
                box = (max(0, int(w * (x0 - PAD) / 100)), max(0, int(h * (y0 - PAD) / 100)),
                       min(w, int(w * (x1 + PAD) / 100)), min(h, int(h * (y1 + PAD) / 100)))
                im.crop(box).save(out_dir / f"{fid}_orig.png")
                made += 1
print(f"{unit['slug']}: {made} figure crops → {out_dir}")
