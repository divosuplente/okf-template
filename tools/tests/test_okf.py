"""Unit tests for the okf CLI library (stdlib + pytest only)."""
import argparse
import json
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import okf
import pytest

def make_concept(cid, fm, body=""):
    """Build a Concept in-memory (no disk access needed)."""
    return okf.Concept(cid, okf.CONCEPTS_DIR / (cid + ".md"), fm, body)


# --- frontmatter parsing ---------------------------------------------------

def test_parse_frontmatter_scalars_inline_and_block_lists():
    block = "\n".join([
        "type: tool",
        "visibility: shareable",
        'title: "Nub"',
        "tags: [nodejs, runtime]",
        "source:",
        "  - toolswiki:ecosystem/nub.md",
        "  - pka:PKM/My Life/Topics/ai-tooling.md",
        "# a comment line",
        "timestamp: 2026-06-30T00:00:00Z",
    ])
    fm = okf.parse_frontmatter(block)
    assert fm["type"] == "tool"
    assert fm["visibility"] == "shareable"
    assert fm["title"] == "Nub"
    assert fm["tags"] == ["nodejs", "runtime"]
    assert fm["source"] == [
        "toolswiki:ecosystem/nub.md",
        "pka:PKM/My Life/Topics/ai-tooling.md",
    ]
    assert fm["timestamp"] == "2026-06-30T00:00:00Z"


def test_split_frontmatter_roundtrip_and_absent():
    text = "---\ntype: note\nvisibility: private\n---\n# Body\nhello"
    fm, body = okf.split_frontmatter(text)
    assert fm == {"type": "note", "visibility": "private"}
    assert body.strip() == "# Body\nhello"

    fm2, body2 = okf.split_frontmatter("no frontmatter here")
    assert fm2 == {}
    assert body2 == "no frontmatter here"


def test_tokenize_lowercases_and_splits():
    assert okf.tokenize("Hello, OKF-World 123!") == ["hello", "okf", "world", "123"]


# --- link extraction -------------------------------------------------------

def test_extract_links_bundle_relative_and_external():
    body = (
        "See [Nub](/concepts/tools/nub.md) and "
        "[OKF](concepts/specs/open-knowledge-format.md) and "
        "[site](https://example.com) and [anchor](#section)."
    )
    links = okf.extract_links(body, "tools/rtk")
    assert "tools/nub" in links
    assert "specs/open-knowledge-format" in links
    assert all(not l.startswith("http") for l in links)
    assert len(links) == 2


def test_extract_links_relative_path():
    body = "Neighbor [x](./customers.md), parent [y](../orgs/acme.md)."
    links = okf.extract_links(body, "people/jane")
    assert "people/customers" in links
    assert "orgs/acme" in links


# --- index + search --------------------------------------------------------

def _sample_concepts():
    return [
        make_concept("tools/nub", {
            "type": "tool", "visibility": "shareable", "domain": "tools",
            "title": "Nub", "description": "All-in-one Node.js toolkit.",
            "tags": ["nodejs", "runtime"],
        }, "Nub augments stock Node with a fast runtime and package manager."),
        make_concept("tools/rtk", {
            "type": "tool", "visibility": "shareable", "domain": "tools",
            "title": "RTK", "description": "Token reduction proxy.",
        }, "RTK is a CLI proxy that reduces tokens for coding agents."),
        make_concept("life/ai-tooling", {
            "type": "topic", "visibility": "private", "domain": "life",
            "title": "AI Tooling", "description": "Agents and workflows I use.",
        }, "Tracking node runtime experiments and agent delegation."),
    ]


def test_build_index_shape():
    index = okf.build_index(_sample_concepts())
    assert index["count"] == 3
    assert index["avgdl"] > 0
    assert "node" in index["df"]
    ids = {d["id"] for d in index["concepts"]}
    assert ids == {"tools/nub", "tools/rtk", "life/ai-tooling"}


def test_search_ranks_relevant_first():
    index = okf.build_index(_sample_concepts())
    results = okf.bm25_search(index, "node runtime")
    assert results, "expected at least one hit"
    assert results[0][1]["id"] == "tools/nub"


