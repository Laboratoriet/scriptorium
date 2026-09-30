"""Find names for structure cards the book shows with a number only.

Usage: scriptorium run name_compounds

For every compound in figures/compounds.yaml without a printed name:
1. PubChem by structure (InChIKey of the drawn structure) → CID, title and synonyms. Cached in work/pubchem_structure_cache.json.
2. The book's own wording: the phrase right before each linked mention "… name (**n**)" in the built text
   (site/content/units/*.json, where numbers carry their scoped key). A phrase counts as the book's name only if
   PubChem lists it as a synonym of the same structure.
Writes `name_book` (confirmed book wording), `pubchem_title` and `cid` (structure match) into compounds.yaml.
"""
import json
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
CACHE = ROOT / "work" / "pubchem_structure_cache.json"
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def get(url: str):
    for attempt in range(6):
        r = requests.get(url, timeout=30)
        if r.status_code == 404:
            return None
        if r.status_code in (429, 503):
            time.sleep(2 + attempt * 4)
            continue
        r.raise_for_status()
        time.sleep(0.22)
        return r.json()
    raise RuntimeError("PubChem busy")


def by_structure(inchikey: str) -> dict | None:
    if inchikey not in cache:
        hit = get(f"{API}/compound/inchikey/{inchikey}/property/Title/JSON")
        entry = None
        if hit:
            p = hit["PropertyTable"]["Properties"][0]
            syn = get(f"{API}/compound/cid/{p['CID']}/synonyms/JSON")
            names = syn["InformationList"]["Information"][0].get("Synonym", [])[:80] if syn else []
            entry = {"cid": p["CID"], "title": p.get("Title"), "synonyms": names}
        cache[inchikey] = entry
        CACHE.write_text(json.dumps(cache))
    return cache[inchikey]


def mentions() -> dict[str, list[str]]:
    """key → phrases printed right before a linked mention of the compound."""
    out: dict[str, list[str]] = {}
    for f in (ROOT / "site" / "content" / "units").glob("*.json"):
        for b in json.loads(f.read_text())["blocks"]:
            for field in ("en", "caption_en"):
                html = b.get(field) or ""
                for m in re.finditer(r'([^()<>]{2,80})\(<a class="cpd" href="[^"]*" data-cpd="([^"]+)">[^<]*</a>', html):
                    text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                    out.setdefault(m.group(2), []).append(text)
    return out


JUNK = re.compile(r"^(\d{2,7}-\d{2}-\d|[A-Z]{2,}[-_ ]?\d|SCHEMBL|DTXSID|DTXCID|AKOS|CHEMBL|ZINC|MFCD|NSC|UNII|BRN|"
                  r"EINECS|CCRIS|HSDB|Q\d+|[A-Z0-9]{8,}$)|:", re.I)


# Name roots the book's readers know (book.yaml: chemistry.familiar_names) are preferred over systematic names.
_familiar = (CONFIG.get("chemistry") or {}).get("familiar_names") or []
FAMILIAR = re.compile("|".join(map(re.escape, _familiar)), re.I) if _familiar else None


def readable(hit: dict) -> str | None:
    """The most readable name PubChem has for the structure: familiar roots and few brackets beat full IUPAC;
    registry numbers, database IDs, salts and very long names are skipped."""
    cands = []
    for s in [hit.get("title") or ""] + hit.get("synonyms", []):
        if not s or JUNK.search(s) or ";" in s or len(s) > 48 or (s.isupper() and len(s) > 6):
            continue
        if re.search(r"\(\+-\)|\(±\)|hydrochloride|sulfate|maleate|\bsalt\b", s, re.I):
            continue
        cands.append(s)
    if not cands:
        return None
    return sorted(set(cands), key=lambda s: (s.count("(") + 2 * s.count("["), 0 if FAMILIAR and FAMILIAR.search(s) else 1,
                                             len(s)))[0]


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> None:
    compounds = yaml.safe_load((ROOT / "figures" / "compounds.yaml").read_text())
    said = mentions()
    todo = [k for k, c in compounds.items()
            if c.get("status") in ("read-twice", "verified", "corrected") and not c.get("names_de") and c.get("render_smiles")]
    found = book = 0
    for i, key in enumerate(todo):
        c = compounds[key]
        mol = Chem.MolFromSmiles(c["render_smiles"])
        if mol is None:
            continue
        hit = by_structure(Chem.MolToInchiKey(mol))
        if not hit:
            continue
        found += 1
        c["cid"] = c.get("cid") or hit["cid"]
        c["pubchem_title"] = hit["title"]
        c["pubchem_name"] = readable(hit)
        syn = {norm(s): s for s in hit["synonyms"] + [hit["title"] or ""]}
        # the longest trailing word run of a mention that PubChem knows as a name of this structure
        best = None
        for phrase in said.get(key, []):
            words = phrase.split()
            for n in range(min(6, len(words)), 0, -1):
                cand = " ".join(words[-n:]).strip(" ,;:.")
                if not cand[:1].isalnum():  # "-acetylaniline": a lost italic N- prefix, not a whole name
                    continue
                if norm(cand) in syn and len(norm(cand)) > 2:
                    best = best or cand
                    break
        if best:
            c["name_book"] = best
            book += 1
        if i % 50 == 0:
            print(f"{i}/{len(todo)} …", file=sys.stderr)
    (ROOT / "figures" / "compounds.yaml").write_text(yaml.safe_dump(compounds, allow_unicode=True, sort_keys=False, width=200))
    print(f"unnamed: {len(todo)} · found in PubChem by structure: {found} · named in the book's text (confirmed): {book}")


if __name__ == "__main__":
    main()
