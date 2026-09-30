"""Render book pages from the PDF at 150 dpi → source/pages/NNNN/pdf.png.

Usage: scriptorium run render_pages <first_book_page> <last_book_page> [workers]

Renders contiguous PDF ranges in one pdftoppm call each (the 337 MB PDF is parsed
once per chunk instead of once per page), several chunks in parallel.
Pages that already have pdf.png are skipped.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bookroot import CONFIG, ROOT  # the book project (book.yaml), not the kit
SRC = ROOT / "source"
book_to_pdf = {int(k): v for k, v in json.loads((SRC / "book_to_pdf.json").read_text()).items()}


def render_chunk(pdf_pages: list[int]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["pdftoppm", "-f", str(pdf_pages[0]), "-l", str(pdf_pages[-1]), "-r", "150", "-png",
             str(SRC / CONFIG["source_pdf"]), f"{tmp}/p"],
            check=True,
        )
        pdf_to_book = {v: k for k, v in book_to_pdf.items()}
        done = 0
        for png in Path(tmp).glob("p-*.png"):
            pdf_page = int(png.stem.split("-")[1])
            book = pdf_to_book.get(pdf_page)
            target = SRC / "pages" / f"{book:04d}" / "pdf.png" if book else None
            if target and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(png, target)  # tmp may be on another volume
                done += 1
        return done


def main(first: int, last: int, workers: int = 4, chunk: int = 20) -> None:
    todo = [book_to_pdf[p] for p in range(first, last + 1)
            if p in book_to_pdf and not (SRC / "pages" / f"{p:04d}" / "pdf.png").exists()]
    chunks = [todo[i:i + chunk] for i in range(0, len(todo), chunk)]
    print(f"rendering {len(todo)} pages in {len(chunks)} chunks", flush=True)
    with ThreadPoolExecutor(workers) as pool:
        for n in pool.map(render_chunk, chunks):
            print(f"  +{n}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