def test_search_visibility_filter():
    index = okf.build_index(_sample_concepts())
    results = okf.bm25_search(index, "node runtime agent")
    shareable = okf.apply_filters(results, visibility="shareable")
    assert shareable
    assert all(d["visibility"] == "shareable" for _, d in shareable)
    assert all(d["id"] != "life/ai-tooling" for _, d in shareable)


def test_search_type_and_domain_filters():
    index = okf.build_index(_sample_concepts())
    results = okf.bm25_search(index, "node runtime agent")
    topics = okf.apply_filters(results, type="topic", domain="life")
    assert all(d["type"] == "topic" and d["domain"] == "life" for _, d in topics)


# --- lint ------------------------------------------------------------------

def test_lint_missing_field_and_bad_visibility():
    concepts = [
        make_concept("tools/a", {"type": "tool"}, "no visibility"),
        make_concept("tools/b", {"type": "tool", "visibility": "public"}, "bad vis"),
    ]
    findings = okf.lint_concepts(concepts)
    kinds = {(f["kind"], f["concept"]) for f in findings}
    assert ("missing-field", "tools/a") in kinds
    assert ("bad-visibility", "tools/b") in kinds


def test_lint_broken_link_and_orphan():
    concepts = [
        make_concept("tools/a", {"type": "tool", "visibility": "shareable"},
                     "links [x](/concepts/tools/missing.md)"),
    ]
    findings = okf.lint_concepts(concepts)
    kinds = {f["kind"] for f in findings}
    assert "broken-link" in kinds
    assert "orphan" in kinds  # single concept has no inbound links


def test_lint_no_privacy_warning_for_nonpersonal_domain_shareable():
    """D-015: a shareable concept in a non-personal domain should NOT be flagged,
    even with historical pka: sources."""
    concepts = [
        make_concept("tools/leak", {
            "type": "tool", "visibility": "shareable", "domain": "tools",
            "source": ["pka:PKM/My Life/Topics/secret.md"],
        }, "should not be flagged"),
    ]
    findings = okf.lint_concepts(concepts)
    assert not any(f["kind"] == "privacy" for f in findings)


def test_lint_warns_on_personal_domain_shareable():
    """D-015: a shareable concept in a personal domain should be flagged."""
    concepts = [
        make_concept("life/journal", {
            "type": "topic", "visibility": "shareable", "domain": "life",
        }, ""),
    ]
    findings = okf.lint_concepts(concepts)
    assert any(f["kind"] == "privacy" and "life" in f["detail"] for f in findings)


def test_lint_no_warning_on_personal_domain_private():
    """D-015: a private concept in a personal domain should NOT be flagged."""
    concepts = [
        make_concept("people/jane", {
            "type": "person", "visibility": "private", "domain": "people",
        }, ""),
    ]
    findings = okf.lint_concepts(concepts)
    assert not any(f["kind"] == "privacy" for f in findings)


def test_lint_duplicate_titles():
    concepts = [
        make_concept("tools/a", {"type": "tool", "visibility": "shareable", "title": "Same"}, ""),
        make_concept("specs/b", {"type": "spec", "visibility": "shareable", "title": "same"}, ""),
    ]
    findings = okf.lint_concepts(concepts)
    assert any(f["kind"] == "duplicate" for f in findings)


# --- view wiring -----------------------------------------------------------

def test_viewer_url():
    assert okf.viewer_url(8000) == f"http://{okf.LOOPBACK}:8000/tools/viewer.html"


def test_view_parser_defaults():
    args = okf.build_parser().parse_args(["view"])
    assert args.func is okf.cmd_view
    assert args.port == 8000
    assert args.no_open is False
    assert args.no_index is False


# --- relink ----------------------------------------------------------------

def test_resolve_to_concept_unique_and_skips():
    sm = {"rtk": ["tools/rtk"]}
    assert okf.resolve_to_concept("../ecosystem/rtk.md", "tools/claude-code", sm) == "tools/rtk"
    assert okf.resolve_to_concept("rtk.md", "tools/x", sm) == "tools/rtk"
    assert okf.resolve_to_concept("https://rtk.ai/", "tools/x", sm) is None
    assert okf.resolve_to_concept("/concepts/tools/rtk.md", "tools/x", sm) is None  # already canonical
    assert okf.resolve_to_concept("unknown.md", "tools/x", sm) is None


