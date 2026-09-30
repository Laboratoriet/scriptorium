"""Split a large unit into translation parts, and merge the translated parts back.

Usage:
  scriptorium run split_parts split work/ch03 "3.1" "3.2" "3.5" "3.11" "3.12.4" "3.13"
      → work/ch03/parts/p1.de.md … (a new part starts at each listed section heading)
  scriptorium run split_parts merge work/ch03
      → work/ch03/en.md from parts/p*.en.md (and checks the German round-trips)

Parts break only at "## <number>." heading blocks. Footnote definitions ([^id]: …)
travel with the part that references them, and are put back at the end on merge.
"""
import re
import sys
from pathlib import Path


def blocks_of(text: str) -> list[str]:
    return text.rstrip("\n").split("\n\n")


def def_id(block: str) -> str:
    return re.match(r"^\[\^([\w-]+)\]", block).group(1)


def is_def(block: str) -> bool:
    return bool(re.match(r"^\[\^[\w-]+\]:", block))


def split(unit: Path, starts: list[str]) -> None:
    blocks = blocks_of((unit / "de.md").read_text())
    body = [b for b in blocks if not is_def(b)]
    defs = [b for b in blocks if is_def(b)]
    parts: list[list[str]] = [[]]
    for b in body:
        m = re.match(r"^## ([\d.]+?)\.? ", b)
        if m and m.group(1) in starts and parts[-1]:
            parts.append([])
        parts[-1].append(b)
    if len(parts) != len(starts) + 1:
        sys.exit(f"expected {len(starts) + 1} parts, got {len(parts)} — check the section numbers")
    out = unit / "parts"
    out.mkdir(exist_ok=True)
    for i, part in enumerate(parts, 1):
        text = "\n\n".join(part)
        own_defs = [d for d in defs if "[^" + def_id(d) + "]" in text]
        (out / f"p{i}.de.md").write_text("\n\n".join(part + own_defs) + "\n")
        print(f"p{i}: {len(text.split()):6} words, {len(own_defs)} footnotes — starts {part[0][:60]!r}")


def merge(unit: Path) -> None:
    files = sorted((unit / "parts").glob("p*.de.md"), key=lambda p: int(p.name[1:].split(".")[0]))
    de_body, de_defs, en_body, en_defs = [], [], [], []
    for de_file in files:
        en_file = de_file.with_name(de_file.name.replace(".de.", ".en."))
        if not en_file.exists():
            sys.exit(f"missing {en_file}")
        for b in blocks_of(de_file.read_text()):
            (de_defs if is_def(b) else de_body).append(b)
        for b in blocks_of(en_file.read_text()):
            (en_defs if is_def(b) else en_body).append(b)
    # The German parts must reassemble to the original exactly (same blocks, same order).
    original = blocks_of((unit / "de.md").read_text())
    if [b for b in original if not is_def(b)] != de_body or sorted(b for b in original if is_def(b)) != sorted(de_defs):
        sys.exit("German parts don't reassemble to de.md — refusing to merge")
    order = {def_id(b): i for i, b in enumerate(original) if is_def(b)}
    en_defs.sort(key=lambda b: order.get(def_id(b), 10**6))
    (unit / "en.md").write_text("\n\n".join(en_body + en_defs) + "\n")
    print(f"wrote {unit / 'en.md'} from {len(files)} parts ({len(' '.join(en_body).split())} words)")


if __name__ == "__main__":
    cmd, unit = sys.argv[1], Path(sys.argv[2])
    split(unit, sys.argv[3:]) if cmd == "split" else merge(unit)
