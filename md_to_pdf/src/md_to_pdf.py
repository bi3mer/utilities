"""Convert a Markdown file to a color-inverted PDF (black background, white text)."""
import argparse
import os
import sys
import tempfile
from pathlib import Path

import fitz
import markdown
from weasyprint import HTML


DEFAULT_CSS = """
@page {
    size: Letter;
    margin: 1in;
}
body {
    font-family: serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #000;
}
h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
}
code, pre {
    font-family: monospace;
    font-size: 10pt;
}
pre {
    padding: 0.5em;
    background: #eee;
    border-radius: 4px;
    overflow-x: auto;
}
"""


def confirm(prompt: str) -> bool:
    """Ask the user a yes/no question."""
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def md_to_pdf_bytes(md_path: Path, css: str) -> bytes:
    """Convert a Markdown file to PDF bytes via HTML."""
    md_text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "smarty"],
    )
    html_doc = (
        f"<!DOCTYPE html><html><head><style>{css}</style></head>"
        f"<body>{html_body}</body></html>"
    )
    return HTML(string=html_doc).write_pdf()


def invert_pdf(pdf_bytes: bytes, dst: Path, dpi: int) -> None:
    """Rasterize each page of an in-memory PDF and invert its colors."""
    scale = dpi / 72
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
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
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to a color-inverted PDF."
    )
    parser.add_argument("markdown", type=Path, help="Path to the input Markdown file.")
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="Resolution for rasterizing pages (default: 144).",
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=None,
        help="Optional CSS file for styling the PDF layout.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT",
        type=Path,
        default=None,
        help="Output PDF path (default: same name as input with .pdf extension).",
    )

    args = parser.parse_args()
    src: Path = args.markdown

    if not src.exists():
        sys.exit(f"Error: file not found: {src}")
    if src.suffix.lower() not in (".md", ".markdown", ".txt"):
        sys.exit(f"Error: expected a Markdown file, got: {src.suffix}")

    dst = args.output if args.output else src.with_suffix(".pdf")
    if dst.suffix.lower() != ".pdf":
        dst = dst.with_suffix(".pdf")

    if dst.exists():
        if not confirm(f"'{dst}' already exists. Overwrite?"):
            sys.exit("Aborted.")

    css = DEFAULT_CSS
    if args.css:
        if not args.css.exists():
            sys.exit(f"Error: CSS file not found: {args.css}")
        css = args.css.read_text(encoding="utf-8")

    print(f"Converting: {src} → {dst}  ({args.dpi} dpi)")
    print("  rendering markdown to PDF ...")
    pdf_bytes = md_to_pdf_bytes(src, css)
    print("  inverting colors ...")
    invert_pdf(pdf_bytes, dst, args.dpi)