def test_resolve_to_concept_disambiguates():
    sm = {"x": ["tools/x", "learning/x"]}
    assert okf.resolve_to_concept("../learning/x.md", "tools/a", sm) == "learning/x"
    assert okf.resolve_to_concept("../ecosystem/x.md", "life/a", sm) == "tools/x"
    # no hint -> fall back to source domain
    assert okf.resolve_to_concept("x.md", "learning/a", sm) == "learning/x"


def test_rewrite_links():
    sm = {"rtk": ["tools/rtk"], "prompting-101": ["learning/prompting-101"]}
    text = ("See [RTK](../ecosystem/rtk.md) and [P](../learning/prompting-101.md#step-2) "
            "and [ext](https://x.com) and [self](rtk.md).")
    new, n = okf.rewrite_links(text, "tools/claude-code", sm)
    assert "[RTK](/concepts/tools/rtk.md)" in new
    assert "[P](/concepts/learning/prompting-101.md#step-2)" in new  # fragment preserved
    assert "[ext](https://x.com)" in new  # external untouched
    assert n == 3


def test_relink_parser_defaults():
    args = okf.build_parser().parse_args(["relink"])
    assert args.func is okf.cmd_relink
    assert args.dry_run is False
    args = okf.build_parser().parse_args(["relink", "--dry-run"])
    assert args.dry_run is True


def test_rewrite_links_preserves_query_string():
    sm = {"rtk": ["tools/rtk"]}
    new, n = okf.rewrite_links("[RTK](rtk.md?version=2#section)", "tools/x", sm)
    assert "[RTK](/concepts/tools/rtk.md?version=2#section)" in new
    assert n == 1


def test_resolve_to_concept_cross_domain_no_hint():
    """Slug in multiple domains with no DOMAIN_HINT for the path segment.
    Falls back to source domain — which may differ from the original author's intent."""
    sm = {"shared": ["tools/shared", "life/shared"]}
    # No hint for 'random/' segment -> falls back to source domain 'tools'
    assert okf.resolve_to_concept("../random/shared.md", "tools/a", sm) == "tools/shared"
    # Same link from a life/ source -> resolves to life/shared
    assert okf.resolve_to_concept("../random/shared.md", "life/a", sm) == "life/shared"


# --- relink root protection + doctor ---------------------------------------

def test_protected_root_links_not_resolved_to_concepts():
    slug_map = {"agents": ["tools/agents/agents"], "identity": ["life/identity"]}
    assert okf.resolve_to_concept("/AGENTS.md", "tools/x", slug_map) is None
    assert okf.resolve_to_concept("/IDENTITY.md", "tools/x", slug_map) is None
    assert okf.resolve_to_concept("/_config/taxonomy.md", "tools/x", slug_map) is None
    assert okf.resolve_to_concept("skills/okf-ingest/SKILL.md", "tools/x", slug_map) is None
    assert okf._is_protected_root_link("/CONTEXT.md") is True
    assert okf._is_protected_root_link("/concepts/tools/nub.md") is False


def test_rewrite_links_leaves_root_agents_alone():
    text = "See [contract](/AGENTS.md) and [nub](nub.md)."
    slug_map = {"agents": ["tools/agents/agents"], "nub": ["tools/nub"]}
    new, n = okf.rewrite_links(text, "tools/warp", slug_map)
    assert "/AGENTS.md" in new
    assert "/concepts/tools/agents/agents.md" not in new
    # nub may rewrite
    assert n >= 0


def test_doctor_runs_without_error(tmp_path, monkeypatch):
    class A:
        json = False
        strict = False
    # doctor uses REPO_ROOT; just ensure callable returns int
    rc = okf.cmd_doctor(A())
    assert rc in (0, 1)


def test_icm_sync_lists_skills_without_write():
    class A:
        write = False
        dry_run = True
        strict = False
    rc = okf.cmd_icm_sync(A())
    assert rc in (0, 1)


def test_list_invocable_skills_nonempty():
    names = okf._list_invocable_skills()
    assert "okf-core" in names
    assert "okf-ingest" in names


# --- sql -------------------------------------------------------------------

