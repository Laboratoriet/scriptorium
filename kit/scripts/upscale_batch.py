"""Upscale scans through ImageRouter (image edit models) and check every result against the original crop.

Usage: scriptorium run upscale_batch --model openai/gpt-image-2 p0617-1 p0965-1 …
       scriptorium run upscale_batch --model google/nano-banana-2 --all     (everything in figures/upscale_todo)

The key is read from .env (IMAGEROUTER_API_KEY) and never printed. Each crop is padded with white to the model's
nearest supported aspect ratio (so nothing is stretched or cut), sent with a strict "restore, don't change" prompt,
and the padding is trimmed off the result. Results land in figures/images/api/<model>/<figure>.png — never on the
site directly. Checks, written to figures/images/api/<model>/report.md:
- OCR (source language + English) of crop and result: words that appear or disappear flag the figure;
- line-art diff: result scaled to the crop, ink in one that has no ink nearby in the other (invented or lost lines).
Generative models invent text; a flagged result is held until checked by eye.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from bookroot import ROOT  # the book project (book.yaml), not the kit
TODO = ROOT / "figures" / "upscale_todo"
API = "https://api.imagerouter.io/v1/openai/images/edits"

PROMPT = (
    "Restore this scanned page figure from a printed chemistry book. Reproduce it EXACTLY: same layout, same "
    "drawing, every line, atom label, bond, arrow, number and word unchanged and in the same place. Do not translate "
    "(German text stays German), do not add, remove, correct or redraw anything, do not add colour. Keep every grey "
    "tone exactly: shapes filled dark grey stay filled dark grey (with their light text inside), grey bands and "
    "shaded backgrounds stay grey — never turn a filled shape into an outline. Only remove scan "
    "noise, paper texture and blur, and render lines and text crisp and sharp on a clean background, like the "
    "original print. The white margins are padding: keep them plain white."
)

SIZES = {
    "openai/gpt-image-2": ["1024x1024", "1536x1024", "1024x1536", "2560x1440", "3840x2160"],
    # 2K tier only (larger sizes cost up to 3×, and ~2500 px is plenty for a figure shown at ≤ 576 px)
    "google/nano-banana-2": ["2048x2048", "1696x2528", "2528x1696", "1792x2400", "2400x1792", "1856x2304",
                             "2304x1856", "1536x2752", "2752x1536", "3168x1344", "2048x512", "1024x4096"],
}


def key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("IMAGEROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("IMAGEROUTER_API_KEY missing in .env")


def pick_size(model: str, w: int, h: int) -> tuple[int, int]:
    """Supported size with the nearest aspect ratio; among near-equal ones, the largest."""
    sizes = [tuple(map(int, s.split("x"))) for s in SIZES[model]]
    best = min(abs(np.log((sw / sh) / (w / h))) for sw, sh in sizes)
    return max((s for s in sizes if abs(np.log((s[0] / s[1]) / (w / h))) <= best + 0.03), key=lambda s: s[0] * s[1])


def pad(crop: Image.Image, size: tuple[int, int]) -> tuple[Image.Image, tuple[float, float, float, float]]:
    """White-pad the crop to the target aspect; return it and the crop's box as fractions of the padded image."""
    w, h = crop.size
    tw, th = size
    if tw / th > w / h:
        pw, ph = round(h * tw / th), h
    else:
        pw, ph = w, round(w * th / tw)
    canvas = Image.new("RGB", (pw, ph), "white")
    x, y = (pw - w) // 2, (ph - h) // 2
    canvas.paste(crop, (x, y))
    return canvas, (x / pw, y / ph, (x + w) / pw, (y + h) / ph)


