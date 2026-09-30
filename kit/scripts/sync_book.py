"""Carry book.yaml into the places that can't read it: site/src/book.json and the {{…}} fields of CLAUDE.md.

Usage: scriptorium run sync_book

book.json keeps any fields you edited by hand (intro, description, searchExamples); only the fields that come
from book.yaml are overwritten. CLAUDE.md placeholders are filled once — after that the file is yours.
"""
import html
import json

from bookroot import CONFIG, ROOT


def main() -> None:
    src = CONFIG.get("languages", {}).get("source", {"code": "de", "name": "German", "short": "DE"})
    authors = CONFIG.get("authors", [])
    title, year, publisher = CONFIG.get("title", ""), CONFIG.get("year", ""), CONFIG.get("publisher", "")

    path = ROOT / "site" / "src" / "book.json"
    book = json.loads(path.read_text()) if path.exists() else {}
    book.update({
        "title": CONFIG.get("title_en", title),
        "subtitle": CONFIG.get("subtitle_en", ""),
        "authors": authors,
        "original": f"<em>{html.escape(title)}</em> ({', '.join(str(x) for x in (publisher, year) if x)})",
        "source": {"code": src["code"], "name": src["name"], "short": src.get("short", src["code"].upper())},
    })
    if not book.get("intro"):  # empty in the template
        book["intro"] = (f"A private English working edition of <em>{html.escape(title)}</em>, "
                         "translated from a verified transcription of the original.")
    book.setdefault("description", "Private English working edition.")
    book.setdefault("searchExamples", {"en": "e.g. keyword, p. 12", "source": "e.g. keyword, p. 12"})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=2, ensure_ascii=False) + "\n")

    claude = ROOT / "CLAUDE.md"
    if claude.exists():
        text = claude.read_text()
        for key, val in {"title_en": CONFIG.get("title_en", title), "title": title, "year": year,
                         "authors": ", ".join(authors), "source_name": src["name"]}.items():
            text = text.replace("{{" + key + "}}", str(val))
        claude.write_text(text)
    print(f"synced {path.relative_to(ROOT)} and CLAUDE.md from book.yaml")


if __name__ == "__main__":
    main()
