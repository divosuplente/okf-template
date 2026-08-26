#!/usr/bin/env python3
"""Snapshot formula regions from a PDF as small PNG crops.

Formulas are located by Docling's layout model (fast, no VLM) and rendered
with PyMuPDF. Each formula becomes a tiny PNG (~5-20KB) that chapter concepts
can embed — the image IS the math, no LaTeX needed.

Usage:
  .venv/bin/python tools/formula-snap.py <book.pdf> [--outdir DIR] [--zoom 2.0]

Output:
  <outdir>/<book-slug>/.book_to_skill/formulas/<chapter>_f<N>.png
  <outdir>/<book-slug>/.book_to_skill/formulas/manifest.json   (per-book)
  <outdir>/<book-slug>/.book_to_skill/formulas/<chapter>.md    (markdown refs)

Best used on per-chapter slices from tools/book-slicer.py (fast, focused);
also works on a whole book (formulas are keyed by page).

Dependencies: pymupdf + docling (both in the vault venv).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("pymupdf not found — run: uv pip install pymupdf")

DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent / "books" / "slices"

_SLUG_KEEP = re.compile(r"[^a-z0-9]+")


def slugify(text: str, maxlen: int = 60) -> str:
    return _SLUG_KEEP.sub("-", text.lower()).strip("-")[:maxlen].rstrip("-")


def formula_regions(pdf_path: Path) -> list[dict]:
    """Run Docling layout (fast, no VLM/pictures) and return formula regions.

    Each entry: {"page": 1-based, "l", "t", "r", "b"} in PDF points with the
    DOCLING origin convention (bottom-left, y-up).
    """
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = False  # formulas only — skip table cost
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    res = conv.convert(str(pdf_path))
    doc = res.document

    regions = []
    for item in doc.iterate_items():
        obj = item[0] if isinstance(item, tuple) else item
        lab = getattr(obj, "label", None)
        if lab is None or str(lab.value) != "formula":
            continue
        for prov in obj.prov:
            b = prov.bbox
            regions.append({
                "page": prov.page_no,
                "l": float(b.l), "t": float(b.t), "r": float(b.r), "b": float(b.b),
            })
    return regions


def snap(pdf_path: Path, outdir: Path, zoom: float, fmt: str, latex: bool) -> dict:
    from PIL import Image
    import io

    pdf = fitz.open(str(pdf_path))
    regions = formula_regions(pdf_path)
    if not regions:
        return {"formulas": 0, "error": "no formulas detected (scanned PDF? try --mode technical OCR)"}

    ocr = None
    if latex:
        try:
            from pix2tex.cli import LatexOCR
            ocr = LatexOCR()
        except ImportError:
            print("WARNING: pix2tex not installed — run: uv pip install pix2tex timm", file=sys.stderr)
            latex = False

    book_slug = slugify(pdf_path.stem)
    formulas_dir = outdir / book_slug / ".book_to_skill" / "formulas"
    formulas_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    per_page: dict[int, list[dict]] = {}
    for i, r in enumerate(regions, 1):
        page = pdf[r["page"] - 1]
        pw, ph = page.rect.width, page.rect.height
        # Docling bbox is bottom-left origin, y-up: t > b in y-up. For fitz
        # (top-left origin, y-down): y0 = ph - t, y1 = ph - b.
        clip = fitz.Rect(r["l"], ph - r["t"], r["r"], ph - r["b"])
        clip = clip & page.rect  # clamp to page
        if clip.is_empty or clip.width < 2 or clip.height < 2:
            continue
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        stem = f"{r['page']:03d}_f{i:03d}"
        if fmt == "webp":
            im = Image.open(io.BytesIO(pix.tobytes("png")))
            im.save(formulas_dir / f"{stem}.webp", "WEBP", lossless=True)
            fname = f"{stem}.webp"
        else:
            pix.save(str(formulas_dir / f"{stem}.png"))
            fname = f"{stem}.png"
        out = formulas_dir / fname
        entry = {
            "file": fname,
            "page": r["page"],
            "size_bytes": out.stat().st_size,
        }
        if ocr is not None:
            try:
                entry["latex"] = ocr(Image.open(out))
            except Exception as e:
                entry["latex"] = None
                entry["latex_error"] = str(e)
        saved.append(entry)
        per_page.setdefault(r["page"], []).append(entry)

    manifest = {
        "book": pdf_path.name,
        "source": str(pdf_path.resolve()),
        "zoom": zoom,
        "format": fmt,
        "latex": bool(ocr),
        "formula_count": len(saved),
        "total_bytes": sum(s["size_bytes"] for s in saved),
        "formulas": saved,
    }
    (formulas_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Per-book markdown refs, one section per page. With --latex, each formula
    # gets the image AND its LaTeX (rendered by Obsidian) side by side.
    md_lines = [f"# {pdf_path.name} — formula snapshots", "",
                f"{len(saved)} formulas ({fmt}), {manifest['total_bytes'] // 1024} KB total."
                + (" + LaTeX OCR" if ocr else ""), ""]
    for page_no in sorted(per_page):
        md_lines.append(f"## Page {page_no}")
        for entry in per_page[page_no]:
            md_lines.append(f"![formula]({entry['file']})")
            if entry.get("latex"):
                md_lines.append(f"$${entry['latex']}$$")
        md_lines.append("")
    (formulas_dir / "formulas.md").write_text("\n".join(md_lines), encoding="utf-8")

    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="path to a PDF (prefer a chapter slice)")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("--zoom", type=float, default=2.0, help="render scale (default 2.0 ≈ 144dpi)")
    ap.add_argument("--format", dest="fmt", choices=["webp", "png"], default="webp",
                    help="output format (default webp — ~54% smaller than png, lossless)")
    ap.add_argument("--latex", action="store_true",
                    help="also OCR each formula to LaTeX with pix2tex (~1.5s/formula; "
                         "needs: uv pip install pix2tex timm)")
    args = ap.parse_args()

    path = Path(args.book).expanduser()
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 1

    manifest = snap(path, args.outdir, args.zoom, args.fmt, args.latex)
    if "error" in manifest:
        print(f"ERROR: {manifest['error']}", file=sys.stderr)
        return 1

    print(f"Formulas: {manifest['formula_count']}")
    print(f"Format:   {manifest['format']}" + (" + LaTeX OCR" if manifest.get("latex") else ""))
    print(f"Total:    {manifest['total_bytes'] / 1024:.0f} KB ({manifest['total_bytes'] / 1024 / max(manifest['formula_count'], 1):.1f} KB avg)")
    print(f"Out:      {args.outdir / slugify(path.stem) / '.book_to_skill' / 'formulas'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
