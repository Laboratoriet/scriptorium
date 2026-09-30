"""Render every molecule of a scheme/generic spec to PNG, for checking a reading atom by atom against the crop.

Usage: scriptorium run render_spec work/scheme_rollout/A/p0123-1.yaml <out-dir>     → <out-dir>/<node>.png (500 px wide)

Generic nodes (R groups, locants, floating bonds, highlights, drawn H, dashed bonds) go through render_generic,
the rest through render_mol with the drawn stereo — the same renderers the site uses.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from render_structures import render_generic, render_mol  # noqa: E402
from scheme_preview import node_mol  # noqa: E402

GENERIC = ("rgroups", "locants", "attach", "highlight", "show_h", "dashed")


def main(spec_path: str, out: str) -> None:
    import cairosvg

    spec = yaml.safe_load(Path(spec_path).read_text())
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, n in (spec.get("nodes") or {}).items():
        if not n.get("smiles"):
            continue
        svg = out_dir / f"{key}.svg"
        if any(n.get(k) for k in GENERIC):
            render_generic(n, svg)
        else:
            render_mol(node_mol(n), svg)
        cairosvg.svg2png(url=str(svg), write_to=str(out_dir / f"{key}.png"), output_width=500, background_color="white")
        print(out_dir / f"{key}.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
