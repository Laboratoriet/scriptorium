"""Check each literature list in a joined chapter against the citations before it.

Usage: scriptorium run check_references work/chNN/de.md
"""
import re
import sys

from bookroot import CONFIG

HEADING = re.escape(CONFIG.get("references_heading", "Literatur"))  # the source's word for the list
text = open(sys.argv[1]).read()
text = re.sub(r"(compounds|labels): \[[^\]]*\]", "", text)  # compound/label lists aren't citations; captions are
parts = re.split(rf"^## (?:{HEADING}|References)\s*$", text, flags=re.M)
ok = True
for i, (body, lit) in enumerate(zip(parts[:-1], parts[1:]), 1):
    lit = re.split(r"^#", lit, flags=re.M)[0]
    entries = [int(x) for x in re.findall(r"^\[(\d+)\]", lit, re.M)]
    cited = set()
    body = re.sub(r"^\[\d+\].*$", "", body, flags=re.M)  # the previous list's entries aren't citations
    for group in re.findall(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]", body):
        for part in re.split(r",\s*", group):
            a = re.split(r"\s*[-–]\s*", part)
            cited.update(range(int(a[0]), int(a[-1]) + 1))
    missing = sorted(cited - set(entries))
    unused = sorted(set(entries) - cited)
    sequential = entries == list(range(1, len(entries) + 1))
    ok &= sequential and not missing
    print(f"list {i}: {len(entries)} entries, sequential={sequential}, cited-not-listed={missing}, listed-not-cited={unused}")
sys.exit(0 if ok else 1)