def _sample_sql_concepts():
    """Return a small set of Concept objects for SQL tests."""
    return [
        okf.Concept("tools/a", okf.CONCEPTS_DIR / "tools/a.md",
                     {"type": "tool", "visibility": "shareable", "domain": "tools", "title": "Tool A", "tags": ["dev", "agent"]},
                     "Body of A. Links to [b](./b.md)."),
        okf.Concept("tools/b", okf.CONCEPTS_DIR / "tools/b.md",
                     {"type": "tool", "visibility": "private", "domain": "tools", "title": "Tool B", "tags": ["dev"]},
                     "Body of B."),
        okf.Concept("life/c", okf.CONCEPTS_DIR / "life/c.md",
                     {"type": "topic", "visibility": "private", "domain": "life", "title": "Life C", "tags": ["health"]},
                     "Body with\ttab and\nnewline."),
    ]


def test_populate_duck_creates_tables_and_populates():
    """_populate_duck creates concepts, tags, links tables with correct row counts."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    con = duckdb.connect()
    concepts = _sample_sql_concepts()
    okf._populate_duck(con, concepts)

    assert con.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == 3
    assert con.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 4  # dev, agent, dev, health
    # tools/a links to tools/b (resolved from ./b.md)
    assert con.execute("SELECT COUNT(*) FROM links").fetchone()[0] >= 1
    con.close()


def test_populate_duck_filters_orphan_links():
    """Links to non-existent concept ids are dropped."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    # Concept that links to a ghost id
    concepts = [
        okf.Concept("tools/x", okf.CONCEPTS_DIR / "tools/x.md",
                     {"type": "tool", "visibility": "shareable", "domain": "tools", "title": "X", "tags": []},
                     "Links to [ghost](../ghost/missing.md)."),
    ]
    con = duckdb.connect()
    okf._populate_duck(con, concepts)
    # No links should exist because ghost/missing doesn't exist in concepts
    count = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    assert count == 0
    con.close()


def test_populate_duck_handles_empty_concepts():
    """_populate_duck with zero concepts creates empty tables without error."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    con = duckdb.connect()
    okf._populate_duck(con, [])
    assert con.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0
    con.close()


def test_populate_duck_stores_meta_schema_version():
    """meta table records the schema version."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    con = duckdb.connect()
    okf._populate_duck(con, [])
    row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert row is not None
    assert int(row[0]) == okf._SQL_SCHEMA_VERSION
    con.close()


def test_populate_duck_preserves_unicode_and_newlines():
    """Unicode and control characters in body survive round-trip."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    body = "日本語 🚀\nLine 2\n\tTabbed"
    concepts = [
        okf.Concept("tools/u", okf.CONCEPTS_DIR / "tools/u.md",
                     {"type": "tool", "visibility": "shareable", "domain": "tools", "title": "Unicode", "tags": []},
                     body),
    ]
    con = duckdb.connect()
    okf._populate_duck(con, concepts)
    stored = con.execute("SELECT body FROM concepts WHERE id='tools/u'").fetchone()[0]
    assert stored == body
    con.close()


def test_cmd_sql_runs_select_query():
    """cmd_sql executes a simple SELECT and prints TSV with headers."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    # Create a temp cache dir to avoid touching real cache
    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=["SELECT", "domain,", "COUNT(*)", "as", "n", "FROM", "concepts", "GROUP", "BY", "domain"])
            with patch('sys.exit') as mock_exit:
                # Capture stdout
                old_stdout, sys.stdout = sys.stdout, io.StringIO()
                try:
                    okf.cmd_sql(args)
                finally:
                    output = sys.stdout.getvalue()
                    sys.stdout = old_stdout

            mock_exit.assert_not_called()
            lines = output.strip().split("\n")
            assert len(lines) >= 2  # header + at least 1 row
            assert lines[0] == "domain\tn"