def call(model: str, image: Image.Image, size: tuple[int, int]) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.png"
        im = image.copy()
        im.thumbnail((2048, 2048), Image.LANCZOS)
        im.save(src)
        out = subprocess.run(
            ["curl", "-sS", "--max-time", "600", API, "-H", f"Authorization: Bearer {key()}",
             "-F", f"model={model}", "-F", f"prompt={PROMPT}", "-F", f"size={size[0]}x{size[1]}",
             "-F", "response_format=b64_json", "-F", "quality=high", "-F", f"image=@{src}"],
            capture_output=True, text=True)
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"no JSON: {out.stdout[:300]} {out.stderr[:300]}")
    if "data" not in data:
        raise RuntimeError(json.dumps(data)[:400])
    item = data["data"][0]
    raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else urllib.request.urlopen(item["url"]).read()
    tmpf = Path(tempfile.mkstemp(suffix=".img")[1])
    tmpf.write_bytes(raw)
    return Image.open(tmpf).convert("RGB")


def ocr_words(im: Image.Image) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "o.png"
        g = im.convert("L")
        if g.width < 2000:
            g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
        g.save(p)
        text = subprocess.run(["tesseract", str(p), "-", "-l", "deu+eng", "--psm", "11"], capture_output=True, text=True).stdout
    return {w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{3,}", text)}


def ink(im: Image.Image, size: tuple[int, int]) -> np.ndarray:
    g = np.asarray(im.convert("L").resize(size, Image.LANCZOS), dtype=np.float32)
    bg = np.asarray(Image.fromarray(g.astype(np.uint8)).filter(ImageFilter.MedianFilter(31)), dtype=np.float32)
    return (bg - g) > 60  # darker than the local paper tone: lines and text, not shading


def near(mask: np.ndarray, r: int) -> np.ndarray:
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * r + 1))) > 0


def check(crop: Image.Image, result: Image.Image) -> dict:
    size = (min(crop.width, 1400), round(min(crop.width, 1400) * crop.height / crop.width))
    a, b = ink(crop, size), ink(result, size)
    extra = (b & ~near(a, 4)).sum() / max(1, b.sum())  # result ink far from any original ink
    lost = (a & ~near(b, 4)).sum() / max(1, a.sum())
    wa, wb = ocr_words(crop), ocr_words(result)
    return {"extra_ink": round(float(extra), 3), "lost_ink": round(float(lost), 3),
            "words_new": sorted(wb - wa), "words_gone": sorted(wa - wb)}


def grey(im: Image.Image) -> Image.Image:
    """The print is greyscale: drop any tint or invented colour, and set the paper to white (2nd–99.5th pct)."""
    g = np.asarray(im.convert("L"), dtype=np.float32)
    lo, hi = np.percentile(g, 0.5), np.percentile(g, 99.5)
    return Image.fromarray(np.clip((g - lo) / max(1, hi - lo) * 255, 0, 255).astype(np.uint8)).convert("RGB")


# Figures printed on a grey panel or with large shaded areas (picked by eye: an even page tint can't be told from a
# panel automatically) get tone-preserving levels only. One figure id per line in figures/upscale_panels.txt.
_PANELS = ROOT / "figures" / "upscale_panels.txt"
PANEL = {l.split("#")[0].strip() for l in _PANELS.read_text().splitlines()} - {""} if _PANELS.exists() else set()


def classic(crop: Image.Image, panel: bool = False) -> Image.Image:
    """Non-generative clean-up (can't invent anything): flatten the paper tone, levels, 2× Lanczos, sharpen.
    Figures printed on a grey panel keep it: they get global levels only (flattening would read the panel as paper)."""
    g = crop.convert("L")
    if panel:
        im = grey(g.convert("RGB")).resize((g.width * 2, g.height * 2), Image.LANCZOS)
        return im.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
    bg = g.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(25))  # paper tone without the ink
    flat = np.asarray(g, dtype=np.float32) / np.maximum(1, np.asarray(bg, dtype=np.float32)) * 255
    im = grey(Image.fromarray(np.clip(flat, 0, 255).astype(np.uint8)))
    # Show-through from the back of the page is faint grey on the flattened paper: fade the lightest tones to white
    # (above ~88 % of white), keeping ink and the printed grey fills (well below that) as they are.
    a = np.asarray(im.convert("L"), dtype=np.float32)
    knee = 225.0
    a = np.where(a > knee, 255.0, a)  # hard knee: only near-white changes
    im = Image.fromarray(a.astype(np.uint8)).convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))


