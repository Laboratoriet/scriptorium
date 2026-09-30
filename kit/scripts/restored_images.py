"""Compress the cleaned/upscaled images (figures/images, mapped in figures/images/map.yaml) for the site.

Usage: scriptorium run restored_images

Writes figures/restored/<figure>.webp: longest side 1400 px (the site shows figures at most ~576 px wide, so this
is sharp at 2× and a little more), WebP quality 80 (85 for line illustrations with small text). Marks the figure
`status: done` in figures/upscale_queue.yaml. build_content.py picks the files up.
"""
from pathlib import Path

import yaml
from PIL import Image

from bookroot import ROOT  # the book project (book.yaml), not the kit
SRC = ROOT / "figures" / "images"
OUT = ROOT / "figures" / "restored"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    mapping = yaml.safe_load((SRC / "map.yaml").read_text())
    queue_path = ROOT / "figures" / "upscale_queue.yaml"
    queue = yaml.safe_load(queue_path.read_text())
    by_id = {q["id"]: q for q in queue}
    before = after = 0
    for row in mapping:
        if not row.get("figure") or row.get("hold"):
            (OUT / f"{row.get('figure')}.webp").unlink(missing_ok=True)
            continue
        src = SRC / row["file"]
        im = Image.open(src).convert("RGB")
        im.thumbnail((1400, 1400), Image.LANCZOS)
        target = OUT / f"{row['figure']}.webp"
        im.save(target, "WEBP", quality=85 if row["file"].startswith(("Illustrations/", "cleanup/")) else 80, method=6)
        before += src.stat().st_size
        after += target.stat().st_size
        if row["figure"] in by_id:
            by_id[row["figure"]].update(status="done", restored=f"figures/images/{row['file']}")
    queue_path.write_text(yaml.safe_dump(queue, sort_keys=False, allow_unicode=True))
    todo = [q["id"] for q in queue if q.get("status") != "done"]
    print(f"{len(list(OUT.glob('*.webp')))} restored images, {before / 1e6:.1f} MB → {after / 1e6:.1f} MB")
    print(f"upscale queue: {len(queue) - len(todo)} done, {len(todo)} still to do")


if __name__ == "__main__":
    main()
