"""Build the site's content for one chapter from work/chNN/{de,en}.md.

Usage: scriptorium run build_content 02

Output:
  site/content/chNN.json   — aligned blocks (EN html + DE html, sidenotes, figures, refs)
  site/public/structures/  — structure SVGs used by the chapter
  site/public/figures/     — original figure crops (adverts, chart originals) as WebP

German and English paragraphs are aligned 1:1 (check_invariants.py guarantees it).
Markup handled here:
  **n**            compound number → link to its structure
  [n], [21, 33-38] citations → links to the reference list
  [^id]            footnote reference
  <!-- TN: … -->   translator's note → numbered sidenote on the block
  <!-- p.N -->     page break → small page marker (inline) or block page
  {{fig:…}}        figure placeholder → figure block
"""
import json
import re
from html import escape as html_escape
import shutil
import sys
from pathlib import Path

import yaml
from markdown_it import MarkdownIt
from PIL import Image

from bookroot import ROOT  # the book project (book.yaml), not the kit
SITE = ROOT / "site"
md = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table")

PAGE_ONLY = re.compile(r"^<!-- p\.(\w+) -->$")  # arabic, roman (front matter), or cover/impressum/…
TN = re.compile(r"\s*<!-- TN:\s*(.*?)\s*-->", re.S)
INLINE_PAGE = re.compile(r"\s*<!-- p\.(\w+) -->\s*")
FIG = re.compile(r"^\{\{fig:(.*)\}\}$", re.S)
ROMAN = re.compile(r"^[IVXLC]+$")


def page_value(anchor: str) -> int | str | None:
    """Printed page of an anchor: 49 → 49, "XV" → "XV"; unnumbered pages (cover, imprint …) → None."""
    if anchor.isdigit():
        return int(anchor)
    return anchor if ROMAN.match(anchor) else None