def run_agreement(a: Image.Image, b: Image.Image) -> tuple[float, Image.Image]:
    """Two independent runs of the same figure: line-art in one with nothing within 2 px in the other.
    Returns the share and an overlay (red = only run 1, blue = only run 2) for the eye check."""
    size = (1400, round(1400 * a.height / a.width))
    ma, mb = ink(a, size), ink(b, size)
    only_a, only_b = ma & ~near(mb, 2), mb & ~near(ma, 2)
    share = (only_a.sum() + only_b.sum()) / max(1, ma.sum() + mb.sum())
    base = np.asarray(a.convert("L").resize(size), dtype=np.uint8)
    over = np.stack([base] * 3, axis=-1).copy() // 3 + 170
    over[near(only_a, 2)] = (220, 30, 30)
    over[near(only_b, 2)] = (30, 60, 220)
    return round(float(share), 4), Image.fromarray(over)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(SIZES) + ["classic"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--runs", type=int, default=1, help="2 = two independent runs that must agree (chemistry)")
    ap.add_argument("figures", nargs="*")
    args = ap.parse_args()
    crops = {p.stem: p for p in TODO.rglob("p*.png") if "_" not in p.stem}
    ids = sorted(crops) if args.all else args.figures
    out = ROOT / "figures" / "images" / "api" / args.model.replace("/", "_")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for fid in ids:
        crop = Image.open(crops[fid]).convert("RGB")
        if args.model == "classic":
            results = [classic(crop, fid in PANEL)]
        else:
            size = pick_size(args.model, *crop.size)
            padded, box = pad(crop, size)
            results = []
            for r in range(args.runs):
                try:
                    res = call(args.model, padded, size)
                except Exception as e:  # noqa: BLE001 — report and go on with the batch
                    print(f"{fid} run {r + 1}: FAILED {e}")
                    break
                W, H = res.size
                results.append(grey(res.crop((round(box[0] * W), round(box[1] * H), round(box[2] * W), round(box[3] * H)))))
            if len(results) < args.runs:
                rows.append((fid, None))
                continue
        res = results[0]
        res.save(out / f"{fid}.png")
        c = check(crop, res)
        agree = None
        if len(results) == 2:
            results[1].save(out / f"{fid}_run2.png")
            agree, overlay = run_agreement(results[0], results[1])
            overlay.save(out / f"{fid}_runs-diff.png")
        flag = (c["extra_ink"] > 0.04 or c["lost_ink"] > 0.04 or len(c["words_new"]) + len(c["words_gone"]) > 2
                or (agree is not None and agree > 0.01))
        rows.append((fid, {**c, "runs_disagree": agree, "flag": flag, "size": f"{res.width}x{res.height}"}))
        print(f"{fid}: {res.width}x{res.height} extra {c['extra_ink']} lost {c['lost_ink']} "
              f"words +{len(c['words_new'])}/-{len(c['words_gone'])} runs {agree} {'FLAG' if flag else 'ok'}")
    report = [f"# {args.model} — automatic checks", "",
              "extra/lost ink: share of line-art in one image with nothing near it in the other (>0.04 flags).",
              "runs: with --runs 2, share of line-art only one run has (>0.01 flags; see <id>_runs-diff.png).",
              "Words: OCR differences (OCR noise on both sides is normal; look at numbers and real words).",
              "Nothing here is accepted automatically: every result is checked by eye against the crop.", ""]
    for fid, c in rows:
        if c is None:
            report.append(f"## {fid} — failed\n")
            continue
        report += [f"## {fid} — {'FLAG' if c['flag'] else 'ok'} ({c['size']})",
                   f"- extra ink {c['extra_ink']} · lost ink {c['lost_ink']} · runs disagree {c['runs_disagree']}",
                   f"- new words: {', '.join(c['words_new']) or '—'}",
                   f"- gone words: {', '.join(c['words_gone']) or '—'}", ""]
    (out / f"report-{'runs2' if args.runs == 2 else 'single'}.md").write_text("\n".join(report))


if __name__ == "__main__":
    main()
