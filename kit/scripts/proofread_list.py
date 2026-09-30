"""Collect every translator's note (<!-- TN: … -->) in a chapter into a
checklist for the proofreading chemist, with the page each note sits on.

Usage: scriptorium run proofread_list work/ch02
"""
import re
import sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
chapter = Path(sys.argv[1])
text = (chapter / "en.md").read_text()
items = []
for match in re.finditer(r"<!-- TN:\s*(.*?)\s*-->", text, re.S):
    pages = re.findall(r"<!-- p\.(\d+) -->", text[: match.start()])
    page = pages[-1] if pages else "?"
    context = re.sub(r"\s+", " ", text[max(0, match.start() - 160): match.start()]).strip()
    context = re.sub(r"<!--.*?-->|\{\{fig:[^}]*\}\}", "", context)[-120:]
    items.append((page, re.sub(r"\s+", " ", match.group(1)), context))

lines = [f"# Proofreading checklist — {chapter.name}", "",
         f"{len(items)} translator's notes. Tick each once checked against the printed book (p. = printed page).", ""]
for i, (page, note, context) in enumerate(items, 1):
    lines += [f"- [ ] **TN{i} — p. {page}**", f"  - Context: “…{context}”", f"  - Note: {note}", ""]
(chapter / "PROOFREAD.md").write_text("\n".join(lines))
print(f"{len(items)} notes → {chapter / 'PROOFREAD.md'}")
