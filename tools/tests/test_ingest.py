"""Unit tests for the ingest producer's pure helpers."""
import ingest


def test_slugify():
    assert ingest.slugify("RTK (Rust Token Killer)") == "rtk-rust-token-killer"
    assert ingest.slugify("My Cool_Tool") == "my-cool-tool"
    assert ingest.slugify("") == ""
    assert ingest.slugify("...---") == ""


def test_parse_source_bold_fields():
    text = "# RTK\n\n**Category:** ecosystem\n**Tags:** token-optimizer, rust\n**Type:** reference\n\n## Description\nA Rust CLI proxy.\n"
    title, tags, body = ingest.parse_source(text)
    assert title == "RTK"
    assert tags == ["token-optimizer", "rust"]
    assert "**Category:**" not in body
    assert "A Rust CLI proxy." in body


def test_parse_source_yaml_frontmatter():
    text = "---\ntitle: AI Tooling\ntags: [ai, dx]\n---\n\n# AI Tooling\n\nBody here.\n"
    title, tags, body = ingest.parse_source(text)
    assert title == "AI Tooling"
    assert tags == ["ai", "dx"]
    assert "Body here." in body


def test_parse_source_no_frontmatter():
    text = "Plain text with no frontmatter or H1.\n\nBody line.\n"
    title, tags, body = ingest.parse_source(text)
    assert title is None
    assert tags == []
    assert "Body line." in body


def test_derive_description():
    assert ingest.derive_description("") == ""
    assert ingest.derive_description("# Heading\n\nFirst real line here.") == "First real line here."
    long_line = "x" * 200
    desc = ingest.derive_description(long_line)
    assert len(desc) == 140
    assert desc.endswith("...")


def test_render_concept_has_required_frontmatter():
    c = {
        "id": "tools/x", "type": "tool", "domain": "tools", "visibility": "shareable",
        "title": "X", "tags": ["a", "b"], "description": "desc",
        "sources": ["https://example.com/article.md"],
        "body": "# X\n\nBody.",
    }
    out = ingest.render_concept(c)
    assert out.startswith("---\n")
    assert "type: tool" in out
    assert "visibility: shareable" in out
    assert "  - https://example.com/article.md" in out
    assert out.rstrip().endswith("Body.")


def test_make_concept_from_url_source():
    text = "# My Tool\n\n**Tags:** cli, rust\n\nA tool description.\n"
    concept = ingest.make_concept("https://example.com/my-tool.md", text,
                                  "tool", "tools", "shareable")
    assert concept["id"] == "tools/my-tool"
    assert concept["type"] == "tool"
    assert concept["visibility"] == "shareable"
    assert concept["title"] == "My Tool"
    assert concept["tags"] == ["cli", "rust"]
    assert concept["sources"] == ["https://example.com/my-tool.md"]
    assert "A tool description." in concept["body"]


def test_make_concept_with_title_override():
    text = "No H1 here.\n\nJust body.\n"
    concept = ingest.make_concept("self:custom", text, "note", "tools",
                                  "private", title_override="Custom Title")
    assert concept["title"] == "Custom Title"
    assert concept["id"] == "tools/custom-title"
    assert concept["visibility"] == "private"


def test_make_concept_falls_back_to_source_slug():
    text = "No H1, no title.\n\nBody.\n"
    concept = ingest.make_concept("self:some-file.md", text, "note", "tools", "private")
    assert concept["title"] == "some-file"
    assert concept["id"] == "tools/some-file"


def test_default_visibility_by_domain():
    assert ingest.default_visibility("life") == "private"
    assert ingest.default_visibility("people") == "private"
    assert ingest.default_visibility("orgs") == "private"
    assert ingest.default_visibility("documents") == "private"
    assert ingest.default_visibility("tools") == "shareable"
    assert ingest.default_visibility("skills") == "shareable"
    assert ingest.default_visibility("learning") == "shareable"
    assert ingest.default_visibility("specs") == "shareable"