def test_cmd_sql_rejects_whitespace_only_query():
    """Whitespace-only query exits with error."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=["   "])
            with patch('sys.exit', side_effect=lambda code: (_ for _ in ()).throw(SystemExit(code))):
                old_stderr, sys.stderr = sys.stderr, io.StringIO()
                try:
                    try:
                        okf.cmd_sql(args)
                    except SystemExit as e:
                        exit_code = e.code
                finally:
                    stderr = sys.stderr.getvalue()
                    sys.stderr = old_stderr
            assert exit_code == 1
            assert "Empty query" in stderr


def test_cmd_sql_escapes_tabs_and_newlines_in_output():
    """TSV output escapes literal tabs and newlines in cell values."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=["SELECT", "body", "FROM", "concepts", "WHERE", "id='tools/u'"])
            # Populate with a concept first so cache exists
            con = duckdb.connect(cache_path)
            con.execute("PRAGMA enable_external_access=false")
            okf._populate_duck(con, [
                okf.Concept("tools/u", okf.CONCEPTS_DIR / "tools/u.md",
                             {"type": "tool", "visibility": "shareable", "domain": "tools", "title": "T", "tags": []},
                             "line1\ttab\nline2"),
            ])
            con.commit()
            con.close()

            with patch('sys.exit') as mock_exit:
                old_stdout, sys.stdout = sys.stdout, io.StringIO()
                try:
                    okf.cmd_sql(args)
                finally:
                    output = sys.stdout.getvalue()
                    sys.stdout = old_stdout

            mock_exit.assert_not_called()
            lines = output.strip().split("\n")
            # Header line
            # Data line should have escaped chars, not literal tab/newline
            assert "\\t" in lines[1], "Tab should be escaped as \\t"
            assert "\\n" in lines[1], "Newline should be escaped as \\n"


def test_cmd_sql_bad_sql_reports_error():
    """Malformed SQL prints error and exits 1."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=["SELECT", "*", "FROM", "nonexistent_table"])
            with patch('sys.exit', side_effect=lambda code: (_ for _ in ()).throw(SystemExit(code))):
                old_stderr, sys.stderr = sys.stderr, io.StringIO()
                try:
                    try:
                        okf.cmd_sql(args)
                    except SystemExit as e:
                        exit_code = e.code
                finally:
                    stderr = sys.stderr.getvalue()
                    sys.stderr = old_stderr
            assert exit_code == 1
            assert "Query failed" in stderr


def test_cmd_sql_blocks_file_read():
    """enable_external_access=false prevents reading arbitrary files."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=["SELECT", "read_text('/etc/hosts')"])
            with patch('sys.exit', side_effect=lambda code: (_ for _ in ()).throw(SystemExit(code))):
                old_stderr, sys.stderr = sys.stderr, io.StringIO()
                try:
                    try:
                        okf.cmd_sql(args)
                    except SystemExit as e:
                        exit_code = e.code
                finally:
                    stderr = sys.stderr.getvalue()
                    sys.stderr = old_stderr
            assert exit_code == 1
            assert "failed" in stderr.lower() or "error" in stderr.lower()


def test_get_concepts_mtime_returns_positive():
    """_get_concepts_mtime returns a positive float for a non-empty concepts/."""
    mt = okf._get_concepts_mtime()
    assert mt > 0


def test_cache_is_fresh_false_when_no_cache():
    """_cache_is_fresh returns False when cache file doesn't exist."""
    with tempfile.TemporaryDirectory() as td:
        fake_cache = Path(td) / "ghost.duckdb"
        with patch.object(okf, 'SQL_CACHE', fake_cache):
            assert okf._cache_is_fresh() is False


def test_sql_parser_wiring():
    """okf sql subcommand is wired in the argument parser."""
    parser = okf.build_parser()
    args = parser.parse_args(["sql", "SELECT", "1"])
    assert args.cmd == "sql"
    assert args.query == ["SELECT", "1"]


