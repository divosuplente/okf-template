#!/usr/bin/env python3
"""Custom PDF slicer accepting a JSON chapter map. Supports pypdf and pymupdf fallback."""
from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False

try:
    import pymupdf
    HAS_PYMUPDF = True
except Exception:
    HAS_PYMUPDF = False

DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent / "books" / "slices"

_SLUG_KEEP = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"^[-_]+|[-_]+$")

def slugify(text: str, maxlen: int = 48) -> str:
    s = _SLUG_KEEP.sub("-", text.lower()).strip("-")
    s = _SLUG_TRIM.sub("", s)
    return s[:maxlen].rstrip("-")

def slice_with_pypdf(path: Path, chapters: list[dict], outdir: Path):
    reader = PdfReader(str(path))
    total = len(reader.pages)
    nums = [c["number"] for c in chapters]
    entries = []
    for i, ch in enumerate(chapters):
        num = ch["number"]
        title = ch["title"]
        start = ch["start_page"]
        end = chapters[i + 1]["start_page"] - 1 if i + 1 < len(chapters) else total - 1
        entries.append({
            "number": num,
            "title": title,
            "pdf_page_start": start,
            "pdf_page_end": end,
            "page_count": end - start + 1,
            "file": f"{num:02d}-{slugify(title)}.pdf",
        })
    outdir.mkdir(parents=True, exist_ok=True)
    for e in entries:
        writer = PdfWriter()
        for p in range(e["pdf_page_start"], e["pdf_page_end"] + 1):
            writer.add_page(reader.pages[p])
        with open(outdir / e["file"], "wb") as fh:
            writer.write(fh)
    return entries

def slice_with_pymupdf(path: Path, chapters: list[dict], outdir: Path):
    doc = pymupdf.open(str(path))
    total = len(doc)
    entries = []
    for i, ch in enumerate(chapters):
        num = ch["number"]
        title = ch["title"]
        start = ch["start_page"]
        end = chapters[i + 1]["start_page"] - 1 if i + 1 < len(chapters) else total - 1
        entries.append({
            "number": num,
            "title": title,
            "pdf_page_start": start,
            "pdf_page_end": end,
            "page_count": end - start + 1,
            "file": f"{num:02d}-{slugify(title)}.pdf",
        })
    outdir.mkdir(parents=True, exist_ok=True)
    for e in entries:
        new_doc = pymupdf.open()
        new_doc.insert_pdf(doc, from_page=e["pdf_page_start"], to_page=e["pdf_page_end"])
        new_doc.save(str(outdir / e["file"]))
        new_doc.close()
    doc.close()
    return entries

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("book", help="path to .pdf")
    ap.add_argument("--map", dest="map_path", required=True, help="JSON chapter map [{number,title,start_page},...]")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("--backend", choices=["auto","pypdf","pymupdf"], default="auto")
    args = ap.parse_args()

    chapters = json.loads(Path(args.map_path).read_text(encoding="utf-8"))
    path = Path(args.book).expanduser()
    slug = slugify(path.stem)
    outdir = args.outdir / slug

    backend = args.backend
    if backend == "auto":
        if HAS_PYPDF:
            backend = "pypdf"
        elif HAS_PYMUPDF:
            backend = "pymupdf"
        else:
            sys.exit("No PDF backend available (install pypdf or pymupdf)")

    if backend == "pypdf" and not HAS_PYPDF:
        sys.exit("pypdf not available")
    if backend == "pymupdf" and not HAS_PYMUPDF:
        sys.exit("pymupdf not available")

    slicer = slice_with_pypdf if backend == "pypdf" else slice_with_pymupdf
    entries = slicer(path, chapters, outdir)

    manifest = {
        "book": path.name,
        "source_path": str(path.resolve()),
        "mapping": "manual-chapter-map",
        "total_pages": (entries[-1]["pdf_page_end"] + 1) if entries else 0,
        "chapters": entries,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# {manifest['book']} — chapter slices", "",
          f"- Source: `{manifest['source_path']}`",
          f"- Mapping: {manifest['mapping']}",
          f"- Total pages: {manifest['total_pages']}", ""]
    for e in entries:
        md.append(f"- ch{e['number']}: {e['title']} — pages {e['pdf_page_start']}-{e['pdf_page_end']} → `{e['file']}`")
    (outdir / "manifest.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} slices to {outdir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
