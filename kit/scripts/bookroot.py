"""Where the book is: every kit script works on one book project (a folder with a book.yaml).

The book root is $BOOK_ROOT if set, else the nearest folder at or above the current directory that contains
book.yaml. So run scripts from inside the book (`cd books/<slug> && scriptorium run build_content 3`), or set BOOK_ROOT.
CONFIG is the parsed book.yaml (title, authors, languages, units …).
"""
import os
import sys
from pathlib import Path

import yaml


def _find() -> Path:
    env = os.environ.get("BOOK_ROOT")
    if env:
        return Path(env).resolve()
    here = Path.cwd().resolve()
    for p in (here, *here.parents):
        if (p / "book.yaml").exists():
            return p
    sys.exit("No book.yaml found here or above — run from inside a book folder, or set BOOK_ROOT.")


ROOT = _find()
CONFIG = yaml.safe_load((ROOT / "book.yaml").read_text()) or {}
KIT = Path(__file__).resolve().parent.parent
