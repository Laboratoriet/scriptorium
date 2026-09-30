# Finding links for unmatched literature references (verify-only)

Phase 6b — run after `scriptorium run link_references <unit>`; the lead splits the unmatched entries into work/references_manual/<group>.todo.yaml.

The book's reference entries were matched to DOIs automatically (Crossref, strict: year + first page + volume/author).
The entries in your `<group>.todo.yaml` did not match. Your job: find the **real** online record for as many as you can
— and **never guess**. A wrong link is worse than no link.

Each todo item: `unit`, `list`, `n`, `entry` (the reference exactly as printed, Markdown: `*Journal*`, `**Year**`, `*Volume*`, page).

## What to look for
- **Journal articles:** the DOI. Search Crossref (`https://api.crossref.org/works?query.bibliographic=…&rows=5`), PubMed, or the
  web. Accept only when the record agrees with the entry on **year** and at least two of: first page, volume, first author's
  surname, journal. The book often abbreviates journals, and old volumes/pages can be off by one — if something disagrees,
  say so in `evidence` and use `status: uncertain` instead of `doi`.
- **No DOI exists** (old journals, Chem. Abstr., books, patents, theses, web pages): a stable URL to the record itself —
  patents → `https://patents.google.com/patent/<number>`; PubMed → `https://pubmed.ncbi.nlm.nih.gov/<pmid>/`;
  books → the publisher page, Google Books or WorldCat record for that edition; archived pages → web.archive.org.
- **Personal communications, unpublished work, "in preparation", conference talks without a record:** `status: none`.
- Don't link to shadow libraries or unofficial PDF copies.

## Output — `work/references_manual/<group>.done.yaml`
One row per todo item, same order, written as you go (every ~15 items), so nothing is lost:

```yaml
- {unit: ch03, list: 1, n: 1, status: doi, doi: "10.xxxx/…", evidence: "Crossref: Logan BK, Forensic Sci Rev 2002 14(2):133–151 — year/vol/author match; book gives p.134 (first page 133)"}
- {unit: ch03, list: 1, n: 4, status: url, url: "https://…", evidence: "…"}
- {unit: ch03, list: 1, n: 7, status: uncertain, doi: "10.…", evidence: "year and author match, volume differs (book 12, record 13)"}
- {unit: ch03, list: 1, n: 9, status: none, evidence: "personal communication"}
```

`status` is one of `doi | url | uncertain | none`. Every `doi`/`url`/`uncertain` row needs `evidence` naming what matched.
A script re-checks every `doi` row against Crossref (year + page/volume/author) before anything is published, so be exact.

Work only in your own `.done.yaml`. Final reply: counts per status and anything notable (e.g. entries in the book that are wrong).