def blocks_of(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def parse_fig(raw: str) -> dict:
    parts = [p.strip() for p in raw.split("|")]
    fig = {"id": parts[0]}
    for part in parts[1:]:
        key, _, value = part.partition(":")
        value = value.strip()
        if value.startswith("["):
            items = value.strip("[]")
            if key.strip() == "labels":
                fig[key.strip()] = re.findall(r'"([^"]*)"', items)
            else:
                # Compound numbers are sometimes quoted in placeholders ("2a"); the key is the bare number.
                fig[key.strip()] = [v.strip().strip('"') for v in items.split(",") if v.strip()]
        else:
            fig[key.strip()] = value.strip('"')
    return fig


def caption_by_compound(caption: str, compounds: list[str]) -> dict:
    """'2: R-Epinephrin (R-Adrenalin) / 3: Ephedrin' → {'2': [...], '3': [...]}.
    A caption without 'n:' prefixes belongs to the figure's only compound."""
    if len(compounds) == 1 and not re.match(r"^\w+:", caption):
        return {compounds[0]: [n.strip() for n in caption.split(" / ")]}
    parts = [n.strip() for n in caption.split(" / ")]
    if all(c.startswith("u") for c in compounds) and len(parts) == len(compounds):
        # Unnumbered structures (ids u1, u2 …): the caption names them in drawing order.
        return {c: [n] for c, n in zip(compounds, parts)}
    names = {}
    for num, text in re.findall(r"(\w+):\s*(.*?)(?=(?:\s*[;/]\s*\w+:)|$)", caption):
        # A bare "13" between names is another compound of the figure printed without a name.
        names[num] = [n.strip() for n in re.split(r"\s+/\s+", text.strip(" ;")) if n.strip() not in compounds]
    return names


def inline(text: str, chapter: str, compounds: set[str], in_refs: bool = False, ref_scope: int = 0,
           cpd_scope: str | None = None, multi_scope: bool = False) -> str:
    """Markdown → HTML for one block, then link compound numbers and citations."""
    text = INLINE_PAGE.sub(lambda m: f' <span class="pb" data-page="{m.group(1)}"></span> ', text)
    # A synthesis omission inside a paragraph (sentence-level cut): a short bracketed notice.
    text = re.sub(r'\{\{omitted:\s*\w+\s*\|\s*pages:\s*([^|]+?)\s*\|\s*note:\s*"(.*?)"\s*\}\}',
                  lambda m: f'<em class="omitted" title="{m.group(2)}">[synthesis passage not included, p. {m.group(1)}]</em>',
                  text)
    text = re.sub(r"\[\^([\w-]+)\](?!:)", r'<sup class="fn"><a href="#fn-\1" id="fnref-\1">*</a></sup>', text)
    html = md.render(text).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    if in_refs:
        return html

    def compound(m: re.Match) -> str:
        num = m.group(1)
        key = f"{chapter}-{cpd_scope}-{num}" if multi_scope and cpd_scope else f"{chapter}-{num}"
        if key not in compounds:
            return m.group(0)
        return f'<a class="cpd" href="#cpd-{key}" data-cpd="{key}">{num}</a>'

    html = re.sub(r"<strong>(\d+[a-z]?)</strong>", compound, html)

    def cite(m: re.Match) -> str:
        inner = re.sub(r"\d+", lambda n: f'<a href="#ref-{ref_scope}-{n.group(0)}">{n.group(0)}</a>', m.group(1))
        return f'<span class="cite">[{inner}]</span>'

    return link_chapters(re.sub(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]", cite, html))


SECTION_UNIT: dict[str, str] | None = None
CHAPTER_REF = re.compile(r"\b((?:[Cc]hapters?|[Kk]apitels?|[Kk]apiteln)\s+)(\d+(?:\.\d+)*\.?(?:(?:\s*,\s*|\s+(?:and|und|&|or|oder)\s+|\s*,\s*(?:and|und)\s+|\s*[–-]\s*)\d+(?:\.\d+)*\.?)*)")


def link_chapters(html: str) -> str:
    """Cross-references in the text ("chapter 3.1.1", "Chapter 3.12.3, 3.12.4 and …", "Kapitel 6.2") → links to
    those sections, wherever they are in the edition. Numbers with no translated section stay plain text."""
    global SECTION_UNIT
    if SECTION_UNIT is None:
        SECTION_UNIT = {e["id"]: e["unit"] for e in read_json(SITE / "content" / "toc.json", [])
                        if e.get("available") and e.get("unit") and re.fullmatch(r"\d+(?:\.\d+)*", e["id"])}

    def numbers(m: re.Match) -> str:
        def one(n: re.Match) -> str:
            num = n.group(0).rstrip(".")
            unit = SECTION_UNIT.get(num)
            if not unit:
                return n.group(0)
            href = f"/chapter/{unit}/" if "." not in num else f"/chapter/{unit}/#s-{num}"
            # A trailing full stop ("8.4." as printed, or the sentence's) stays outside the link.
            return f'<a class="xref" href="{href}">{num}</a>' + n.group(0)[len(num):]
        return m.group(1) + re.sub(r"\d+(?:\.\d+)*\.?", one, m.group(2))

    # Only in text, never inside tags or existing links.
    out, depth = [], 0
    for part in re.split(r"(<[^>]+>)", html):
        if part.startswith("<"):
            if re.match(r"<a[\s>]", part):
                depth += 1
            elif part.startswith("</a"):
                depth = max(0, depth - 1)
            out.append(part)
        else:
            out.append(part if depth else CHAPTER_REF.sub(numbers, part))
    return "".join(out)


def read_yaml(path: Path, default):
    """Optional inputs (a book without compounds, restored images, …) read as empty."""
    return (yaml.safe_load(path.read_text()) or default) if path.exists() else default


def read_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


# Second halves of two-page figures redrawn as one (work/schemes/<first>.yaml: `continues: <second>`).
CONTINUED = {}
for _spec in (ROOT / "work" / "schemes").glob("*.yaml"):
    _cont = yaml.safe_load(_spec.read_text()).get("continues")
    if _cont:
        CONTINUED[_cont] = _spec.stem
TOC_ENTRIES = read_json(SITE / "content" / "toc.json", [])

# How each restored image was made (figures/images/map.yaml): "cleanup" = contrast/sharpening only, nothing redrawn.
RESTORE_METHOD = {r["figure"]: r.get("method", "upscale")
                  for r in read_yaml(ROOT / "figures" / "images" / "map.yaml", []) if r.get("figure")}


def as_list(value) -> list:
    """A spec's data lines: a list, or a single line written as a plain string (one line, not one per character)."""
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def build_scheme(path: Path, chapter: str, known: set[str], ref_scope: int, cpd_scope, multi_scope: bool) -> dict:
    """Scheme spec → site data: each molecule node rendered as an SVG (same style and scale as the structure
    cards) with its PubChem status, text and arrow cells as HTML."""
    from render_structures import render_generic, render_mol
    from scheme_check import check
    from scheme_preview import node_mol

    spec = yaml.safe_load(path.read_text())
    status = check(path)
    fmt = lambda t: inline(escape_block(t), chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope,
                           multi_scope=multi_scope) if t else ""
    nodes = {}
    for key, n in (spec.get("nodes") or {}).items():
        node = {"number": n.get("number") or "", "name_en": fmt(n.get("name_en")), "name_de": fmt(n.get("name_de")),
                "data_en": [fmt(d) for d in as_list(n.get("data_en"))], "text_en": fmt(n.get("text_en")),
                "text_de": fmt(n.get("text_de"))}
        for lang in ("en", "de"):  # callout text beside a class (structure–activity summaries), line by line
            lines = as_list(n.get(f"callout_{lang}"))
            if lines:
                node[f"callout_{lang}"] = [{"bullet": str(l).startswith("- "), "html": fmt(str(l)[2:] if str(l).startswith("- ") else str(l))}
                                           for l in lines]
        if n.get("callout_side"):
            node["callout_side"] = n["callout_side"]
        for k in ("role", "arrow"):  # class maps: the parent structure; arrow direction from/to it
            if n.get(k):
                node[k] = n[k]
        if n.get("arrow_label_en"):
            node["arrow_label_en"] = fmt(n["arrow_label_en"])
        if n.get("chapter"):  # class maps: "Chapter 7.1" links to that section
            entry = next((e for e in TOC_ENTRIES if e["id"] == str(n["chapter"])), None)
            node["chapter"] = str(n["chapter"])
            node["chapter_href"] = f"/chapter/{entry['unit']}#s-{entry['id']}" if entry and entry.get("available") else None
        if n.get("image"):  # a drawing cut from the restored page as an ink mask (visual table of contents)
            src = ROOT / n["image"]
            (SITE / "public" / "toc").mkdir(parents=True, exist_ok=True)
            shutil.copy(src, SITE / "public" / "toc" / src.name)
            with Image.open(src) as im:
                node["image"] = {"src": f"/toc/{src.name}", "width": im.width, "height": im.height}
        if n.get("of"):
            node["of"] = n["of"]
        for lang in ("en", "de"):  # chapter cards: the class under the chapter title ("Heteroaromatics")
            if n.get(f"subtitle_{lang}"):
                node[f"subtitle_{lang}"] = fmt(n[f"subtitle_{lang}"])
        if n.get("smiles"):
            svg_name = f"scheme-{spec['id']}-{key}.svg"
            if any(n.get(k) for k in ("rgroups", "locants", "attach", "highlight", "show_h", "dashed",
                                      "repeat", "box", "arc", "under", "coords", "horizontal",
                                      "circle", "axis", "inner_circle", "kekule", "lone_pairs", "clash",
                                      "lobes", "wavy", "decor")):
                render_generic(n, ROOT / "figures" / "structures" / svg_name)  # R groups, ring numbers, floating bond
            else:
                render_mol(node_mol(n), ROOT / "figures" / "structures" / svg_name)
            shutil.copy(ROOT / "figures" / "structures" / svg_name, SITE / "public" / "structures" / svg_name)
            node.update(svg=f"/structures/{svg_name}", **status.get(key, {}))
        nodes[key] = node
    grid = []
    for row in spec.get("grid") or []:
        cells = []
        for c in row:
            if isinstance(c, dict) and c.get("node"):
                cells.append({"node": c["node"], "span": c.get("span", 1), "rows": c.get("rows", 1)})
            elif isinstance(c, dict):
                cells.append({"arrow": c.get("arrow"), "span": c.get("span", 1), "rows": c.get("rows", 1),
                              "style": c.get("style", "line"), "heads": c.get("heads"), "label_side": c.get("label_side"),
                              **{k: fmt(c.get(k)) for k in ("label_en", "label_below_en", "label_de", "label_below_de")}})
            else:
                cells.append({"node": c, "span": 1, "rows": 1} if c else None)
        grid.append(cells)
    generic = spec.get("kind") == "generic"
    # A scheme read twice blind (and agreeing) is no longer a pilot; generic figures carry their own note.
    toc = None
    if spec.get("kind") == "toc":  # visual table of contents: a head (flow + notes) and groups of chapter cards
        head = [[{**item, **{k: fmt(item.get(k)) for k in ("label_en", "label_de") if item.get(k)}} for item in row]
                for row in spec.get("head") or []]
        toc = {"head": head, "groups": spec.get("groups") or []}
    # callout layouts, and schemes marked `wide: true` (too broad for the reading column), use the margin column too
    wide = bool(spec.get("wide")) or any(n.get("callout_en") for n in nodes.values())
    return {"nodes": nodes, "grid": grid, "toc": toc, "classmap": spec.get("kind") == "classmap", "wide": wide,
            **({"scale": spec["scale"]} if spec.get("scale") else {}), **({"tight": True} if spec.get("tight") else {}), "pilot": not generic and not spec.get("read"),
            "checked": not generic and "two blind" in str(spec.get("read", "")), "generic": generic}


def escape_block(text: str) -> str:
    """Keep a one-line label inline: a leading "-", ">", "#" or "1." is text, not Markdown block syntax."""
    text = re.sub(r"^(\s*)([-+*](?=\s|$)|>|#{1,6}(?=\s|$))", r"\1\\\2", text)
    return re.sub(r"^(\s*\d+)([.)])(?=\s)", r"\1\\\2", text)


def heading_anchor(title_de: str, number: str | None, toc: list[dict]) -> str | None:
    """Anchor ids come from the TOC so the contents page can link to any heading,
    numbered ('s-2.1') or not ('s-ex-naturstoffe')."""
    if number:
        return f"s-{number}"
    norm = lambda s: re.sub(r"[*_]|^Exkurs:\s*", "", s).strip().lower()
    # Exact title first: "Exkurs: Anorektika" must not take the anchor of section 6.3.8 "Anorektika".
    for entry in toc:
        if entry["de"].strip() == title_de.strip():
            return f"s-{entry['id']}"
    for entry in toc:
        if norm(entry["de"]) == norm(title_de):
            return f"s-{entry['id']}"
    return None


def main(slug: str) -> None:
    units = yaml.safe_load((ROOT / "source" / "units.yaml").read_text())
    slug = slug.lstrip("0") or slug
    unit = next(u for u in units if u["slug"] == slug)
    chapter = unit["dir"]
    toc = yaml.safe_load((ROOT / "source" / "toc.yaml").read_text())
    work = ROOT / "work" / chapter
    de_blocks = blocks_of(TN.sub("", (work / "de.md").read_text()))
    en_blocks = blocks_of((work / "en.md").read_text())
    compounds_all = read_yaml(ROOT / "figures" / "compounds.yaml", {})  # chemistry books only
    # Verified links for the literature lists (scripts/link_references.py): (list number, entry) → row.
    links_path = work / "references.yaml"
    ref_links = {(r["list"], r["n"]): r for r in (yaml.safe_load(links_path.read_text()) or [])
                 if r.get("url")} if links_path.exists() else {}
    multi_scope = unit.get("compound_scopes") == "per-section"
    known = {k for k in compounds_all if k.startswith(f"{chapter}-")}  # keys, as compound() builds them

    # Align: drop standalone page anchors but remember them as page state.
    def split(blocks):
        """Pair each block with the printed page it starts on. Page breaks can be
        standalone anchors or sit inside a paragraph (text running over the break)."""
        out, page = [], None
        for b in blocks:
            m = PAGE_ONLY.match(b)
            if m:
                page = page_value(m.group(1))
                continue
            # Anchors stacked on top of a block (no blank line after them) are page state too,
            # otherwise they hide what the block starts with (e.g. "[53]" of a reference list).
            lines = b.split("\n")
            while len(lines) > 1 and PAGE_ONLY.match(lines[0]):
                page = page_value(PAGE_ONLY.match(lines.pop(0)).group(1))
            b = "\n".join(lines)
            out.append((page, b))
            inline_pages = INLINE_PAGE.findall(b)
            if inline_pages:
                page = page_value(inline_pages[-1])
        return out

    de, en = split(de_blocks), split(en_blocks)
    if len(de) != len(en):
        sys.exit(f"paragraph mismatch DE {len(de)} / EN {len(en)} — run check_invariants.py")

    blocks, tn_counter, in_refs, ref_scope = [], 0, False, 0
    fn_scopes: dict[str, tuple] = {}  # footnote id → (ref_scope, cpd_scope) where it is called
    figure_of: dict[str, str] = {}    # compound key → first figure showing it (printed original or redrawn)
    tables_on_page: dict[int, int] = {}  # the k-th table starting on page P has the crop pPPPP-tk
    cpd_scope: str | None = None
    (SITE / "public" / "structures").mkdir(parents=True, exist_ok=True)
    (SITE / "public" / "figures").mkdir(parents=True, exist_ok=True)

    for (page, de_raw), (_, en_raw) in zip(de, en):
        tns = []

        def take_tn(m):
            nonlocal tn_counter
            tn_counter += 1
            tns.append({"n": tn_counter, "html": inline(m.group(1), chapter, known, ref_scope=ref_scope,
                                                         cpd_scope=cpd_scope, multi_scope=multi_scope)})
            return f'<sup class="tn-ref"><a href="#tn-{tn_counter}" id="tnref-{tn_counter}">{tn_counter}</a></sup>'

        en_text = TN.sub(take_tn, en_raw)
        block = {"page": page, "tns": tns}

        heading = re.match(r"^(#+)\s+(.*)$", en_text)
        fig = FIG.match(TN.sub("", en_raw).strip())  # notes may follow a placeholder
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            number = re.match(r"^([\d.]+)\s+(.*)$", title)
            if in_refs and title.strip() != "References":
                ref_scope += 1  # the previous list is complete; citations now point to the next one
            in_refs = title.strip() == "References"
            de_title = re.sub(r"^#+\s+([\d.]+\s+)?", "", de_raw)
            num_id = number.group(1).rstrip(".") if number else None
            if multi_scope and num_id and (level == 1 or re.fullmatch(r"\d+\.\d+", num_id)):
                cpd_scope = num_id
            block.update(type="heading", level=level, number=num_id,
                         anchor=heading_anchor(de_title, num_id, toc),
                         en=inline(number.group(2) if number else title, chapter, known, ref_scope=ref_scope,
                                   cpd_scope=cpd_scope, multi_scope=multi_scope),
                         de=inline(de_title, chapter, known, ref_scope=ref_scope,
                                   cpd_scope=cpd_scope, multi_scope=multi_scope))
        elif en_text.strip().startswith("{{omitted:"):
            # A synthesis passage left out of this edition (CONVENTIONS.md, "Omitted passages").
            om = re.match(r'\{\{omitted:\s*(\w+)\s*\|\s*pages:\s*([^|]+?)\s*\|\s*note:\s*"(.*?)"\s*\}\}', en_text.strip())
            pages_, note = (om.group(2), om.group(3)) if om else ("", "")
            block.update(type="paragraph",
                         en=f'<em class="omitted">Passage on chemical synthesis not included in this edition (pp. {pages_}). {note}.</em>',
                         de=f'<em class="omitted">Syntheseteil in dieser Ausgabe nicht enthalten (S. {pages_}).</em>')
        elif en_text.strip() == "{{toc}}":
            # The front matter's printed table of contents is the site's Contents page.
            block.update(type="paragraph", en='<em>The table of contents is on the <a href="/">Contents</a> page.</em>',
                         de='<em>Das Inhaltsverzeichnis steht auf der Seite <a href="/">Contents</a>.</em>')
        elif fig:
            f = parse_fig(fig.group(1))
            de_f = parse_fig(FIG.match(de_raw).group(1))
            tn_html = "".join(re.findall(r'<sup class="tn-ref">.*?</sup>', en_text))
            # Some captions repeat their own label ("**Fig. 16.** Comparison …"): the label is shown once.
            lab = re.sub(r"\W", "", f.get("label", "")).lower()
            for fig_ in (f, de_f):
                lm = re.match(r"^\s*\*\*([^*]+)\*\*\s*", fig_.get("caption", ""))
                if lab and lm and re.sub(r"\W", "", lm.group(1)).lower() in (lab, re.sub(r"^fig", "abb", lab)):
                    fig_["caption"] = fig_["caption"][lm.end():]
            block.update(type="figure", id=f["id"], kind=f.get("kind"), label=f.get("label", ""),
                         caption_en=inline(f.get("caption", ""), chapter, known, ref_scope=ref_scope,
                                           cpd_scope=cpd_scope, multi_scope=multi_scope),
                         caption_de=inline(de_f.get("caption", ""), chapter, known, ref_scope=ref_scope,
                                           cpd_scope=cpd_scope, multi_scope=multi_scope),
                         tn_marker=tn_html.strip())
            # A figure printed across two pages is cropped as two halves; the second has no caption of its own.
            prev = blocks[-1] if blocks else None
            if (not f.get("caption") and prev and prev["type"] == "figure" and prev["label"]
                    and prev["kind"] == f.get("kind") and block["label"] in ("", prev["label"])
                    and int(f["id"][1:5]) == int(prev["id"][1:5]) + 1):
                block["label"] = prev["label"].rstrip(".") + " (continued)"
            ready ={"verified", "corrected", "read-twice"}
            if multi_scope and cpd_scope:
                fig_keys = [f"{chapter}-{cpd_scope}-{c}" for c in f.get("compounds", [])]
            else:
                fig_keys = [f"{chapter}-{c}" for c in f.get("compounds", [])]
            scheme_path = ROOT / "work" / "schemes" / f"{f['id']}.yaml"
            if scheme_path.exists():
                # A scheme redrawn from a spec (scriptorium brief SCHEMES): molecules + arrows on the printed grid.
                block["scheme"] = build_scheme(scheme_path, chapter, known, ref_scope, cpd_scope, multi_scope)
                block["labels_en"] = [inline(escape_block(x), chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope) for x in f.get("labels", [])]

            def drawable(k):
                return (compounds_all.get(k, {}).get("status") in ready
                        and f["id"] not in compounds_all.get(k, {}).get("keep_original_in", []))
            # A figure mixing generic drawings (R, X …) with real compounds: the real ones get cards,
            # the printed original stays in view for the generic part.
            as_structures = f.get("kind") in ("structure", "table-image")  # a table printed as an image of structures
            partial = (as_structures and any(drawable(k) for k in fig_keys)
                       and all(drawable(k) or compounds_all.get(k, {}).get("status") == "generic" for k in fig_keys)
                       and not all(drawable(k) for k in fig_keys))
            if block.get("scheme"):
                pass
            elif as_structures and fig_keys and (all(drawable(k) for k in fig_keys) or partial):
                names_en = caption_by_compound(f.get("caption", ""), f.get("compounds", []))
                names_de = caption_by_compound(de_f.get("caption", ""), f.get("compounds", []))
                # Names printed inside the figure ("14: phenelzine" labels) when the caption doesn't give them.
                for names, fig_ in ((names_en, f), (names_de, de_f)):
                    for label in fig_.get("labels", []):
                        lm = re.match(r"^(\w+):\s*(.+)$", label)
                        if lm and lm.group(1) in f.get("compounds", []) and not names.get(lm.group(1)):
                            names[lm.group(1)] = [lm.group(2)]
                block["compounds"] = []
                groups_file = ROOT / "figures" / "groups" / f"{f['id']}.yaml"
                if groups_file.exists():
                    # Columns of a table printed as an image: cards grouped under their column heading.
                    block["groups"] = yaml.safe_load(groups_file.read_text())
                if partial:
                    block["partial"] = True
                    block["labels_en"] = [inline(escape_block(x), chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope) for x in f.get("labels", [])]
                for c in f.get("compounds", []):
                    key = f"{chapter}-{cpd_scope}-{c}" if multi_scope and cpd_scope else f"{chapter}-{c}"
                    if not drawable(key):
                        continue
                    info = compounds_all[key]
                    shutil.copy(ROOT / "figures" / "structures" / f"{key}.svg", SITE / "public" / "structures" / f"{key}.svg")
                    block["compounds"].append({
                        "key": key, "number": "" if c.startswith("u") else c, "svg": f"/structures/{key}.svg",
                        "names_en": [inline(n, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope) for n in names_en.get(c, [])],
                        "names_de": [inline(n, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope) for n in names_de.get(c, [])],
                        "smiles": info["render_smiles"], "cid": info.get("cid"), "status": info["status"],
                    })
                    card = block["compounds"][-1]
                    if not card["names_en"]:
                        # No name printed with the drawing: the book's own name from its text (confirmed by PubChem
                        # for this structure), else PubChem's most readable name — marked as such on the card.
                        if info.get("name_book"):
                            card["names_en"] = [html_escape(info["name_book"])]
                        elif info.get("pubchem_name"):
                            card["names_en"] = [html_escape(info["pubchem_name"])]
                            card["name_source"] = "pubchem"
            elif f.get("kind") == "chart" and (ROOT / "figures" / "charts" / f"{f['id']}.yaml").exists():
                block["chart"] = yaml.safe_load((ROOT / "figures" / "charts" / f"{f['id']}.yaml").read_text())
            else:
                # Not redrawn yet: the printed original is shown, with the English labels as a key.
                block["pending"] = f.get("kind") in ("structure", "scheme", "chart")
                # Labels are single lines of a drawing: "> 300mg" or "- Alkyl" is text, not a quote or a list.
                block["labels_en"] = [inline(escape_block(x), chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope) for x in f.get("labels", [])]
            translation = ROOT / "figures" / "translations" / f"{f['id']}.md"
            if translation.exists():
                # A printed document (e.g. Heffter's 1897 protocol) given as English text; the scan stays one click away.
                block["document_en"] = md.render(translation.read_text())
            restored = ROOT / "figures" / "restored" / f"{f['id']}.webp"
            if restored.exists() and block.get("document_en"):
                # A document given as English text: its cleaned German page stands in for the raw scan behind the toggle.
                shutil.copy(restored, SITE / "public" / "figures" / f"{f['id']}-restored.webp")
                with Image.open(restored) as im:
                    block["original_restored"] = {"src": f"/figures/{f['id']}-restored.webp", "width": im.width, "height": im.height}
            illustration = ROOT / "figures" / "illustrations" / f"{f['id']}.svg"
            if illustration.exists() and not (block.get("compounds") or block.get("chart") or block.get("scheme")):
                # A simple schematic redrawn by hand as SVG, in the page's ink colours.
                (SITE / "public" / "illustrations").mkdir(parents=True, exist_ok=True)
                shutil.copy(illustration, SITE / "public" / "illustrations" / illustration.name)
                block["illustration"] = f"/illustrations/{illustration.name}"
                block.pop("pending", None)  # drawn now: no "printed original" note under it
            elif restored.exists() and (block.get("partial") or not (block.get("compounds") or block.get("chart") or block.get("scheme") or block.get("document_en"))):
                # Cleaned and upscaled from the printed page (scripts/restored_images.py); the scan stays one click away.
                shutil.copy(restored, SITE / "public" / "figures" / f"{f['id']}-restored.webp")
                with Image.open(restored) as im:
                    block["restored"] = {"src": f"/figures/{f['id']}-restored.webp", "width": im.width, "height": im.height,
                                         "method": RESTORE_METHOD.get(f["id"], "upscale")}
            original = ROOT / "figures" / chapter / f"{f['id']}_orig.png"
            if original.exists():
                Image.open(original).save(SITE / "public" / "figures" / f"{f['id']}.webp", quality=82)
                with Image.open(original) as im:
                    block["original"] = {"src": f"/figures/{f['id']}.webp", "width": im.width, "height": im.height}
        elif in_refs and re.match(r"^\[\d+\]", en_text):
            refs = []
            for line in en_text.split("\n"):
                m = re.match(r"^\[(\d+)\]\s*(.*)$", line)
                if m:
                    ref = {"n": int(m.group(1)), "html": inline(m.group(2), chapter, known, in_refs=True,
                                                                cpd_scope=cpd_scope, multi_scope=multi_scope)}
                    link = ref_links.get((ref_scope + 1, ref["n"]))
                    if link:
                        ref.update(href=link["url"], link=link["status"])
                    refs.append(ref)
            if blocks and blocks[-1]["type"] == "references":
                # A page break inside the list splits it into blocks — it's still one list.
                blocks[-1]["refs"] += refs
                blocks[-1]["tns"] += block["tns"]  # notes on entries of the continued list
                continue
            block.update(type="references", scope=ref_scope, refs=refs)
        elif re.match(r"^\[\^([\w-]+)\]:", en_text):
            m = re.match(r"^\[\^([\w-]+)\]:\s*(.*)$", en_text, re.S)
            dm = re.match(r"^\[\^([\w-]+)\]:\s*(.*)$", de_raw, re.S)
            # Footnotes are collected at the end of the unit; link them in the scope of their call site.
            fn_ref, fn_cpd = fn_scopes.get(m.group(1), (ref_scope, cpd_scope))
            block.update(type="footnote", id=m.group(1),
                         en=inline(m.group(2), chapter, known, ref_scope=fn_ref, cpd_scope=fn_cpd, multi_scope=multi_scope),
                         de=inline(dm.group(2), chapter, known, ref_scope=fn_ref, cpd_scope=fn_cpd, multi_scope=multi_scope))
        elif re.fullmatch(r"(<!--.*?-->\s*)+", en_text.strip(), re.S):
            # A transcriber's note standing on its own (how a table was laid out in print): for the
            # proofreader, not the reader — the ones that matter to the reader are TNs as well.
            continue
        elif en_text.startswith("|"):
            block.update(type="table",
                         en=inline(en_text, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope),
                         de=inline(de_raw, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope))
            if isinstance(page, int):
                tables_on_page[page] = tables_on_page.get(page, 0) + 1
                table_id = f"p{page:04d}-t{tables_on_page[page]}"
                original = ROOT / "figures" / chapter / f"{table_id}_orig.png"
                if original.exists():
                    Image.open(original).save(SITE / "public" / "figures" / f"{table_id}.webp", quality=82)
                    with Image.open(original) as im:
                        block["original"] = {"src": f"/figures/{table_id}.webp", "width": im.width, "height": im.height}
        else:
            block.update(type="paragraph",
                         en=inline(en_text, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope),
                         de=inline(de_raw, chapter, known, ref_scope=ref_scope, cpd_scope=cpd_scope, multi_scope=multi_scope))
        block["_scope"] = cpd_scope  # for linking numbers after the loop (removed before writing)
        for fn_id in re.findall(r"\[\^([\w-]+)\](?!:)", en_raw):
            fn_scopes.setdefault(fn_id, (ref_scope, cpd_scope))
        if block.get("type") == "figure":
            for c in parse_fig(fig.group(1)).get("compounds", []):
                key = f"{chapter}-{cpd_scope}-{c}" if multi_scope and cpd_scope else f"{chapter}-{c}"
                figure_of.setdefault(key, block["id"])
            if block.get("pending") and not block.get("original"):
                # A structure drawn inside a table (header row) has no crop of its own; the table's
                # "printed original" shows it, so an empty figure with only a label key is left out.
                if blocks:
                    blocks[-1]["tns"] += block["tns"]
                continue
        blocks.append(block)

    # A figure printed over two pages and redrawn as one (spec `continues: <second half>`): the second half
    # points back to the redrawn figure and keeps its scan behind "Compare with printed original".
    label_of = {b["id"]: b.get("label") or "the figure" for b in blocks if b["type"] == "figure"}
    for b in blocks:
        if b["type"] == "figure" and b["id"] in CONTINUED and not b.get("scheme"):
            main = CONTINUED[b["id"]]
            b["merged_into"] = {"id": main, "label": re.sub(r"<[^>]+>", "", label_of.get(main, "the figure")).rstrip(".")}

    # A compound number without a redrawn card links to the figure that shows the printed original,
    # or to nothing if no figure shows it.
    cards = {c["key"] for b in blocks if b["type"] == "figure" for c in (b.get("compounds") or [])}

    def relink(html: str) -> str:
        def one(m):
            key = m.group(2)
            if key in cards:
                return m.group(0)
            if key in figure_of:
                return f'{m.group(1)}#{figure_of[key]}{m.group(3)}{m.group(4)}</a>'
            return f'<span class="cpd">{m.group(4)}</span>'
        return re.sub(r'(<a class="cpd" href=")#cpd-([^"]+)(" data-cpd="[^"]+">)([^<]*)</a>', one, html)

    def walk(x):
        if isinstance(x, str):
            return relink(x) if "cpd-" in x else x
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x

    blocks = walk(blocks)

    # Numbers of compounds that were never read as structures (e.g. only in a reaction scheme) are still
    # linked when a figure shows them.
    def link_bare(html: str, scope: str | None) -> str:
        def one(m):
            key = f"{chapter}-{scope}-{m.group(1)}" if multi_scope and scope else f"{chapter}-{m.group(1)}"
            if key in figure_of:
                return f'<a class="cpd" href="#{figure_of[key]}" data-cpd="{key}">{m.group(1)}</a>'
            return m.group(0)
        return re.sub(r"<strong>(\d+[a-z]?)</strong>", one, html)

    for b in blocks:
        scope = b.pop("_scope", None)
        if b["type"] == "references":
            continue
        for k in ("en", "de", "caption_en", "caption_de"):
            if isinstance(b.get(k), str):
                b[k] = link_bare(b[k], scope)
        for t in b.get("tns", []):
            t["html"] = link_bare(t["html"], scope)

    # A table caption paragraph directly before a table belongs to it.
    merged = []
    for b in blocks:
        if b["type"] == "table" and merged and merged[-1]["type"] == "paragraph" and merged[-1]["en"].startswith("<strong>Table"):
            cap = merged.pop()
            b.update(caption_en=cap["en"], caption_de=cap["de"], tns=cap["tns"] + b["tns"])
        merged.append(b)

    for b in merged:
        if b.get("original_restored"):
            b["original"] = b.pop("original_restored")
    out = {"slug": slug, "title_de": unit.get("title_de", ""), "title_en": unit.get("title_en", ""),
           "first": unit["first"], "last": unit["last"], "blocks": merged}
    (SITE / "content" / "units").mkdir(parents=True, exist_ok=True)
    (SITE / "content" / "units" / f"{slug}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    write_toc(toc, units)
    kinds = {}
    for b in merged:
        kinds[b["type"]] = kinds.get(b["type"], 0) + 1
    print(f"{chapter}: {len(merged)} blocks {kinds}, {tn_counter} sidenotes")


def unit_of(page: str | int, units: list[dict]) -> dict | None:
    """The unit a printed page belongs to (units split around an excursus use `ranges`)."""
    if not str(page).isdigit():
        # Front matter: roman pages listed per unit.
        return next((u for u in units if str(page) in (u.get("pages") or [])), None)
    p = int(page)
    for u in units:
        if any(a <= p <= b for a, b in u.get("ranges") or [[u["first"], u["last"]]]):
            return u
    return None


def write_toc(toc: list[dict], units: list[dict]) -> None:
    """toc.json for the contents page: each entry knows its reading unit and
    whether that unit has been built yet."""
    built = {p.stem for p in (SITE / "content" / "units").glob("*.json")}
    titles_en = yaml.safe_load((ROOT / "source" / "toc_en.yaml").read_text())
    entries = []
    for e in toc:
        u = unit_of(e["page"], units)
        entries.append({**e, "en": titles_en.get(e["id"]), "page": str(e["page"]), "unit": u["slug"] if u else None,
                        "available": bool(u and u["slug"] in built)})
    (SITE / "content" / "toc.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
