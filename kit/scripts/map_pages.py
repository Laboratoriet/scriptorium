"""Build source/book_to_pdf.json and source/page_manifest.json: printed page → PDF page.

Usage: scriptorium run map_pages <first_book_page> <last_book_page> <pdf_page_of_first> [--missing 6,10,16] [--blank 42,58]

--missing  printed pages that are not in the PDF at all (a scan that skipped blank pages);
           the PDF counter does not advance for them.
--blank    printed pages that are in the PDF but empty (section-break pages); mapped, but
           join_pages skips them.
Roman-numbered front matter is not mapped here — list it in units.yaml (`pages: [I, II, …]`).
Check a few pages against pdf.png after render_pages: an off-by-one here shifts every page.
"""
import argparse
import json

from bookroot import ROOT


def ints(s: str) -> set[int]:
    return {int(x) for x in s.split(",") if x.strip()} if s else set()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("pdf_first", type=int)
    ap.add_argument("--missing", default="")
    ap.add_argument("--blank", default="")
    a = ap.parse_args()
    missing, blank = ints(a.missing), ints(a.blank)

    mapping, manifest, pdf = {}, {}, a.pdf_first
    for n in range(a.first, a.last + 1):
        if n in missing:
            manifest[str(n)] = "missing-likely-blank"
            continue
        mapping[f"{n:04d}"] = pdf
        manifest[str(n)] = "missing-likely-blank" if n in blank else "scanned"
        pdf += 1

    src = ROOT / "source"
    src.mkdir(exist_ok=True)
    (src / "book_to_pdf.json").write_text(json.dumps(mapping, indent=0) + "\n")
    (src / "page_manifest.json").write_text(json.dumps(manifest, indent=0) + "\n")
    print(f"mapped {len(mapping)} pages (p.{a.first} → PDF {a.pdf_first} … PDF {pdf - 1}); "
          f"{len(missing)} missing, {len(blank)} blank")


if __name__ == "__main__":
    main()
