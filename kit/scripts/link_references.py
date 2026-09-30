"""Find DOIs for the book's literature references → work/<dir>/references.yaml.

Usage: scriptorium run link_references [unit-dir …]     (default: every unit with a de.md)

Each entry "[n] Authors. *Journal* **Year**, *Vol*, Page." is looked up in Crossref and a DOI is
accepted only if the candidate agrees on year AND first page AND (volume, or the first author's
surname when the entry has no volume) — no guessed links. URLs printed in an entry become links as
they are. Everything else is left "unmatched" for a second, manual/agent pass (books, patents, old
journals). Crossref answers are cached in work/references_cache.json, so reruns are cheap.
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
import yaml

from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
CACHE = ROOT / "work" / "references_cache.json"
API = "https://api.crossref.org/works"
HEADERS = {"User-Agent": "book-kit-reference-linker/1.0 (private study edition)"}
REF = re.compile(r"^\[(\d+)\]\s*(.*)$")
LIST_START = re.compile(rf"^#+\s+({re.escape(CONFIG.get('references_heading', 'Literatur'))}|References)\b")


def plain(text: str) -> str:
    return re.sub(r"<[^>]+>|[*_]", "", text).strip()


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def parse(entry: str) -> dict:
    year = re.search(r"\*\*(\d{4})\*\*", entry) or re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", entry)
    vol = re.search(r"\*\*\d{4}\*\*,\s*\*([^*]+)\*", entry)
    page = re.search(r"\*\*\d{4}\*\*,\s*(?:\*[^*]+\*,\s*)?(?:\([^)]*\),?\s*)?([A-Za-z]?\d+)", entry)
    first_author = re.match(r"\s*(?:[A-ZÄÖÜ]\.\s*)+([^,.;]+)", plain(entry))
    return {"year": year.group(1) if year else None, "volume": vol.group(1).strip() if vol else None,
            "page": page.group(1) if page else None,
            "author": first_author.group(1).strip() if first_author else None}


def crossref(query: str, cache: dict) -> list[dict]:
    if query in cache:
        return cache[query]
    for attempt in range(4):
        try:
            r = requests.get(API, params={"query.bibliographic": query, "rows": 5,
                                          "select": "DOI,issued,volume,page,author,title,container-title"},
                             headers=HEADERS, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(3 + attempt * 5)
                continue
            r.raise_for_status()
            items = r.json()["message"]["items"]
            cache[query] = items
            time.sleep(0.15)
            return items
        except requests.RequestException:
            time.sleep(3 + attempt * 5)
    return []


def accept(ref: dict, item: dict) -> bool:
    year = str((item.get("issued", {}).get("date-parts") or [[None]])[0][0])
    first_page = re.split(r"[-–]", item.get("page") or "")[0]
    if not (ref["year"] and ref["page"] and year == ref["year"] and first_page == ref["page"]):
        return False
    if ref["volume"]:
        return (item.get("volume") or "").strip() == ref["volume"]
    surnames = [fold(a.get("family", "")) for a in item.get("author", [])]
    return bool(ref["author"]) and any(fold(ref["author"]).endswith(s) or s in fold(ref["author"]) for s in surnames if s)


def link_unit(unit: str, cache: dict) -> dict:
    text = (ROOT / "work" / unit / "de.md").read_text()
    out, list_no, counts = [], 0, {"doi": 0, "url": 0, "unmatched": 0}
    for line in text.splitlines():
        if LIST_START.match(line):
            list_no += 1
            continue
        m = REF.match(line)
        if not m or list_no == 0:
            continue
        n, entry = int(m.group(1)), m.group(2)
        row = {"list": list_no, "n": n}
        url = re.search(r"https?://[^\s,;)\]]+", entry)
        ref = parse(entry)
        if url:
            row.update(status="url", url=url.group(0).rstrip("."))
        elif ref["year"] and ref["page"]:
            hit = next((i for i in crossref(plain(entry), cache) if accept(ref, i)), None)
            if hit:
                row.update(status="doi", doi=hit["DOI"], url=f"https://doi.org/{hit['DOI']}",
                           title=(hit.get("title") or [""])[0][:120])
        row.setdefault("status", "unmatched")
        counts["doi" if row["status"] == "doi" else "url" if row["status"] == "url" else "unmatched"] += 1
        out.append(row)
    (ROOT / "work" / unit / "references.yaml").write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False))
    CACHE.write_text(json.dumps(cache))
    # Links found by hand and re-checked (scriptorium run apply_manual_links) survive a rerun of this automatic pass.
    from apply_manual_links import overlay
    overlay(unit)
    print(f"{unit}: {len(out)} refs · {counts['doi']} DOI · {counts['url']} URL · {counts['unmatched']} unmatched", flush=True)
    return counts


def main() -> None:
    units = sys.argv[1:] or sorted(p.parent.name for p in (ROOT / "work").glob("*/de.md"))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    total = {"doi": 0, "url": 0, "unmatched": 0}
    for unit in units:
        for k, v in link_unit(unit, cache).items():
            total[k] += v
    print("total:", total)


if __name__ == "__main__":
    main()
