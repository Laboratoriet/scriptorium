"""Export a chapter as clean, portable English Markdown.

Usage: scriptorium run export_markdown <unit slug or dir>   e.g. 2 → exports/ch02.en.md (+ exports/structures/)

- Page anchors become small page markers: ⟨p. 50⟩
- Translator's notes become Markdown footnotes [^tn1]
- Structure placeholders become image rows with compound numbers and names
- Chart/advert placeholders become an image of the printed original plus the caption
"""
import re
import shutil
import sys
from pathlib import Path

import yaml

from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
EXPORTS = ROOT / "exports"


def unit_dir(arg: str) -> str:
    """A unit's slug ("3", "ex-fluor") or dir ("ch03") → its work/ folder name."""
    units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text()) or []
    for u in units:
        if arg in (str(u["slug"]), u["dir"]) or arg.lstrip("0") == str(u["slug"]):
            return u["dir"]
    sys.exit(f"no unit {arg!r} in source/units.yaml")


def main(num: str) -> None:
    chapter = unit_dir(num)
    text = (ROOT / "work" / chapter / "en.md").read_text()
    compounds = yaml.safe_load((ROOT / "figures" / "compounds.yaml").read_text())
    (EXPORTS / "structures").mkdir(parents=True, exist_ok=True)
    (EXPORTS / "figures").mkdir(parents=True, exist_ok=True)

    notes = []

    def tn(m: re.Match) -> str:
        notes.append(re.sub(r"\s+", " ", m.group(1)).strip())
        return f"[^tn{len(notes)}]"

    text = re.sub(r"\s*<!-- TN:\s*(.*?)\s*-->", tn, text, flags=re.S)
    text = re.sub(r"\n?<!-- p\.(\d+) -->\n?", lambda m: f" ⟨p. {m.group(1)}⟩ ", text)

    def figure(m: re.Match) -> str:
        fields = dict(
            (k.strip(), v.strip().strip('"'))
            for k, _, v in (part.partition(":") for part in m.group(1).split("|")[1:])
        )
        fid = m.group(1).split("|")[0].strip()
        label = fields.get("label", "").replace("Abb.", "Fig.")
        caption = fields.get("caption", "")
        if fields.get("kind") == "structure":
            cells = []
            for c in re.findall(r"[\w]+", fields.get("compounds", "").strip("[]")):
                key = f"{chapter}-{c}"
                shutil.copy(ROOT / "figures" / "structures" / f"{key}.svg", EXPORTS / "structures" / f"{key}.svg")
                cells.append(f"![Structure {c}](structures/{key}.svg) **{c}**")
                cells[-1] += f" — PubChem {compounds[key]['cid']}"
            return "\n\n".join(cells) + f"\n\n*{caption}*"
        original = ROOT / "figures" / chapter / f"{fid}_orig.png"
        if original.exists():
            shutil.copy(original, EXPORTS / "figures" / original.name)
            return f"![{label or 'Figure'}](figures/{original.name})\n\n**{label}** {caption}".strip()
        return f"**{label}** {caption}".strip()

    text = re.sub(r"\{\{fig:(.*?)\}\}", figure, text, flags=re.S)
    text = re.sub(r"  +", " ", text).strip()
    if notes:
        text += "\n\n---\n\n" + "\n".join(f"[^tn{i}]: Translator's note: {n}" for i, n in enumerate(notes, 1))

    header = (
        f"<!-- Working English translation of {', '.join(CONFIG.get('authors', []))}, "
        f"{CONFIG.get('title', '')} ({CONFIG.get('year', '')}). Private use. -->\n\n"
    )
    out = EXPORTS / f"{chapter}.en.md"
    out.write_text(header + text + "\n")
    print(f"wrote {out} ({len(text.split())} words, {len(notes)} translator's notes)")


if __name__ == "__main__":
    main(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
