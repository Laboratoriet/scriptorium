"""Join verified German pages (source/pages/NNNN/de.md) into one chapter file.

Usage: scriptorium run join_pages <first_page> <last_page> <out_dir>
Example: scriptorium run join_pages 49 66 work/ch02

- Strips each page's front matter and inserts a page anchor <!-- p.N -->.
- Where a page continues the previous one mid-sentence, the text is joined
  into the same paragraph (the anchor sits inline).
- A word split across the page break ("rei-" + "ne") is merged and reported,
  because it could also be a real hyphen.
- Missing pages are checked against source/page_manifest.json: blank
  section-break pages are skipped, anything else stops the join.
"""
import json
import re
import sys
from pathlib import Path

from bookroot import ROOT  # the book project (book.yaml), not the kit
PAGES = ROOT / "source" / "pages"


def read_page(n: int) -> tuple[dict, str]:
    text = (PAGES / f"{n:04d}" / "de.md").read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        sys.exit(f"p.{n}: no front matter")
    front, body = match.groups()
    meta = {}
    for key in ("continues_from_previous", "continues_on_next"):
        found = re.search(rf"^{key}:\s*(true|false)", front, re.M)
        meta[key] = found and found.group(1) == "true"
    return meta, body.strip()


FOOTNOTE = re.compile(r"^<sup>(\w)\)</sup>\s*(.*)$", re.S)


def split_footnotes(n: int, body: str, notes: list[str]) -> tuple[str, list[str]]:
    """Move a page's footnotes (trailing '<sup>a)</sup> …' paragraphs, optionally
    after a '---' rule) into Markdown footnotes [^p0052-a], so text that continues
    on the next page isn't interrupted by them."""
    footnotes = []
    # A footnote section starts at a line that is just "---" (the rule printed above
    # the footnotes), whether or not a blank line follows it.
    rule = re.search(r"(?:^|\n)---\n(?=\s*<sup>\w\)</sup>)", body)
    if rule:
        main, section = body[: rule.start()], body[rule.end():]
        for chunk in re.split(r"\n(?=\s*<sup>\w\)</sup>)", section.strip()):
            m = FOOTNOTE.match(chunk.strip())
            if m:
                footnotes.append((m.group(1), re.sub(r"\s*\n\s*", " ", m.group(2).strip())))
        main = main.rstrip()
    else:
        paras = body.split("\n\n")
        while paras and (FOOTNOTE.match(paras[-1].strip()) or paras[-1].strip() == "---"):
            para = paras.pop().strip()
            if para != "---":
                footnotes.insert(0, FOOTNOTE.match(para).groups())
        main = "\n\n".join(paras)

    definitions = []
    for key, text in footnotes:
        ref = f"[^p{n:04d}-{key}]"
        marker = f"<sup>{key})</sup>"
        if marker in main:
            main = main.replace(marker, ref, 1)
        else:
            main = main.rstrip() + ref
            notes.append(f"p.{n}: footnote {key}) has no marker in the printed text — attached to the page's last paragraph")
        definitions.append(f"{ref}: {text}")
    return main, definitions


def main(first: int, last: int, out_dir: Path, skip: set[int] = frozenset()) -> None:
    manifest = json.loads((ROOT / "source" / "page_manifest.json").read_text())
    out = ""
    notes = []
    footnotes = []
    held_figures: list[str] = []
    prev_continues = False

    for n in range(first, last + 1):
        if n in skip:  # pages of another unit (an excursus inside a chapter)
            continue
        status = manifest[str(n)]
        if status == "missing-likely-blank":
            notes.append(f"p.{n}: skipped (blank section-break page)")
            continue
        if status != "scanned" or not (PAGES / f"{n:04d}" / "de.md").exists():
            sys.exit(f"p.{n}: no verified de.md ({status}) — transcribe it first")

        meta, body = read_page(n)
        body, page_footnotes = split_footnotes(n, body, notes)
        footnotes += page_footnotes
        anchor = f"<!-- p.{n} -->"

        if meta["continues_from_previous"]:
            if not prev_continues:
                notes.append(f"p.{n}: continues_from_previous, but p.{n-1} doesn't say it continues")
            # Figures printed at the top of a page sit before the text that carries
            # over; the continued paragraph has to be joined first, figures after it.
            paras = body.split("\n\n")
            top_figures = held_figures
            held_figures = []
            # Figures printed at the bottom of the previous page, after the text that
            # continues here, also belong after the continued paragraph.
            out_blocks = out.split("\n\n")
            bottom_figures = []
            while out_blocks and out_blocks[-1].lstrip().startswith("{{fig:"):
                bottom_figures.insert(0, out_blocks.pop().strip())
            if bottom_figures:
                out = "\n\n".join(out_blocks)
                top_figures = bottom_figures + top_figures
                notes.append(f"p.{n-1}: {len(bottom_figures)} figure(s) at the bottom of the page moved after the continued paragraph")
            while paras and paras[0].lstrip().startswith("{{fig:"):
                top_figures.append(paras.pop(0).strip())
            if top_figures and not paras:
                # A figure-only page inside a running sentence (e.g. a full-page figure):
                # hold its figures until the sentence ends on a later page.
                held_figures = top_figures
                notes.append(f"p.{n}: figure-only page inside a running paragraph — figures placed after it")
                out = out + " " + anchor
                prev_continues = meta["continues_on_next"]
                continue
            if top_figures:
                paras = paras[:1] + top_figures + paras[1:]
                notes.append(f"p.{n}: {len(top_figures)} figure(s) at the top of the page moved after the continued paragraph")
            body = "\n\n".join(paras).lstrip("…").lstrip()
            if out.endswith("-") and body[:1].islower():
                first_word, rest = (body.split(None, 1) + [""])[:2]
                word_start = out.rsplit(None, 1)[-1]
                notes.append(f"p.{n}: merged split word '{word_start[:-1]}{first_word}' — check hyphen")
                out = out[:-1] + first_word + " " + anchor + " " + rest
            elif re.match(r"^\[\d+\]", body):
                # A literature list running over the page: the next entry starts its own line.
                out = out + "\n" + anchor + "\n" + body
            else:
                out = out + " " + anchor + " " + body
        else:
            if prev_continues:
                notes.append(f"p.{n-1} says it continues, but p.{n} doesn't")
            out = out + ("\n\n" if out else "") + anchor + "\n\n" + body

        prev_continues = meta["continues_on_next"]

    if held_figures:
        out = out.rstrip() + "\n\n" + "\n\n".join(held_figures)
    if footnotes:
        out = out.rstrip() + "\n\n" + "\n\n".join(footnotes)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "de.md").write_text(out.strip() + "\n")
    (out_dir / "join_notes.txt").write_text("\n".join(notes) + "\n")
    print(f"wrote {out_dir / 'de.md'} ({len(out.split())} words)")
    print("\n".join(notes) or "no notes")


if __name__ == "__main__":
    # Optional: --skip 521-530,615-630 leaves out the pages of excursuses printed inside a chapter.
    args = sys.argv[1:]
    skip: set[int] = set()
    if "--skip" in args:
        i = args.index("--skip")
        for part in args[i + 1].split(","):
            a, _, b = part.partition("-")
            skip |= set(range(int(a), int(b or a) + 1))
        args = args[:i] + args[i + 2:]
    if len(args) != 3:
        sys.exit(__doc__)
    main(int(args[0]), int(args[1]), ROOT / args[2], skip)
