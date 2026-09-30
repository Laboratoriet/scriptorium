"""One complete English PDF of the edition, printed from the built site (site/out, served on 127.0.0.1:4800).

Usage: scriptorium run make_pdf [--edition a4|a5|bilingual]
Output: pdf/<slug>-EN.pdf (A4), -EN-A5.pdf (tablet), -EN-SRC.pdf (A4 landscape, English | source language for
proofreading) — private, like the site; not published anywhere.

Each unit page is printed by headless Chromium with the site's print styles (German, navigation and scans hidden;
translator's notes inline). The page is laid out at the exact printed width first, so the class-map arrows are
measured where they will print, lazy images are loaded, and any figure wider than the page is scaled to fit.
Then: title page + contents with start pages, merged, one bookmark per unit, continuous page numbers, and a
reading copy with images at 200 dpi (Ghostscript) next to the full-resolution file.
"""
import html
import json
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
BASE = f"http://127.0.0.1:{CONFIG.get('site_port', 4800)}"
# Page geometry per edition (mm): size, margins (top, sides, bottom), body size; the layout width is the page minus
# the side margins at 96 dpi, so the site is laid out exactly as it prints (class-map arrows, figure scaling).
EDITIONS = {
    "a4": {"out": "{slug}-EN.pdf", "w": 210, "h": 297, "m": (20, 18, 22), "body": "10.5pt", "attr": None},
    "a5": {"out": "{slug}-EN-A5.pdf", "w": 148, "h": 210, "m": (14, 13, 16), "body": "9.5pt", "attr": None},
    "bilingual": {"out": "{slug}-EN-SRC.pdf", "w": 297, "h": 210, "m": (14, 14, 16), "body": "9pt",
                  "attr": "bilingual"},
}

PREPARE = """async (pageHeight) => {
  for (const img of document.querySelectorAll('img')) { img.loading = 'eager'; }
  // Translator's notes print in full: a closed <details> never renders its content, whatever the CSS says.
  for (const d of document.querySelectorAll('.tn-inline details')) { d.open = true; }
  await Promise.all([...document.images].map(i => i.complete ? null : new Promise(r => { i.onload = i.onerror = r; })));
  // Chrome evaluates width breakpoints against a wider box when it prints than the page really has (A5 prints the
  // 640px+ layout). Freeze what every responsive element looks like at the true print width.
  for (const el of document.querySelectorAll('[class*="sm:"],[class*="md:"],[class*="lg:"],[class*="xl:"]')) {
    const cs = getComputedStyle(el);
    el.style.setProperty('display', cs.display, 'important');
    if (cs.display === 'grid') el.style.setProperty('grid-template-columns', cs.gridTemplateColumns, 'important');
  }
  let scaled = 0;
  // Wider than the page: scale to the page width.
  for (const box of document.querySelectorAll('figure .overflow-x-auto')) {
    const inner = box.firstElementChild;
    if (!inner) continue;
    const need = inner.scrollWidth, have = box.clientWidth;
    if (need > have + 2) { inner.style.zoom = (have / need).toFixed(3); scaled++; }
  }
  // Taller than a page (class maps on landscape pages): scale to the page height, so a figure never splits.
  for (const fig of document.querySelectorAll('figure')) {
    const h = fig.getBoundingClientRect().height;
    if (h > pageHeight * 0.96) { fig.style.zoom = (pageHeight * 0.92 / h).toFixed(3); scaled++; }
  }
  await new Promise(r => setTimeout(r, 500));  // class-map arrows re-measure after the layout changes
  return scaled;
}"""


def units() -> list[dict]:
    out = []
    for f in (ROOT / "site" / "content" / "units").glob("*.json"):
        d = json.loads(f.read_text())
        out.append({"slug": d["slug"], "title": d.get("title_en") or d["title_de"], "first": d["first"]})
    return sorted(out, key=lambda u: u["first"])


def page_css(e: dict) -> str:
    t, x, b = e["m"]
    return f"@page {{ size: {e['w']}mm {e['h']}mm; margin: {t}mm {x}mm {b}mm; }}"


