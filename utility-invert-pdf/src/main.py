"""Invert the colors of a PDF file."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

import fitz


def confirm(prompt: str) -> bool:
    """Ask the user a yes/no question."""
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def invert_pdf(src: Path, dst: Path, dpi: int) -> None:
    """Rasterize each page of a PDF and invert its colors."""
    scale = dpi / 72
    doc = fitz.open(src)
    out = fitz.open()

    for page_num, page in enumerate(doc, start=1):
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        pix.invert_irect(pix.irect)
        img_page = out.new_page(width=pix.width, height=pix.height)
        img_page.insert_image(img_page.rect, pixmap=pix)
        print(f"  processed page {page_num}/{len(doc)}", end="\r")

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=dst.parent)
    os.close(tmp_fd)
    try:
        out.save(tmp_path, deflate=True)
        Path(tmp_path).replace(dst)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    finally:
        doc.close()
        out.close()

    print(f"\nSaved → {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Invert the colors of a PDF file.")
    parser.add_argument("pdf", type=Path, help="Path to the input PDF file.")
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="Resolution for rasterizing pages (default: 144).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT",
        type=Path,
        default=None,
        help="Output PDF path (default: overwrite the input file).",
    )

    args = parser.parse_args()
    src: Path = args.pdf

    if not src.exists():
        sys.exit(f"Error: file not found: {src}")
    if src.suffix.lower() != ".pdf":
        sys.exit(f"Error: expected a PDF file, got: {src.suffix}")

    dst = args.output if args.output else src

    if dst != src and dst.exists():
        if not confirm(f"'{dst}' already exists. Overwrite?"):
            sys.exit("Aborted.")

    print(f"Inverting: {src} → {dst}")
    print(f"  rasterizing at {args.dpi} dpi ...")
    invert_pdf(src, dst, args.dpi)


if __name__ == "__main__":
    main()
