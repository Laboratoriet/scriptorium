"""Compare a German and an English Markdown file for things that must survive translation.

Usage: scriptorium run check_invariants work/ch02/de.md work/ch02/en.md

Checked, as multisets (count matters):
  compound numbers **n**, reference markers [n], figure placeholders,
  page anchors, headings' section numbers, sub/superscript contents,
  numeric tokens (digits incl. decimals, ranges, units stuck to them).
Checked per paragraph (paragraphs must line up 1:1):
  English/German length ratio — outliers often mean dropped or added content.

Exit code 1 if any hard invariant fails. Length outliers are warnings.
"""
import re
import sys
from collections import Counter
from pathlib import Path

HARD_CHECKS = {
    "compound numbers": r"\*\*(\d+[a-z]?)\*\*",
    "reference markers": r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]",
    "figure placeholders": r"\{\{fig:([^|}\s]+)",
    "page anchors": r"<!-- p\.(\d+) -->",
    "section numbers": r"^#+\s+([\d.]+)",
    "sub/superscripts": r"<su[bp]>(.*?)</su[bp]>",
}
# Digits outside the constructs above. German and English both use '.' for
# decimals in this book; a mismatch here needs a human look, not auto-fixing.
NUMBER = r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])"

RATIO_LOW, RATIO_HIGH = 0.75, 1.45


def strip_checked_constructs(text: str) -> str:
    for pattern in HARD_CHECKS.values():
        text = re.sub(pattern, " ", text, flags=re.M)
    return re.sub(r"\{\{fig:[^}]*\}\}", " ", text)


def paragraphs(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text)]
    return [b for b in blocks if b and not re.fullmatch(r"<!-- p\.\d+ -->", b)]


def diff(name: str, de: Counter, en: Counter) -> list[str]:
    missing = de - en
    extra = en - de
    lines = []
    if missing:
        lines.append(f"  missing in EN: {dict(missing)}")
    if extra:
        lines.append(f"  extra in EN:   {dict(extra)}")
    return [f"✗ {name}"] + lines if lines else []


def exceptions_path(en_path: Path) -> Path:
    """Parts of a split unit have their own file (p3.en.md → p3.exceptions.yaml).
    A whole unit's en.md has no ".en.md" suffix to replace, so it always uses invariant_exceptions.yaml."""
    part_file = en_path.with_name(en_path.name.replace(".en.md", ".exceptions.yaml"))
    is_part = en_path.name.endswith(".en.md")
    return part_file if is_part and part_file.exists() else en_path.parent / "invariant_exceptions.yaml"


def main(de_path: Path, en_path: Path) -> int:
    # Translator's notes are commentary, not translation — exclude them from all checks.
    strip_tn = lambda s: re.sub(r"\s*<!-- TN:.*?-->", "", s, flags=re.S)
    de, en = strip_tn(de_path.read_text()), strip_tn(en_path.read_text())
    failures = []

    # Deliberate English corrections (e.g. a misprinted compound number, fixed with a TN) are
    # mapped back to the printed German form before checking — each must occur exactly once.
    exceptions_file = exceptions_path(en_path)
    if exceptions_file.exists():
        import yaml
        for sub in (yaml.safe_load(exceptions_file.read_text()) or {}).get("en_substitutions") or []:
            if en.count(sub["en"]) != 1:
                failures.append(f"✗ en_substitution not found exactly once: {sub['en'][:60]!r}")
                continue
            en = en.replace(sub["en"], sub["de"])
            print(f"  (accepted change: {sub['reason'][:80]})")

    for name, pattern in HARD_CHECKS.items():
        failures += diff(name, Counter(re.findall(pattern, de, re.M)), Counter(re.findall(pattern, en, re.M)))

    # Decades: German "1940er" (Jahre) counts as 1940, like English "1940s" below.
    de_plain = re.sub(r"\b(1[5-9]\d0|20\d0)er", r"\1", strip_checked_constructs(de))
    # English ordinals also occur in the German file (verbatim references: "2nd ed.").
    de_plain = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", de_plain)
    de_nums = Counter(re.findall(NUMBER, de_plain))
    # English ordinals ("20th") correspond to German "20." — count them as the bare number.
    en_plain = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", strip_checked_constructs(en))
    # Decades: English "the 1960s" corresponds to German "1960er"/"1960".
    en_plain = re.sub(r"\b(1[5-9]\d0|20\d0)(?:s\b|er)", r"\1", en_plain)  # "er": verbatim German references
    en_nums = Counter(re.findall(NUMBER, en_plain))
    exceptions_file = exceptions_path(en_path)
    if exceptions_file.exists():
        import yaml
        accepted = yaml.safe_load(exceptions_file.read_text()) or {}
        # A reason can be a list: one entry per occurrence of that number.
        def each(section):
            for number, reasons in (accepted.get(section) or {}).items():
                for reason in reasons if isinstance(reasons, list) else [reasons]:
                    yield number, reason
        for number, reason in each("numbers_missing_in_en"):
            if de_nums[number] > en_nums[number]:
                de_nums[number] -= 1
                # A German decimal comma becomes an English decimal point.
                if "," in number and en_nums[number.replace(",", ".")] > de_nums[number.replace(",", ".")]:
                    en_nums[number.replace(",", ".")] -= 1
                print(f"  (accepted: {number} — {reason[:80]})")
        # Numbers the English has to spell out where German glues them to a word ("100mal" → "100-fold").
        for number, reason in each("numbers_extra_in_en"):
            if en_nums[number] > de_nums[number]:
                en_nums[number] -= 1
                print(f"  (accepted extra: {number} — {reason[:80]})")
    failures += diff("numbers", de_nums, en_nums)

    de_paras, en_paras = paragraphs(de), paragraphs(en)
    warnings = []
    if len(de_paras) != len(en_paras):
        failures.append(f"✗ paragraph count: DE {len(de_paras)} vs EN {len(en_paras)}")
    else:
        for i, (d, e) in enumerate(zip(de_paras, en_paras), 1):
            if len(d) < 80:
                continue
            ratio = len(e) / len(d)
            if not RATIO_LOW <= ratio <= RATIO_HIGH:
                warnings.append(f"⚠ paragraph {i}: length ratio {ratio:.2f} — «{d[:70]}…»")

    print("\n".join(failures) if failures else "✓ all hard invariants match")
    if warnings:
        print("\n".join(warnings))
    print(f"paragraphs: {len(de_paras)} DE / {len(en_paras)} EN")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
