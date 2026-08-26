#!/usr/bin/env python3
"""Slice books into per-chapter PDFs so study concepts can reference the exact
pages of the original (formulas, figures, layout intact).

Usage:
  .venv/bin/python tools/book-slicer.py <book.pdf|epub> [--outdir DIR] [--dry-run] [--json]

- PDF with bookmarks: chapter ranges come from the outline (exact).
- PDF without bookmarks: chapter starts detected from heading text (same
  patterns as book-to-skill's engine).
- EPUB: chapters are already separate spine items — no physical slicing; the
  tool writes a manifest mapping chapter titles to spine items so concepts can
  reference them by title/index.

Output:
  <outdir>/<book-slug>/<NN>-<chapter-slug>.pdf   (slices; EPUB: none)
  <outdir>/<book-slug>/manifest.json             (machine-readable map)
  <outdir>/<book-slug>/manifest.md               (human-readable map)

Slices are committed to the vault (default outdir: books/slices/) so study
concepts can reference them; the original books stay outside the repo.

Dependencies: pypdf (already in the vault venv), stdlib otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf not found — run: uv pip install -e 'tools/book-to-skill[pdf]'")

# Slices live in the vault (committed); originals stay outside the repo.
DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent / "books" / "slices"

_SLUG_KEEP = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"^[-_]+|[-_]+$")


def slugify(text: str, maxlen: int = 48) -> str:
    s = _SLUG_KEEP.sub("-", text.lower()).strip("-")
    s = _SLUG_TRIM.sub("", s)
    return s[:maxlen].rstrip("-")


# Chapter heading patterns (mirror book_to_skill/utils.py).
_EXPLICIT_CHAPTER = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:chapter|cap[ií]tulo|kapitel|capitolo|hoofdstuk|ch\.?)\s*([0-9]{1,2})\b",
    re.IGNORECASE,
)
_ROMAN_HEAD = re.compile(r"^\s*([IVXLCDM]+)\s*[:.]\s+[A-Z]")
_CN_CHAPTER = re.compile(r"^\s*第\s*([0-9０-９〇零一二两三四五六七八九十百千]+)\s*[章回卷节篇讲]")
_KO_CHAPTER = re.compile(r"^\s*제\s*([0-9]+)\s*[장편절관]")
_TH_CHAPTER = re.compile(r"^\s*(?:บทที่|ตอนที่|ภาคที่)\s*([0-9๐-๙]+)")


def _heading_number(line: str) -> int | None:
    m = _EXPLICIT_CHAPTER.match(line)
    if m:
        return int(m.group(1))
    m = _CN_CHAPTER.match(line)
    if m:
        digits = {"０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
                  "５": "5", "６": "6", "７": "7", "８": "8", "９": "9"}
        s = "".join(digits.get(c, c) for c in m.group(1))
        if s.isdigit():
            return int(s)
    m = _KO_CHAPTER.match(line)
    if m:
        return int(m.group(1))
    m = _TH_CHAPTER.match(line)
    if m:
        return int("".join(str("๐๑๒๓๔๕๖๗๘๙".index(c)) if c in "๐๑๒๓๔๕๖๗๘๙" else c for c in m.group(1)))
    return None


def _roman_to_int(s: str) -> int | None:
    """Convert a Roman numeral to integer. Returns None if invalid."""
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(s.upper()):
        v = vals.get(ch)
        if v is None:
            return None
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def _bookmarks_map(reader: PdfReader) -> dict[int, tuple[str, int]]:
    """{chapter_number: (title, pdf_page_index)} from the outline."""
    out: dict[int, tuple[str, int]] = {}

    def walk(items, depth=0):
        for it in items:
            if isinstance(it, list):
                walk(it, depth + 1)
            else:
                title = it.title or ""
                num = None
                # Traditional chapter headings at shallow depth
                if depth <= 1 and re.search(r"\bchapter\b", title, re.IGNORECASE):
                    m = re.search(r"\b(\d{1,3})\b", title)
                    if m:
                        num = int(m.group(1))
                    else:
                        m = re.search(r"\b([IVXLCDM]+)\b", title)
                        if m:
                            num = _roman_to_int(m.group(1))
                # Numbered sections like "1. Categories: The Idea" at depth 1-2
                # (common in textbooks where chapters live under Parts)
                elif depth <= 2:
                    m = re.match(r"^\s*(\d{1,3})\b", title)
                    if m:
                        num = int(m.group(1))
                if num is not None and num not in out:
                    out[num] = (title.strip(), reader.get_destination_page_number(it))

    try:
        walk(reader.outline)
    except Exception:
        return {}
    return out


def _headings_map(reader: PdfReader) -> dict[int, tuple[str, int]]:
    """{chapter_number: (heading_line, pdf_page_index)} from text scan."""
    out: dict[int, tuple[str, int]] = {}
    for i in range(len(reader.pages)):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            continue
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            num = _heading_number(line)
            if num is not None and num not in out:
                out[num] = (line[:80], i)
                break
    return out


def slice_pdf(path: Path, outdir: Path, dry_run: bool) -> dict:
    reader = PdfReader(str(path))
    total = len(reader.pages)
    bookmarks = _bookmarks_map(reader)
    headings = _headings_map(reader)
    source = "bookmarks" if len(bookmarks) >= 3 else "headings"
    chapter_map = bookmarks if source == "bookmarks" else headings

    if not chapter_map:
        return {"error": "no chapter mapping found (no bookmarks, no headings)", "source": source}

    nums = sorted(chapter_map)
    entries = []
    for i, num in enumerate(nums):
        title, start = chapter_map[num]
        end = chapter_map[nums[i + 1]][1] if i + 1 < len(nums) else total
        entries.append({
            "number": num,
            "title": title,
            "pdf_page_start": start,
            "pdf_page_end": end - 1,
            "page_count": end - start,
            "file": f"{num:02d}-{slugify(title)}.pdf",
        })

    book_dir = outdir / slugify(path.stem)
    if not dry_run:
        book_dir.mkdir(parents=True, exist_ok=True)
        for e in entries:
            writer = PdfWriter()
            for p in range(e["pdf_page_start"], e["pdf_page_end"] + 1):
                writer.add_page(reader.pages[p])
            with open(book_dir / e["file"], "wb") as fh:
                writer.write(fh)

    manifest = {
        "book": path.name,
        "source_path": str(path.resolve()),
        "mapping": source,
        "total_pages": total,
        "chapters": entries,
    }
    return manifest


def slice_epub(path: Path, outdir: Path, dry_run: bool) -> dict:
    """EPUB chapters are already separate spine items; emit the map only."""
    import zipfile

    entries = []
    try:
        with zipfile.ZipFile(path) as zf:
            opf = next(n for n in zf.namelist() if n.endswith(".opf"))
            opf_text = zf.read(opf).decode("utf-8", errors="replace")
            manifest_items = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"', opf_text))
            spine_refs = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf_text)
            for idx, ref in enumerate(spine_refs, 1):
                href = manifest_items.get(ref, ref)
                entries.append({
                    "number": idx,
                    "title": href.rsplit("/", 1)[-1],
                    "spine_item": href,
                    "file": None,  # no physical slice for EPUB
                })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"epub mapping failed: {e}"}

    return {
        "book": path.name,
        "source_path": str(path.resolve()),
        "mapping": "epub-spine",
        "note": "EPUB chapters are separate spine items — reference by chapter title/number in the original.",
        "chapters": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", help="path to a .pdf or .epub")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help=f"output dir (default {DEFAULT_OUTDIR})")
    ap.add_argument("--dry-run", action="store_true", help="map chapters but write no slices")
    ap.add_argument("--json", action="store_true", help="print manifest as JSON")
    args = ap.parse_args()

    path = Path(args.book).expanduser()
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 1

    if path.suffix.lower() == ".pdf":
        manifest = slice_pdf(path, args.outdir, args.dry_run)
    elif path.suffix.lower() == ".epub":
        manifest = slice_epub(path, args.outdir, args.dry_run)
    else:
        print(f"ERROR: unsupported format {path.suffix} (pdf or epub only)", file=sys.stderr)
        return 1

    if "error" in manifest:
        print(f"ERROR: {manifest['error']}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    book_dir = args.outdir / slugify(path.stem)
    print(f"Book:   {path.name}")
    print(f"Mapping: {manifest['mapping']}  ({manifest['total_pages']} pages)" if "total_pages" in manifest
          else f"Mapping: {manifest['mapping']}  ({len(manifest['chapters'])} spine items)")
    print(f"Chapters: {len(manifest['chapters'])}")
    for e in manifest["chapters"][:10]:
        if e["file"]:
            print(f"  ch{e['number']:>3}  pages {e['pdf_page_start']:>4}-{e['pdf_page_end']:>4}  -> {book_dir.name}/{e['file']}")
        else:
            print(f"  ch{e['number']:>3}  {e['spine_item']}  (EPUB — reference by title)")
    if len(manifest["chapters"]) > 10:
        print(f"  ... and {len(manifest['chapters']) - 10} more")

    if not args.dry_run:
        book_dir.mkdir(parents=True, exist_ok=True)
        (book_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        md_lines = [f"# {manifest['book']} — chapter slices", "",
                    f"- Source: `{manifest['source_path']}`", f"- Mapping: {manifest['mapping']}",
                    f"- Total pages: {manifest.get('total_pages', 'n/a (epub)')}", ""]
        for e in manifest["chapters"]:
            if e["file"]:
                md_lines.append(f"- ch{e['number']}: {e['title']} — pages {e['pdf_page_start']}-{e['pdf_page_end']} → `{e['file']}`")
            else:
                md_lines.append(f"- ch{e['number']}: {e['spine_item']} (EPUB spine item)")
        (book_dir / "manifest.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print(f"\nSlices + manifest written to: {book_dir}")
    else:
        print("\nDry run — nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
