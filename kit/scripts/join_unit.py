"""Join all pages of a reading unit (source/units.yaml) into work/<dir>/de.md.

Usage: scriptorium run join_unit <slug>        e.g. 3, ex-fluor

Units split around an excursus are joined range by range; each range starts a
new block, so text never runs across the excursus.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from bookroot import ROOT  # the book project (book.yaml), not the kit
units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
unit = next(u for u in units if u["slug"] == sys.argv[1])
ranges = unit.get("ranges") or [[unit["first"], unit["last"]]]
out_dir = ROOT / "work" / unit["dir"]

parts, notes = [], []
with tempfile.TemporaryDirectory() as tmp:
    for i, (a, b) in enumerate(ranges):
        part = Path(tmp) / f"part{i}"
        r = subprocess.run([sys.executable, str(Path(__file__).with_name("join_pages.py")), str(a), str(b), str(part)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
        parts.append((part / "de.md").read_text().strip())
        notes.append((part / "join_notes.txt").read_text().strip())

# Footnote definitions collect at the end of each part — move them all to the end.
body, footnotes = [], []
for text in parts:
    blocks = text.split("\n\n")
    body += [b for b in blocks if not b.startswith("[^")]
    footnotes += [b for b in blocks if b.startswith("[^")]
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "de.md").write_text("\n\n".join(body + footnotes) + "\n")
(out_dir / "join_notes.txt").write_text("\n".join(n for n in notes if n) + "\n")
print(f"wrote {out_dir / 'de.md'} ({len(' '.join(body).split())} words) from {len(ranges)} range(s)")
print("\n".join(n for n in notes if n) or "no notes")
