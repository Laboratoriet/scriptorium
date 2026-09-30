"""scriptorium — turn a scanned book into a verified, readable English edition.

Everyday commands:
  new [scan.pdf]      start a book (asks a few questions)
  next                what to do now: inspects the book and names the next step
  status              progress per chapter
  check [unit]        run the checks (page joins, translation invariants, references)
  build [unit]        update the reading site
  preview             open the reading site in your browser
  pdf [a4|a5|bilingual]  print the edition to PDF
  export [unit]       English Markdown

For agents and power users:
  brief NAME          print an agent brief (TRANSCRIBE, TRANSLATE, REVIEW, FIX, …)
  docs [NAME]         print the guide (WORKFLOW, LESSONS, TOOLS)
  tools               list the individual tools
  run TOOL [args]     run one tool on this book
  python [args]       the kit's Python, with this book as context
  doctor              check that everything is installed
"""
import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import yaml

KIT = Path(__file__).resolve().parent
HOME = KIT.parent
SCRIPTS = KIT / "scripts"
PY = sys.executable
TTY = sys.stdout.isatty()

LANGUAGES = {  # name → (code, what reference lists are usually called)
    "german": ("de", "Literatur"), "french": ("fr", "Bibliographie"), "spanish": ("es", "Bibliografía"),
    "italian": ("it", "Bibliografia"), "dutch": ("nl", "Literatuur"), "portuguese": ("pt", "Referências"),
    "swedish": ("sv", "Referenser"), "norwegian": ("no", "Litteratur"), "danish": ("da", "Litteratur"),
    "finnish": ("fi", "Lähteet"), "polish": ("pl", "Bibliografia"), "czech": ("cs", "Literatura"),
    "russian": ("ru", "Литература"), "latin": ("la", "Bibliographia"), "greek": ("el", "Βιβλιογραφία"),
    "japanese": ("ja", "参考文献"), "chinese": ("zh", "参考文献"),
}
RIGHTS = ["public-domain", "own-work", "licensed", "permission", "undecided"]


# ── output ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m" if TTY else s


def dim(s: str) -> str:
    return f"\033[2m{s}\033[0m" if TTY else s


def ok(s: str) -> None:
    print(f"  {bold('✓')} {s}")


def fail(s: str) -> None:
    print(f"  {bold('✗')} {s}")


def die(s: str) -> None:
    sys.exit(f"scriptorium: {s}")


# ── the book ───────────────────────────────────────────────────────────────────────────────────────────────────────

def find_book() -> Path:
    env = os.environ.get("BOOK_ROOT")
    if env:
        return Path(env).resolve()
    for d in [Path.cwd(), *Path.cwd().parents]:
        if (d / "book.yaml").exists():
            return d
    die("not inside a book. `cd` into one, or start one with `scriptorium new scan.pdf`")


def config(book: Path) -> dict:
    return yaml.safe_load((book / "book.yaml").read_text()) or {}