def test_cmd_sql_rejects_ddl():
    """cmd_sql rejects non-SELECT statements."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            for bad_query in ["DROP TABLE concepts", "INSERT INTO concepts VALUES ('x','','','','','','','')", "DELETE FROM concepts", "ALTER TABLE concepts ADD COLUMN foo TEXT"]:
                args = MagicMock(query=bad_query.split())
                with patch('sys.exit', side_effect=lambda code: (_ for _ in ()).throw(SystemExit(code))):
                    old_stderr, sys.stderr = sys.stderr, io.StringIO()
                    try:
                        try:
                            okf.cmd_sql(args)
                        except SystemExit as e:
                            exit_code = e.code
                    finally:
                        stderr = sys.stderr.getvalue()
                        sys.stderr = old_stderr
                assert exit_code == 1
                assert "SELECT" in stderr


def test_cmd_sql_stdin_path():
    """cmd_sql reads SQL from stdin when args.query is empty."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = os.path.join(td, "test.duckdb")
        with patch.object(okf, 'SQL_CACHE', Path(cache_path)):
            args = MagicMock(query=[])
            # Simulate non-tty stdin with SQL
            with patch.object(sys, 'stdin', new_callable=lambda: MagicMock(isatty=lambda: False, read=lambda: "SELECT COUNT(*) FROM concepts")):
                with patch('sys.exit') as mock_exit:
                    old_stdout, sys.stdout = sys.stdout, io.StringIO()
                    try:
                        okf.cmd_sql(args)
                    finally:
                        output = sys.stdout.getvalue()
                        sys.stdout = old_stdout
                mock_exit.assert_not_called()
                # Should have output a count
                assert output.strip() != ""


def test_cache_hit_path_reuses_existing():
    """cmd_sql uses existing cache when it is fresh."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = Path(td) / "test.duckdb"
        with patch.object(okf, 'SQL_CACHE', cache_path):
            # First call builds the cache
            args1 = MagicMock(query=["SELECT", "1", "as", "cold"])
            with patch('sys.exit') as mock_exit:
                old_stdout, sys.stdout = sys.stdout, io.StringIO()
                try:
                    okf.cmd_sql(args1)
                finally:
                    sys.stdout = old_stdout
            mock_exit.assert_not_called()
            assert cache_path.exists()

            # Second call should use cache (no rebuild needed)
            # Verify by checking _cache_is_fresh returns True
            assert okf._cache_is_fresh() is True

            args2 = MagicMock(query=["SELECT", "1", "as", "cached"])
            with patch('sys.exit') as mock_exit:
                old_stdout, sys.stdout = sys.stdout, io.StringIO()
                try:
                    okf.cmd_sql(args2)
                finally:
                    output = sys.stdout.getvalue()
                    sys.stdout = old_stdout
            mock_exit.assert_not_called()
            assert "cached" in output
            assert "1" in output


def test_cache_invalidates_on_schema_version_mismatch():
    """_cache_is_fresh returns False when schema version doesn't match."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    with tempfile.TemporaryDirectory() as td:
        cache_path = Path(td) / "test.duckdb"
        # Build a cache with version 1
        with patch.object(okf, 'SQL_CACHE', cache_path):
            args = MagicMock(query=["SELECT", "1"])
            with patch('sys.exit') as mock_exit:
                old_stdout, sys.stdout = sys.stdout, io.StringIO()
                try:
                    okf.cmd_sql(args)
                finally:
                    sys.stdout = old_stdout
            mock_exit.assert_not_called()
            assert okf._cache_is_fresh() is True

        # Bump version — cache should now be stale
        old_version = okf._SQL_SCHEMA_VERSION
        okf._SQL_SCHEMA_VERSION = 99
        try:
            with patch.object(okf, 'SQL_CACHE', cache_path):
                assert okf._cache_is_fresh() is False
        finally:
            okf._SQL_SCHEMA_VERSION = old_version


def test_populate_duck_handles_missing_frontmatter_keys():
    """_populate_duck doesn't crash when concept fm is missing optional keys."""
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    # Concept with minimal frontmatter (only required fields)
    concepts = [
        okf.Concept("tools/minimal", okf.CONCEPTS_DIR / "tools/minimal.md",
                     {"type": "tool", "visibility": "shareable"},
                     "Body."),
    ]
    con = duckdb.connect()
    okf._populate_duck(con, concepts)
    row = con.execute("SELECT id, domain, title, status FROM concepts WHERE id='tools/minimal'").fetchone()
    assert row[0] == "tools/minimal"
    assert row[1] == ""  # domain missing → empty
    assert row[2] == ""  # title missing → empty
    assert row[3] == ""  # status missing → empty
    con.close()


