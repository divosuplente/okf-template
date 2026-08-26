#!/usr/bin/env python3
"""Mechanical post-ingest cleanup only.

NEVER assigns domain, subdomain, subsubdomain, or semantic tags.
Agent full-body classification (FBC) owns placement and meaning tags.

Safe operations:
  - flag / rename obvious garbage path-derived slugs (users-…-inbox-…)
  - strip banned noise tags: clippings (always); bare youtube optional
  - flag missing required frontmatter (type, visibility) or empty title

Usage:
  python3 tools/ingest_postprocess.py --dry-run
  python3 tools/ingest_postprocess.py --paths concepts/tools/foo.md
  python3 tools/ingest_postprocess.py --since-git  # changed concept files (best-effort)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
CONCEPTS = REPO_ROOT / "concepts"

# Import okf frontmatter helpers
sys.path.insert(0, str(TOOLS_DIR))
import okf  # noqa: E402

GARBAGE_SLUG_RE = re.compile(
    r"^(users?|home|var|tmp|private|folders)-.*|"
    r".*okf-inbox.*|"
    ,
    re.I,
)
BANNED_TAGS = {"clippings"}
OPTIONAL_NOISE = {"youtube"}  # strip only with --strip-youtube


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def iter_concept_paths(paths: list[str] | None):
    if paths:
        for p in paths:
            path = Path(p)
            if not path.is_absolute():
                path = REPO_ROOT / path
            if path.is_file() and path.suffix == ".md":
                yield path
        return
    if not CONCEPTS.exists():
        return
    for path in CONCEPTS.rglob("*.md"):
        if path.name in ("index.md", "log.md", "_template.md"):
            continue
        yield path


def parse_tags(fm: dict) -> list:
    return [str(t).strip() for t in okf.as_list(fm.get("tags")) if str(t).strip()]


def format_tags(tags: list[str]) -> str:
    return "[" + ", ".join(tags) + "]"


def rewrite_fm_tags(text: str, new_tags: list[str]) -> str:
    """Replace tags: line in frontmatter; supports inline list form only."""
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if i == 0 or i >= end:
            out.append(line)
            i += 1
            continue
        if re.match(r"^tags:\s*\[", line):
            out.append(f"tags: {format_tags(new_tags)}")
            i += 1
            continue
        if line.strip() == "tags:" or re.match(r"^tags:\s*$", line):
            # block list — replace following - items
            out.append(f"tags: {format_tags(new_tags)}")
            i += 1
            while i < end and re.match(r"^\s*-\s+", lines[i]):
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def process_file(path: Path, *, dry_run: bool, strip_youtube: bool) -> list[str]:
    notes = []
    text = path.read_text(encoding="utf-8")
    fm, body = okf.split_frontmatter(text)
    new_text = text

    # Required FM flags
    rel = _display_path(path)
    if not fm.get("type"):
        notes.append(f"FLAG missing type: {rel}")
    if not fm.get("visibility"):
        notes.append(f"FLAG missing visibility: {rel}")
    title = fm.get("title")
    if title is None or str(title).strip() in ("", "null"):
        notes.append(f"FLAG empty/missing title: {rel}")

    # Garbage slug flag (rename is opt-in via --rename-garbage and needs --title-slug)
    slug = path.stem
    if GARBAGE_SLUG_RE.match(slug):
        notes.append(f"FLAG garbage-slug (rename manually after FBC title): {rel}")

    # Tag strip — mechanical only
    tags = parse_tags(fm)
    banned = set(BANNED_TAGS)
    if strip_youtube:
        banned |= OPTIONAL_NOISE
    cleaned = []
    removed = []
    for t in tags:
        tl = t.lower().strip()
        if tl in banned:
            removed.append(tl)
            continue
        cleaned.append(t)
    # domain-redundant
    dom = str(fm.get("domain") or "").strip().lower()
    if dom:
        cleaned2 = []
        for t in cleaned:
            if t.lower().strip() == dom:
                removed.append(t)
            else:
                cleaned2.append(t)
        cleaned = cleaned2
    if removed:
        notes.append(
            f"{'WOULD strip' if dry_run else 'STRIP'} tags {removed} on {rel}"
        )
        new_text = rewrite_fm_tags(text, cleaned)
        if not dry_run and new_text != text:
            path.write_text(new_text, encoding="utf-8")

    return notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--paths", nargs="*", help="Concept paths (default: none — require paths or --all)")
    ap.add_argument("--all", action="store_true", help="Scan all concepts (slow)")
    ap.add_argument("--strip-youtube", action="store_true", help="Also strip bare youtube tags")
    args = ap.parse_args(argv)

    if not args.paths and not args.all:
        print("Specify --paths … or --all", file=sys.stderr)
        return 2

    paths = list(iter_concept_paths(None if args.all else args.paths))
    all_notes = []
    for path in paths:
        all_notes.extend(process_file(path, dry_run=args.dry_run, strip_youtube=args.strip_youtube))

    for n in all_notes:
        print(n)
    print(f"ingest_postprocess: {len(all_notes)} note(s) over {len(paths)} file(s); dry_run={args.dry_run}")
    print("NOTE: never classifies domain/sub/tags — FBC remains agent-owned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
