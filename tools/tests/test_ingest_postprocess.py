"""Unit tests for mechanical ingest_postprocess (never classifies)."""
import sys
from pathlib import Path

import ingest_postprocess as ip
import okf


def test_garbage_slug_regex():
    assert ip.GARBAGE_SLUG_RE.match("users-ima-okf-inbox-foo")
    assert not ip.GARBAGE_SLUG_RE.match("okf-pipeline")


def test_strip_clippings_tag_dry_run(tmp_path):
    p = tmp_path / "sample.md"
    p.write_text(
        "---\n"
        "type: tool\n"
        "visibility: shareable\n"
        "title: Sample\n"
        "domain: tools\n"
        "tags: [clippings, agent, tools]\n"
        "---\n\n# Sample\nbody\n",
        encoding="utf-8",
    )
    notes = ip.process_file(p, dry_run=True, strip_youtube=False)
    text = p.read_text(encoding="utf-8")
    assert "clippings" in text  # dry-run does not write
    assert any("WOULD strip" in n for n in notes)
    notes2 = ip.process_file(p, dry_run=False, strip_youtube=False)
    text2 = p.read_text(encoding="utf-8")
    assert "clippings" not in text2
    assert "agent" in text2
    # domain-redundant 'tools' stripped
    assert "tools]" not in text2 and "tools," not in text2


def test_never_sets_domain_field(tmp_path):
    p = tmp_path / "x.md"
    p.write_text(
        "---\ntype: note\nvisibility: private\ntitle: X\ntags: [clippings]\n---\n\nbody\n",
        encoding="utf-8",
    )
    ip.process_file(p, dry_run=False, strip_youtube=False)
    fm, _ = okf.split_frontmatter(p.read_text(encoding="utf-8"))
    assert "domain" not in fm or fm.get("domain") in (None, "")


def test_main_requires_paths_or_all():
    assert ip.main([]) == 2