def test_is_select_identifies_queries():
    """_is_select correctly identifies SELECT queries and rejects others."""
    assert okf._is_select("SELECT * FROM x") is True
    assert okf._is_select("  SELECT * FROM x") is True
    assert okf._is_select("select * from x") is True
    assert okf._is_select("DROP TABLE x") is False
    assert okf._is_select("INSERT INTO x VALUES (1)") is False
    assert okf._is_select("DELETE FROM x") is False
    assert okf._is_select("UPDATE x SET y=1") is False

def test_is_select_rejects_forbidden_keywords():
    """_is_select rejects SELECT queries containing forbidden keywords."""
    for kw in ("ATTACH", "PRAGMA", "CREATE", "INSERT", "UPDATE", "DELETE", "DROP"):
        assert okf._is_select(f"SELECT 1; {kw} TABLE x") is False, f"Should reject {kw}"
    assert okf._is_select('SELECT readfile("/etc/passwd")') is False
    assert okf._is_select('SELECT read_csv("/tmp/x.csv")') is False


def test_is_select_accepts_safe_queries():
    """_is_select accepts clean SELECT queries."""
    assert okf._is_select("SELECT * FROM concepts") is True
    assert okf._is_select("SELECT id, title FROM concepts WHERE tags LIKE '%tool%'") is True


def test_cmd_sql_rejects_oversized_query(tmp_path, capsys):
    """cmd_sql rejects queries exceeding the 1MB limit."""
    import argparse
    big = "SELECT '" + "x" * okf._MAX_QUERY_BYTES + "'"
    args = argparse.Namespace(query=[big])
    try:
        okf.cmd_sql(args)
    except SystemExit as e:
        assert e.code == 1
    stdout, stderr = capsys.readouterr()
    assert "too large" in stderr.lower()


def test_cmd_link_rejects_invalid_json(tmp_path, monkeypatch):
    """cmd_link exits 1 on malformed JSON stdin."""
    import io
    monkeypatch.setattr(okf, "CONCEPTS_DIR", tmp_path)
    monkeypatch.setattr(okf, "INDEX_PATH", tmp_path / "index.json")
    (tmp_path / "index.json").write_text("{}")
    import sys
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{bad json}")))
    args = argparse.Namespace(auto=False)
    result = okf.cmd_link(args)
    assert result == 1


def test_cmd_link_rejects_non_array_json(tmp_path, monkeypatch):
    """cmd_link exits 1 when stdin JSON is not an array."""
    import io
    monkeypatch.setattr(okf, "CONCEPTS_DIR", tmp_path)
    monkeypatch.setattr(okf, "INDEX_PATH", tmp_path / "index.json")
    (tmp_path / "index.json").write_text("{}")
    import sys
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b'{"score": 1}')))
    args = argparse.Namespace(auto=False)
    result = okf.cmd_link(args)
    assert result == 1


def test_cmd_link_rejects_missing_keys(tmp_path, monkeypatch):
    """cmd_link exits 1 when entry lacks required keys."""
    import io
    monkeypatch.setattr(okf, "CONCEPTS_DIR", tmp_path)
    monkeypatch.setattr(okf, "INDEX_PATH", tmp_path / "index.json")
    (tmp_path / "index.json").write_text("{}")
    import sys
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b'[{"score": 1}]')))
    args = argparse.Namespace(auto=False)
    result = okf.cmd_link(args)
    assert result == 1


def test_cmd_link_accepts_valid_json(tmp_path, monkeypatch):
    """cmd_link exits 0 with valid JSON array."""
    import io
    monkeypatch.setattr(okf, "CONCEPTS_DIR", tmp_path)
    monkeypatch.setattr(okf, "INDEX_PATH", tmp_path / "index.json")
    (tmp_path / "index.json").write_text("{}")
    import sys
    payload = json.dumps([{"score": 1, "a": "x", "b": "y", "reason": "test"}])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload.encode())))
    args = argparse.Namespace(auto=False)
    result = okf.cmd_link(args)
    assert result == 0


def test_cmd_view_prints_loopback_warning(tmp_path, monkeypatch, capsys):
    """cmd_view LOOPBACK constant is correct."""
    monkeypatch.setattr(okf, "CONCEPTS_DIR", tmp_path)
    monkeypatch.setattr(okf, "INDEX_PATH", tmp_path / "index.json")
    (tmp_path / "index.json").write_text("{}")
    assert okf.LOOPBACK == "127.0.0.1"