def front_html(entries: list[tuple[str, int]] | None, e: dict) -> str:
    rows = "".join(f'<tr><td>{html.escape(t)}</td><td class="n">{p}</td></tr>' for t, p in entries or [])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
      {page_css(e)}
      body {{ font-family: "Source Serif 4", Georgia, serif; color: #111; }}
      .title {{ height: {e["h"] - e["m"][0] - e["m"][2] - 12}mm; display: flex; flex-direction: column; justify-content: center; }}
      .authors {{ font: 600 9pt/1.4 "Source Sans 3", system-ui, sans-serif; letter-spacing: .14em; text-transform: uppercase; color: #555; }}
      h1 {{ font-size: 40pt; margin: 14pt 0 4pt; letter-spacing: -.01em; }}
      .sub {{ font-size: 20pt; font-style: italic; color: #333; margin: 0; }}
      .note {{ margin-top: 28pt; max-width: 120mm; font: 10pt/1.5 "Source Sans 3", system-ui, sans-serif; color: #333; }}
      .toc {{ break-before: page; }}
      h2 {{ font: 600 10pt "Source Sans 3", system-ui, sans-serif; letter-spacing: .1em; text-transform: uppercase; color: #555; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 11pt; }}
      td {{ padding: 5pt 0; border-bottom: .5pt solid #ddd; }} td.n {{ text-align: right; font-variant-numeric: tabular-nums; width: 3em; }}
    </style></head><body>
      <section class="title">
        <div class="authors">{html.escape(" · ".join(CONFIG.get("authors", [])))}</div>
        <h1>{html.escape(CONFIG.get("title_en", CONFIG.get("title", "")))}</h1><p class="sub">{html.escape(CONFIG.get("subtitle_en", ""))}</p>
        {'<p class="sub" style="font-size:13pt;margin-top:10pt">' + html.escape(CONFIG.get("bilingual_label", "Parallel edition for proofreading")) + '</p>' if e["attr"] == "bilingual" else ""}
        <p class="note">{CONFIG.get("edition_note", "")}</p>
      </section>
      <section class="toc"><h2>Contents</h2><table>{rows}</table></section>
    </body></html>"""


def main(edition: str) -> None:
    e = EDITIONS[edition]
    OUT = ROOT / "pdf" / e["out"].format(slug=CONFIG.get("slug", ROOT.name))
    width = round((e["w"] - 2 * e["m"][1]) / 25.4 * 96)
    OUT.parent.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    order = units()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1100})
        page.emulate_media(media="print")
        parts = []
        for u in order:
            page.goto(f"{BASE}/chapter/{u['slug']}/", wait_until="load")
            page.add_style_tag(content=f"@media print {{ {page_css(e)} body {{ font-size: {e['body']}; }} }}")
            if e["attr"]:
                page.evaluate(f"document.documentElement.setAttribute('data-print', '{e['attr']}')")
            scaled = page.evaluate(PREPARE, (e["h"] - e["m"][0] - e["m"][2]) / 25.4 * 96)
            target = tmp / f"{u['first']:04d}-{u['slug']}.pdf"
            page.pdf(path=str(target), prefer_css_page_size=True, print_background=True)
            n = len(PdfReader(str(target)).pages)
            parts.append((u, target, n))
            print(f"{u['slug']:>28}: {n:3d} pages{f', {scaled} wide figure(s) scaled' if scaled else ''}")

        # Front matter twice: once to count its pages, then with the real start pages in the contents.
        page.set_content(front_html([(u["title"], 0) for u, _, _ in parts], e))
        page.pdf(path=str(tmp / "front.pdf"), prefer_css_page_size=True)
        front_n = len(PdfReader(str(tmp / "front.pdf")).pages)
        start, entries = front_n + 1, []
        for u, _, n in parts:
            entries.append((u["title"], start))
            start += n
        page.set_content(front_html(entries, e))
        page.pdf(path=str(tmp / "front.pdf"), prefer_css_page_size=True)
        total = start - 1

        # Page numbers (not on the title page), printed as a separate PDF and stamped onto each page.
        numbers = "".join(f'<div class="p">{"" if i == 1 else i}</div>' for i in range(1, total + 1))
        page.set_content(f"""<!doctype html><html><head><style>@page {{ size: {e['w']}mm {e['h']}mm; margin: 0; }}
            body {{ margin: 0; }} .p {{ height: {e['h']}mm; box-sizing: border-box; padding-top: {e['h'] - e['m'][2] + 4}mm; text-align: center;
            font: 8.5pt "Source Sans 3", system-ui, sans-serif; color: #666; break-after: page; }}</style></head>
            <body>{numbers}</body></html>""")
        page.pdf(path=str(tmp / "numbers.pdf"), prefer_css_page_size=True)
        browser.close()

    writer = PdfWriter()
    writer.append(str(tmp / "front.pdf"))
    for (u, path, _), (_, first) in zip(parts, entries):
        writer.append(str(path))
        writer.add_outline_item(u["title"], first - 1)
    nums = PdfReader(str(tmp / "numbers.pdf")).pages
    for i, pg in enumerate(writer.pages):
        if i < len(nums):
            pg.merge_page(nums[i])
    writer.add_metadata({"/Title": f"{CONFIG.get('title_en', '')} (English working edition)",
                         "/Author": ", ".join(CONFIG.get("authors", []))})
    full = OUT.with_name(OUT.stem + "-full-res.pdf")
    with open(full, "wb") as fh:
        writer.write(fh)
    # Reading copy: images at 200 dpi (plenty for scans and restored figures); text and structures stay vector.
    subprocess.run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.7",
                    "-dDownsampleColorImages=true", "-dColorImageResolution=200", "-dDownsampleGrayImages=true",
                    "-dGrayImageResolution=200", "-dColorImageDownsampleType=/Bicubic", "-dGrayImageDownsampleType=/Bicubic",
                    f"-sOutputFile={OUT}", str(full)], check=True)
    print(f"{total} pages → {OUT} ({OUT.stat().st_size / 1e6:.1f} MB; full resolution {full.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", choices=sorted(EDITIONS), default="a4")
    main(ap.parse_args().edition)