def tool(book: Path, name: str, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
    script = SCRIPTS / f"{name.removesuffix('.py')}.py"
    if not script.exists():
        die(f"no tool called {name!r} (see `scriptorium tools`)")
    env = {**os.environ, "BOOK_ROOT": str(book)}
    return subprocess.run([PY, str(script), *args], cwd=book, env=env, text=True,
                          capture_output=capture)


def load(path: Path, default):
    if not path.exists():
        return default
    return (json.loads(path.read_text()) if path.suffix == ".json" else yaml.safe_load(path.read_text())) or default


def units_of(book: Path) -> list[dict]:
    return load(book / "source" / "units.yaml", [])


def pages_of(unit: dict) -> list[int]:
    return [p for a, b in unit.get("ranges") or [[unit["first"], unit["last"]]] for p in range(a, b + 1)]


def pick_units(book: Path, arg: str | None) -> list[dict]:
    units = units_of(book)
    if not arg or arg == "all":
        return units
    hit = [u for u in units if arg in (str(u["slug"]), u["dir"]) or arg.lstrip("0") == str(u["slug"])]
    if not hit:
        die(f"no unit {arg!r} in source/units.yaml")
    return hit


def invariants_ok(book: Path, d: str) -> tuple[bool, str]:
    r = tool(book, "check_invariants", f"work/{d}/de.md", f"work/{d}/en.md", capture=True)
    out = (r.stdout + r.stderr).strip()
    return "all hard invariants match" in out, out


# ── new ────────────────────────────────────────────────────────────────────────────────────────────────────────────

def ask(question: str, default: str = "") -> str:
    hint = f" {dim('[' + default + ']')}" if default else ""
    try:
        answer = input(f"{bold('?')} {question}{hint} ").strip()
    except EOFError:
        answer = ""
    return answer or default


def choose(question: str, options: list[str], default: str) -> str:
    print(f"{bold('?')} {question}")
    for i, o in enumerate(options, 1):
        print(f"    {i}. {o}")
    answer = ask("  number", str(options.index(default) + 1))
    return options[int(answer) - 1] if answer.isdigit() and 1 <= int(answer) <= len(options) else default


def free_port(start: int = 4800) -> int:
    for port in range(start, start + 100):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def pdf_pages(pdf: Path) -> int:
    try:
        out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        return int(re.search(r"Pages:\s+(\d+)", out).group(1))
    except Exception:
        return 0


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "book"


def q(s) -> str:
    """A YAML scalar."""
    return json.dumps(s, ensure_ascii=False)


def cmd_new(args: list[str]) -> None:
    pdf = Path(args[0]).expanduser().resolve() if args else None
    if pdf and not pdf.exists():
        die(f"{pdf} not found")
    print(bold("\nA new Scriptorium book") + dim("  — press Enter to accept a suggestion\n"))

    title = ask("Original title:")
    if not title:
        die("a title is needed")
    subtitle = ask("Original subtitle:", "")
    authors = [a.strip() for a in ask("Authors (comma-separated):").split(",") if a.strip()]
    year = ask("Year of publication:", "")
    publisher = ask("Publisher:", "")
    lang = ask("Language of the original:", "German").strip()
    code, refs = LANGUAGES.get(lang.lower(), (lang[:2].lower(), "References"))
    title_en = ask("English title:", title)
    subtitle_en = ask("English subtitle:", "")
    print(dim("\n  Rights decide how the translation is made. Claude translates books that are public domain, your own,\n"
              "  licensed or used with permission. For other books, bring your own English and Scriptorium checks it.\n"))
    rights = choose("Rights:", RIGHTS, "undecided")
    translation = "agents" if rights != "undecided" else "supplied"
    translation = choose("Who translates?", ["agents", "supplied"], translation)

    slug = ask("Folder name:", slugify(title_en))
    book = Path.cwd() / slug
    if book.exists():
        die(f"{book} already exists")

    shutil.copytree(KIT / "template", book)
    shutil.copytree(KIT / "site", book / "site",
                    ignore=shutil.ignore_patterns("node_modules", ".next", "out", "content", "*.tsbuildinfo"))
    source_pdf = "book.pdf"
    if pdf:
        source_pdf = pdf.name
        shutil.copy2(pdf, book / "source" / source_pdf)

    values = {
        "slug": slug, "title": q(title), "subtitle": q(subtitle), "title_en": q(title_en),
        "subtitle_en": q(subtitle_en), "authors": q(authors), "year": year or "null", "publisher": q(publisher),
        "source_pdf": source_pdf, "lang_code": code, "lang_name": lang.capitalize(), "lang_short": code.upper(),
        "references_heading": q(refs), "rights": rights, "translation": translation, "site_port": free_port(),
    }
    for name in ("book.yaml", "CLAUDE.md"):
        text = (book / name).read_text()
        for k, v in {**values, "source_name": lang.capitalize(), "authors": ", ".join(authors) if name == "CLAUDE.md"
                     else values["authors"], "title": title if name == "CLAUDE.md" else values["title"],
                     "title_en": title_en if name == "CLAUDE.md" else values["title_en"]}.items():
            text = text.replace("{{" + k + "}}", str(v))
        (book / name).write_text(text)
    tool(book, "sync_book", capture=True)
    print(f"\n{bold('Created')} {book}")

    n = pdf_pages(book / "source" / source_pdf) if pdf else 0
    if n:
        print(dim(f"\n  The PDF has {n} pages. Printed page numbers usually start a few PDF pages in.\n"))
        first_pdf = int(ask("Which PDF page shows printed page 1?", "1"))
        last = int(ask("Last printed page:", str(n - first_pdf + 1)))
        missing = ask("Printed pages missing from the scan (e.g. 6,10 — blank pages often are):", "")
        tool(book, "map_pages", "1", str(last), str(first_pdf), *(["--missing", missing] if missing else []))
        if ask("Render page images now? (needed for transcription; takes a while) y/n", "y").lower().startswith("y"):
            tool(book, "render_pages", "1", str(last))
    print(f"\nNext: {bold(f'cd {slug} && scriptorium next')}")


# ── next / status ──────────────────────────────────────────────────────────────────────────────────────────────────

def ranges(nums: list[int]) -> str:
    out, start = [], None
    for i, n in enumerate(nums):
        if start is None:
            start = n
        if i + 1 == len(nums) or nums[i + 1] != n + 1:
            out.append(f"{start}" if start == n else f"{start}–{n}")
            start = None
    return ", ".join(out[:6]) + (" …" if len(out) > 6 else "")


def next_steps(book: Path) -> list[str]:
    """The first unfinished step, as text. Order follows docs/WORKFLOW.md."""
    cfg = config(book)
    src = book / "source"
    pdf = src / cfg.get("source_pdf", "book.pdf")
    if not pdf.exists():
        return [f"Put the scanned PDF at {pdf.relative_to(book)} (or change `source_pdf` in book.yaml)."]
    manifest = load(src / "page_manifest.json", {})
    if not manifest:
        return ["Map printed pages to PDF pages:",
                "  scriptorium run map_pages 1 <last printed page> <PDF page of printed page 1> [--missing 6,10]"]
    scanned = sorted(int(p) for p, s in manifest.items() if s == "scanned")
    unrendered = [p for p in scanned if not (src / "pages" / f"{p:04d}" / "pdf.png").exists()]
    if unrendered:
        return [f"Render page images ({len(unrendered)} to go):",
                f"  scriptorium run render_pages {unrendered[0]} {unrendered[-1]}"]
    if not load(src / "toc.yaml", []):
        return ["Transcribe the printed table of contents into source/toc.yaml (English titles: source/toc_en.yaml).",
                "  With Claude: “transcribe the contents pages into source/toc.yaml following its header comment.”"]
    units = units_of(book)
    if not units:
        return ["Split the book into reading units (chapters) in source/units.yaml — see its header comment.",
                "  With Claude: “propose units.yaml from the table of contents.”"]

    todo = [p for p in scanned if not (src / "pages" / f"{p:04d}" / "de.md").exists()]
    for u in units:  # unit by unit, so a pilot chapter can go all the way through first
        d, pages = u["dir"], [p for p in pages_of(u) if p in scanned]
        work = book / "work" / d
        missing = [p for p in pages if p in todo]
        if missing:
            done = len(scanned) - len(todo)
            return [f"Transcribe {u['title_en']}: pages {ranges(missing)}  ({done}/{len(scanned)} pages in the book done)",
                    "  With Claude: “transcribe pages N–M”, using `scriptorium brief TRANSCRIBE` (≈4 pages per agent)."]
        if not (work / "de.md").exists() or any(
                (src / "pages" / f"{p:04d}" / "de.md").stat().st_mtime > (work / "de.md").stat().st_mtime for p in pages):
            return [f"Join the pages of {u['title_en']}:", f"  scriptorium run join_unit {u['slug']}"]
        if not (work / "en.md").exists():
            if cfg.get("translation") == "supplied":
                return [f"Add the English for {u['title_en']} at work/{d}/en.md,",
                        "  laid out like de.md: same headings and paragraphs, page anchors and {{fig:…}} placeholders copied over."]
            return [f"Translate {u['title_en']}:",
                    f"  With Claude: “translate unit {u['slug']}”, using `scriptorium brief TRANSLATE`."]
        good, _ = invariants_ok(book, d)
        if not good:
            return [f"The English of {u['title_en']} doesn't match the original yet:",
                    f"  scriptorium check {u['slug']}   (then fix work/{d}/en.md)"]
        if not (work / "review.md").exists():
            return [f"Review {u['title_en']} (an independent reader, then a fixer):",
                    f"  With Claude: “review unit {u['slug']}”, using `scriptorium brief REVIEW` then `FIX`."]
        built = book / "site" / "content" / "units" / f"{u['slug']}.json"
        if not built.exists() or built.stat().st_mtime < (work / "en.md").stat().st_mtime:
            return [f"Put {u['title_en']} on the site:", f"  scriptorium build {u['slug']}"]
    if not (book / "site" / "out" / "index.html").exists():
        return ["Build the reading site:", "  scriptorium build"]
    return ["Every unit is transcribed, translated, reviewed and on the site.",
            "  scriptorium preview · scriptorium pdf · figures and references: `scriptorium docs WORKFLOW` phases 5–6"]


def cmd_next(_: list[str]) -> None:
    book = find_book()
    cfg = config(book)
    print(f"{bold(cfg.get('title_en') or cfg.get('title', book.name))}\n")
    if cfg.get("rights") == "undecided" and cfg.get("translation") == "agents":
        print(dim("  note: rights are undecided — Claude may decline to translate. See book.yaml.\n"))
    steps = next_steps(book)
    print(f"{bold('Next:')} {steps[0]}")
    for line in steps[1:]:
        print(line)


def cmd_status(_: list[str]) -> None:
    book = find_book()
    tool(book, "coverage")
    print()
    cmd_next([])


# ── check / build ──────────────────────────────────────────────────────────────────────────────────────────────────

def cmd_check(args: list[str]) -> None:
    book = find_book()
    bad = 0
    for u in pick_units(book, args[0] if args else None):
        d = u["dir"]
        work = book / "work" / d
        if not (work / "de.md").exists():
            continue
        print(bold(u["title_en"]))
        r = tool(book, "check_references", f"work/{d}/de.md", capture=True)
        refs = [l for l in r.stdout.splitlines() if l.startswith("list")]
        refs_bad = [l for l in refs if "sequential=False" in l or any(re.findall(r"=\[([^\]]+)\]", l))]
        (fail if refs_bad else ok)(f"references: {len(refs)} list(s)" + (f" — {'; '.join(refs_bad)}" if refs_bad else ""))
        bad += bool(refs_bad)
        if (work / "en.md").exists():
            good, out = invariants_ok(book, d)
            if good:
                ok("translation matches the original (numbers, references, figures, paragraphs)")
            else:
                fail("translation doesn't match yet:")
                print("\n".join("      " + l for l in out.splitlines()))
                bad += 1
        else:
            print(dim("  · not translated yet"))
    print()
    print(bold("All checks pass.") if not bad else bold(f"{bad} problem(s) to fix."))
    sys.exit(1 if bad else 0)


def site_build(book: Path) -> bool:
    site = book / "site"
    if not (site / "node_modules").exists():
        print(dim("installing the site's packages (first build only)…"))
        if subprocess.run(["npm", "ci", "--silent", "--no-fund", "--no-audit"], cwd=site).returncode:
            return False
    r = subprocess.run(["npm", "run", "build", "--silent"], cwd=site, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        return False
    return True


def cmd_build(args: list[str]) -> None:
    book = find_book()
    tool(book, "sync_book", capture=True)
    built = 0
    for u in pick_units(book, args[0] if args else None):
        if (book / "work" / u["dir"] / "en.md").exists():
            r = tool(book, "build_content", str(u["slug"]), capture=True)
            if r.returncode:
                print(r.stdout, r.stderr)
                die(f"building {u['title_en']} failed")
            ok(u["title_en"])
            built += 1
    if not built:
        print(dim("  no translated units yet — building the empty site"))
    print(dim("building the site…"))
    if not site_build(book):
        die("the site build failed (output above)")
    ok(f"site ready — `scriptorium preview`")


# ── preview / pdf / export ─────────────────────────────────────────────────────────────────────────────────────────

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def serve(book: Path) -> tuple[socketserver.TCPServer, int]:
    out = book / "site" / "out"
    if not (out / "index.html").exists():
        die("the site isn't built yet — run `scriptorium build`")
    port = config(book).get("site_port", 4800)
    handler = lambda *a, **k: Quiet(*a, directory=str(out), **k)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    except OSError:
        die(f"port {port} is in use — change site_port in book.yaml")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def cmd_preview(_: list[str]) -> None:
    book = find_book()
    server, port = serve(book)
    url = f"http://127.0.0.1:{port}/"
    print(f"Reading site at {bold(url)}  {dim('(Ctrl-C to stop)')}")
    webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


def cmd_pdf(args: list[str]) -> None:
    book = find_book()
    editions = ["a4", "a5", "bilingual"] if args[:1] == ["all"] else (args or ["a4"])
    server, _ = serve(book)
    try:
        for e in editions:
            if tool(book, "make_pdf", "--edition", e).returncode:
                die(f"the {e} PDF failed")
    finally:
        server.shutdown()


def cmd_export(args: list[str]) -> None:
    book = find_book()
    for u in pick_units(book, args[0] if args else None):
        if (book / "work" / u["dir"] / "en.md").exists():
            tool(book, "export_markdown", str(u["slug"]))


# ── agents and power users ─────────────────────────────────────────────────────────────────────────────────────────

def cmd_brief(args: list[str]) -> None:
    briefs = {p.stem.upper(): p for p in (KIT / "briefs").rglob("*.md")}
    if not args or args[0].upper() not in briefs:
        print("Briefs: " + ", ".join(sorted(briefs)))
        sys.exit(0 if not args else 1)
    p = briefs[args[0].upper()]
    print(f"<!-- {p} -->\n" + p.read_text())


def cmd_docs(args: list[str]) -> None:
    docs = {p.stem.upper(): p for p in (HOME / "docs").glob("*.md")}
    name = (args[0] if args else "WORKFLOW").upper()
    if name not in docs:
        die("docs: " + ", ".join(sorted(docs)))
    print(docs[name].read_text())


def cmd_tools(_: list[str]) -> None:
    import ast
    for p in sorted(SCRIPTS.glob("*.py")):
        if p.stem == "bookroot":
            continue
        doc = (ast.get_docstring(ast.parse(p.read_text())) or "").splitlines()
        print(f"  {bold(p.stem):<32} {doc[0] if doc else ''}" if TTY else f"  {p.stem:<24} {doc[0] if doc else ''}")
    print(dim("\n  scriptorium run <tool> …   — each tool's first lines (docs/TOOLS.md) say how to use it"))


def cmd_run(args: list[str]) -> None:
    if not args:
        cmd_tools([])
        return
    sys.exit(tool(find_book(), args[0], *args[1:]).returncode)


def cmd_python(args: list[str]) -> None:
    book = find_book()
    env = {**os.environ, "BOOK_ROOT": str(book), "PYTHONPATH": str(SCRIPTS)}
    sys.exit(subprocess.run([PY, *args], env=env).returncode)


def cmd_doctor(_: list[str]) -> None:
    good = True
    ok(f"Python {sys.version.split()[0]} at {PY}")
    for mod in ("yaml", "markdown_it", "PIL", "numpy", "pypdf", "requests", "playwright"):
        try:
            __import__(mod)
            ok(mod)
        except ImportError:
            fail(f"{mod} — run install.sh again")
            good = False
    for mod in ("rdkit", "cairosvg"):
        try:
            __import__(mod)
            ok(f"{mod} (chemistry)")
        except Exception:
            print(dim(f"  · {mod} not available — only needed for chemistry books"))
    for cmd, why in [("pdftoppm", "poppler — page images"), ("pdfinfo", "poppler"), ("node", "the reading site"),
                     ("npm", "the reading site"), ("gs", "ghostscript — smaller PDFs"), ("tesseract", "upscale checks")]:
        if shutil.which(cmd):
            ok(cmd)
        else:
            fail(f"{cmd} missing ({why}) — brew install poppler node ghostscript tesseract")
            good = good and cmd in ("gs", "tesseract")
    print()
    print(bold("Ready.") if good else bold("Some things are missing (above)."))


COMMANDS = {
    "new": cmd_new, "next": cmd_next, "status": cmd_status, "check": cmd_check, "build": cmd_build,
    "preview": cmd_preview, "pdf": cmd_pdf, "export": cmd_export, "brief": cmd_brief, "docs": cmd_docs,
    "tools": cmd_tools, "run": cmd_run, "python": cmd_python, "doctor": cmd_doctor,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd = COMMANDS.get(sys.argv[1])
    if not cmd:
        die(f"unknown command {sys.argv[1]!r} — try `scriptorium help`")
    cmd(sys.argv[2:])


if __name__ == "__main__":
    main()
