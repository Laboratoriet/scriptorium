"""Check the agents' manual reference links and apply the ones that hold up → work/<unit>/references_manual.yaml.

Usage: scriptorium run apply_manual_links

Input: work/references_manual/<group>.todo.yaml (the unmatched entries as printed) and <group>.done.yaml
(proposals: status doi | url | uncertain | none, with evidence; brief: scriptorium brief REFERENCES).
- doi: re-fetched from Crossref and accepted only if the year matches and at least one of first page, volume or
  first-author surname matches the printed entry — the agents' word alone is not enough.
- url: accepted if it answers (HTTP < 400; 401/403/429 count as "exists, bot-blocked" and are accepted with a note).
- uncertain / none: not linked; listed in the report for the proofreader.
Accepted links go to work/<unit>/references_manual.yaml, which link_references.py and this script overlay onto
work/<unit>/references.yaml (so a rerun of the automatic pass keeps them). Report: work/references_manual/REPORT.md.
"""
import json
import re
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from link_references import CACHE, HEADERS, fold, parse

from bookroot import ROOT  # the book project (book.yaml), not the kit
MANUAL = ROOT / "work" / "references_manual"


def crossref_doi(doi: str, cache: dict) -> dict | None:
    key = f"doi:{doi.lower()}"
    if key not in cache:
        r = requests.get(f"https://api.crossref.org/works/{requests.utils.quote(doi)}", headers=HEADERS, timeout=30)
        cache[key] = r.json()["message"] if r.status_code == 200 else None
    return cache[key]


def doi_holds(ref: dict, item: dict) -> tuple[bool, str]:
    parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
    year = str(parts[0]) if parts and parts[0] else None
    first_page = re.split(r"[-–]", item.get("page") or "")[0]
    volume = (item.get("volume") or "").strip()
    surnames = [fold(a.get("family", "")) for a in item.get("author", [])]
    hits = []
    if ref["page"] and first_page == ref["page"]:
        hits.append("page")
    if ref["volume"] and volume == ref["volume"]:
        hits.append("volume")
    if ref["author"] and any(s and (s in fold(ref["author"]) or fold(ref["author"]).endswith(s)) for s in surnames):
        hits.append("author")
    ok = bool(year and ref["year"] == year and hits)
    return ok, f"year {year} vs {ref['year']}; matched: {', '.join(hits) or 'nothing'}"


def url_holds(url: str) -> tuple[bool, str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    except requests.RequestException as e:
        return False, f"unreachable ({type(e).__name__})"
    if r.status_code < 400:
        return True, f"HTTP {r.status_code}"
    if r.status_code in (401, 403, 429):
        return True, f"HTTP {r.status_code} (bot-blocked, exists)"
    return False, f"HTTP {r.status_code}"


def overlay(unit: str) -> None:
    """Write the accepted manual links onto work/<unit>/references.yaml rows that are still unmatched."""
    auto, manual = ROOT / "work" / unit / "references.yaml", ROOT / "work" / unit / "references_manual.yaml"
    if not (auto.exists() and manual.exists()):
        return
    links = {(m["list"], m["n"]): m for m in yaml.safe_load(manual.read_text()) or []}
    rows = yaml.safe_load(auto.read_text()) or []
    for row in rows:
        m = links.get((row["list"], row["n"]))
        if m and row["status"] == "unmatched":
            row.update({k: v for k, v in m.items() if k in ("status", "doi", "url", "title")}, source="manual")
    auto.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False))


def main() -> None:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    accepted: dict[str, list[dict]] = {}
    report = {"doi": [], "url": [], "rejected": [], "uncertain": [], "none": [], "missing": []}
    for todo_path in sorted(MANUAL.glob("*.todo.yaml")):
        done_path = todo_path.with_name(todo_path.name.replace(".todo.", ".done."))
        todo = yaml.safe_load(todo_path.read_text()) or []
        done = {(d["unit"], d["list"], d["n"]): d for d in (yaml.safe_load(done_path.read_text()) or [])} if done_path.exists() else {}
        for t in todo:
            d = done.get((t["unit"], t["list"], t["n"]))
            label = f"{t['unit']} [{t['list']}.{t['n']}] {re.sub(r'[*]', '', t['entry'])[:110]}"
            if not d:
                report["missing"].append(label)
                continue
            status, ev = d.get("status"), d.get("evidence", "")
            if status == "doi" and d.get("doi"):
                item = crossref_doi(d["doi"].strip(), cache)
                ok, why = doi_holds(parse(t["entry"]), item) if item else (False, "DOI not in Crossref")
                if ok:
                    accepted.setdefault(t["unit"], []).append({"list": t["list"], "n": t["n"], "status": "doi", "doi": d["doi"].strip(),
                                                               "url": f"https://doi.org/{d['doi'].strip()}", "title": ((item.get('title') or [''])[0])[:120]})
                    report["doi"].append(f"{label} → {d['doi']} ({why})")
                else:
                    report["rejected"].append(f"{label} → {d['doi']}: {why} · agent: {ev}")
            elif status == "url" and d.get("url"):
                ok, why = url_holds(d["url"].strip())
                if ok:
                    accepted.setdefault(t["unit"], []).append({"list": t["list"], "n": t["n"], "status": "url", "url": d["url"].strip()})
                    report["url"].append(f"{label} → {d['url']} ({why})")
                else:
                    report["rejected"].append(f"{label} → {d['url']}: {why} · agent: {ev}")
            elif status == "uncertain":
                report["uncertain"].append(f"{label} → {d.get('doi') or d.get('url') or '—'}: {ev}")
            else:
                report["none"].append(f"{label}: {ev}")
    CACHE.write_text(json.dumps(cache))
    for unit, rows in accepted.items():
        (ROOT / "work" / unit / "references_manual.yaml").write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False))
        overlay(unit)
    titles = {"doi": "Accepted DOIs (re-checked against Crossref)", "url": "Accepted URLs", "rejected": "Rejected proposals",
              "uncertain": "Uncertain — for the proofreader", "none": "No online record", "missing": "Not answered"}
    lines = ["# Manual reference links — report", "", "Generated by `scriptorium run apply_manual_links`.", "",
             " · ".join(f"{titles[k].split(' (')[0]}: {len(v)}" for k, v in report.items()), ""]
    for k, v in report.items():
        if v:
            lines += [f"## {titles[k]} ({len(v)})", ""] + [f"- {x}" for x in v] + [""]
    (MANUAL / "REPORT.md").write_text("\n".join(lines))
    print(" · ".join(f"{k} {len(v)}" for k, v in report.items()))


if __name__ == "__main__":
    main()
