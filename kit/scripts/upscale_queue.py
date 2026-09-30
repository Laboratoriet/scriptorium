"""List the illustrations (photos, adverts) to send for upscaling → figures/upscale_queue.yaml.

Usage: scriptorium run upscale_queue

Collects every figure of kind `photo` or `advert` from the transcribed pages (de.md placeholders)
and from the figure-box pass (source/pages/NNNN/figures.yaml), with its crop if one exists.
Existing `status` fields (e.g. `upscaled`, `skip`) are kept when the list is rebuilt.
"""
import re
from pathlib import Path

import yaml
from PIL import Image

from bookroot import ROOT  # the book project (book.yaml), not the kit
KINDS = {"photo", "advert"}
FIG = re.compile(r"\{\{fig:(p\d+-\d+)\s*\|([^}]*)\}\}")


def unit_of(page: int, units: list[dict]) -> dict | None:
    for u in units:
        for a, b in u.get("ranges") or [[u["first"], u["last"]]]:
            if a <= page <= b:
                return u
    return None


def main() -> None:
    units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
    out_path = ROOT / "figures" / "upscale_queue.yaml"
    previous = {e["id"]: e for e in (yaml.safe_load(out_path.read_text()) or [])} if out_path.exists() else {}
    queue = {}
    for page_dir in sorted((ROOT / "source" / "pages").iterdir()):
        if not page_dir.name.isdigit():
            continue
        page = int(page_dir.name)
        found = {}
        de = page_dir / "de.md"
        if de.exists():
            for fid, rest in FIG.findall(de.read_text()):
                kind = re.search(r"kind:\s*([\w-]+)", rest)
                caption = re.search(r'caption:\s*"([^"]*)"', rest)
                found[fid] = (kind.group(1) if kind else None, caption.group(1) if caption else "")
        boxes = page_dir / "figures.yaml"
        if boxes.exists():
            for f in yaml.safe_load(boxes.read_text()) or []:
                found.setdefault(f["id"], (f.get("kind"), f.get("note", "")))
        for fid, (kind, caption) in found.items():
            if kind not in KINDS:
                continue
            unit = unit_of(page, units)
            crop = ROOT / "figures" / (unit["dir"] if unit else "misc") / f"{fid}_orig.png"
            entry = {"id": fid, "page": page, "unit": unit["slug"] if unit else None, "kind": kind,
                     "caption_de": caption, "crop": str(crop.relative_to(ROOT)) if crop.exists() else None}
            if crop.exists():
                with Image.open(crop) as im:
                    entry["crop_px"] = list(im.size)
            entry["status"] = previous.get(fid, {}).get("status", "todo")
            queue[fid] = entry
    out_path.write_text(yaml.safe_dump(list(queue.values()), allow_unicode=True, sort_keys=False))
    todo = sum(e["status"] == "todo" for e in queue.values())
    print(f"{len(queue)} illustrations ({todo} todo) → {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
