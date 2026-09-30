"""How far each unit of the book has come → printed table (used for STATUS.md).

Usage: scriptorium run coverage

Per unit: scanned pages, pages transcribed (de.md), joined German, English, independent review,
built into the site, structures redrawn. Derived from the files, so it can't go stale.
"""
import json
from pathlib import Path

import yaml

from bookroot import ROOT  # the book project (book.yaml), not the kit


def main() -> None:
    units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
    manifest = json.loads((ROOT / "source" / "page_manifest.json").read_text())
    reg_path = ROOT / "figures" / "compounds.yaml"  # chemistry books only
    registry = (yaml.safe_load(reg_path.read_text()) or {}) if reg_path.exists() else {}
    built = {p.stem for p in (ROOT / "site" / "content" / "units").glob("*.json")}
    rows, totals = [], {"pages": 0, "de": 0}
    for u in units:
        if u["slug"] == "front":
            pages, de = 19, (ROOT / "work" / "front" / "de.md").exists() and 19 or 0
        else:
            ranges = u.get("ranges") or [[u["first"], u["last"]]]
            nums = [p for a, b in ranges for p in range(a, b + 1) if manifest.get(str(p)) == "scanned"]
            pages = len(nums)
            de = sum((ROOT / "source" / "pages" / f"{p:04d}" / "de.md").exists() for p in nums)
        work = ROOT / "work" / u["dir"]
        structures = sum(1 for k, c in registry.items() if k.startswith(u["dir"] + "-") and c.get("status") in ("verified", "corrected", "read-twice"))
        rows.append({
            "unit": u.get("title_en") or u["slug"], "slug": u["slug"], "pages": pages, "de": de,
            "joined": (work / "de.md").exists(), "en": (work / "en.md").exists(),
            "reviewed": (work / "review.md").exists() or any(work.glob("parts/*review*")),
            "site": u["slug"] in built, "structures": structures,
        })
        totals["pages"] += pages
        totals["de"] += de
    tick = lambda b: "✓" if b else "—"
    print("| Unit | Pages | Transcribed | English | Reviewed | On site | Structures redrawn |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['unit']} | {r['pages']} | {r['de']}/{r['pages']} | {tick(r['en'])} | {tick(r['reviewed'])} | {tick(r['site'])} | {r['structures'] or '—'} |")
    en_pages = sum(r["pages"] for r in rows if r["en"])
    print(f"\nTotal: {totals['pages']} scanned pages · transcribed {totals['de']} · translated {en_pages}")


if __name__ == "__main__":
    main()
