#!/usr/bin/env python3
"""okf — tooling for the OKF brain corpus.

Subcommands:
  index        Walk concepts/, build tools/index.json, and regenerate provenance/map.{json,md}.
  search       Rank concepts for a query (BM25) with optional --visibility/--type/--domain filters.
  lint         Report missing required frontmatter, broken links, orphans, duplicates, privacy issues.
  relink       Rewrite intra-corpus markdown links to canonical /concepts/<id>.md paths.
  sql          Run ad-hoc SQL queries over the corpus (requires: pip install "okf-tools[sql]").
  doctor       Agent-surface integrity (ICM files, AGENTS dup, AAAK parity, routing).
  icm-sync     Diff skills/ vs CONTEXT routing; optional --write.
  view         Build the index, serve locally, and open the graph viewer in a browser.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# --- repo layout -----------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
CONCEPTS_DIR = REPO_ROOT / "concepts"
INDEX_PATH = TOOLS_DIR / "index.json"
PROV_JSON = REPO_ROOT / "provenance" / "map.json"
PROV_MD = REPO_ROOT / "provenance" / "map.md"
SQL_CACHE = TOOLS_DIR / "sql_cache.duckdb"

REQUIRED_FIELDS = ("type", "visibility")
VALID_VISIBILITY = ("private", "shareable")
PERSONAL_DOMAINS = {"life", "people", "orgs", "documents", "work"}  # default private (D-015)
LOOPBACK = "127.0.0.1"  # local-only bind host for `okf view`

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FM_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
_FM_ITEM_RE = re.compile(r"^\s*-\s+(.*)$")


# --- frontmatter parsing (minimal YAML subset) -----------------------------

def split_frontmatter(text: str):
    """Return (frontmatter_dict, body_str). Empty dict if no frontmatter."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm = parse_frontmatter("\n".join(lines[1:end]))
    body = "\n".join(lines[end + 1:])
    return fm, body


def _strip_scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value


def parse_frontmatter(block: str) -> dict:
    """Parse the small YAML subset used by OKF concept frontmatter.

    Supports scalars, inline lists ([a, b]), and block lists (- item).
    Full-line comments (starting with #) and blank lines are ignored.
    """
    data: dict = {}
    last_key = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = _FM_ITEM_RE.match(raw)
        if item and last_key is not None:
            data.setdefault(last_key, [])
            if not isinstance(data[last_key], list):
                data[last_key] = []
            data[last_key].append(_strip_scalar(item.group(1)))
            continue
        m = _FM_KEY_RE.match(raw)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        last_key = key
        if rest == "":
            data[key] = None  # may become a block list on following lines
        elif rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            data[key] = [_strip_scalar(x) for x in inner.split(",")] if inner else []
        else:
            data[key] = _strip_scalar(rest)
    return data


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [value]


def tokenize(text: str):
    return _TOKEN_RE.findall((text or "").lower())


# --- concept loading -------------------------------------------------------

class Concept:
    __slots__ = ("id", "path", "fm", "body", "links", "tf", "length")

    def __init__(self, cid, path, fm, body):
        self.id = cid
        self.path = path
        self.fm = fm
        self.body = body
        self.links = extract_links(body, cid)
        terms = tokenize(" ".join([
            str(fm.get("title") or ""),
            str(fm.get("description") or ""),
            " ".join(as_list(fm.get("tags"))),
            body,
        ]))
        tf: dict = {}
        for t in terms:
            if len(t) < 2:
                continue
            tf[t] = tf.get(t, 0) + 1
        self.tf = tf
        self.length = sum(tf.values())


def concept_id_from_path(path: Path) -> str:
    return path.relative_to(CONCEPTS_DIR).with_suffix("").as_posix()


def extract_links(body: str, source_id: str):
    """Return a sorted list of concept ids this body links to (best-effort)."""
    out = set()
    for target in _LINK_RE.findall(body):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part = target.split("#", 1)[0].split("?", 1)[0]
        if not path_part.endswith(".md"):
            continue
        # Collapse accidental /concepts/id.md.md links
        while path_part.endswith(".md.md"):
            path_part = path_part[:-3]
        if path_part.startswith("/concepts/"):
            cid = path_part[len("/concepts/"):-len(".md")]
        elif path_part.startswith("concepts/"):
            cid = path_part[len("concepts/"):-len(".md")]
        elif path_part.startswith("/"):
            continue  # bundle-relative but outside concepts/
        else:
            # relative to the source concept's directory
            base = (CONCEPTS_DIR / source_id).parent
            resolved = (base / path_part).resolve()
            try:
                cid = resolved.relative_to(CONCEPTS_DIR).with_suffix("").as_posix()
            except ValueError:
                continue
        # Only collapse known bad mid-path doubles (e.g. tools/agents/agents/foo).
        # Do NOT collapse domain hubs (tools/tools) or leaf hubs (learning/topic/topic).
        if "/agents/agents/" in cid:
            alt = cid.replace("/agents/agents/", "/agents/")
            cid = alt
        out.add(cid)
    return sorted(out)


def load_concepts():
    concepts = []
    if not CONCEPTS_DIR.exists():
        return concepts
    for path in sorted(CONCEPTS_DIR.rglob("*.md")):
        if path.name in ("index.md", "log.md", "_template.md"):
            continue  # reserved filenames — not concept documents
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        concepts.append(Concept(concept_id_from_path(path), path, fm, body))
    return concepts


# --- index -----------------------------------------------------------------

def build_index(concepts):
    df: dict = {}
    docs = []
    for c in concepts:
        for term in c.tf:
            df[term] = df.get(term, 0) + 1
        docs.append({
            "id": c.id,
            "path": c.path.relative_to(REPO_ROOT).as_posix(),
            "type": c.fm.get("type"),
            "visibility": c.fm.get("visibility"),
            "domain": c.fm.get("domain"),
            "title": c.fm.get("title") or c.id.rsplit("/", 1)[-1],
            "description": c.fm.get("description") or "",
            "tags": as_list(c.fm.get("tags")),
            "source": as_list(c.fm.get("source")),
            "links": c.links,
            "tf": c.tf,
            "length": c.length,
        })
    total_len = sum(d["length"] for d in docs)
    avgdl = (total_len / len(docs)) if docs else 0.0
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(docs),
        "avgdl": avgdl,
        "df": df,
        "concepts": docs,
    }


def write_provenance(concepts):
    entries = {}
    for c in concepts:
        entries[c.id] = {
            "title": c.fm.get("title") or c.id.rsplit("/", 1)[-1],
            "sources": as_list(c.fm.get("source")),
        }
    PROV_JSON.write_text(json.dumps({
        "version": "1",
        "description": ("Concept -> source provenance. GENERATED by "
                        "`python3 tools/okf.py index` from each concept's `source` "
                        "frontmatter. Do not edit by hand; edit the concept's frontmatter instead."),
        "concepts": entries,
    }, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Provenance Map",
        "",
        ("**GENERATED** by `python3 tools/okf.py index` from each concept's `source` "
         "frontmatter. Do not edit by hand — edit the concept's frontmatter instead, then "
         "re-run the indexer."),
        "",
        ("Each row maps a concept to its source(s). Source refs may be historical "
         "origin paths (e.g. `origin-1:`, `origin-2:`), URLs (`https://...`), or `self:` for "
         "vault-synthesized content. Historical snapshots live under `raw/`."),
        "",
        "## Concepts",
    ]
    if not entries:
        lines.append("(none yet — populated on first ingest)")
    else:
        for cid in sorted(entries):
            srcs = entries[cid]["sources"]
            srcs_str = ", ".join(f"`{s}`" for s in srcs) if srcs else "_(no provenance recorded)_"
            lines.append(f"- [{entries[cid]['title']}](/concepts/{cid}.md) — {srcs_str}")
    PROV_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_domain_indexes(concepts):
    """Generate per-domain index.md files under concepts/<domain>/index.md."""
    by_domain: dict = {}
    for c in concepts:
        d = c.fm.get("domain") or "uncategorized"
        by_domain.setdefault(d, []).append(c)
    for domain, dconcepts in sorted(by_domain.items()):
        dpath = CONCEPTS_DIR / domain / "index.md"
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dconcepts.sort(key=lambda c: c.fm.get("title") or c.id.rsplit("/", 1)[-1])
        lines = [f"# {domain.capitalize()}", ""]
        for c in dconcepts:
            title = c.fm.get("title") or c.id.rsplit("/", 1)[-1]
            desc = c.fm.get("description") or ""
            lines.append(f"- [{title}](/{c.path.relative_to(REPO_ROOT).as_posix()}) — {desc}")
        dpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Domain indexes -> {len(by_domain)} files under concepts/*/index.md")

def cmd_index(args):
    concepts = load_concepts()
    index = build_index(concepts)
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    write_provenance(concepts)
    write_domain_indexes(concepts)
    print(f"Indexed {index['count']} concept(s) -> {INDEX_PATH.relative_to(REPO_ROOT)}")
    print(f"Provenance -> {PROV_JSON.relative_to(REPO_ROOT)}, {PROV_MD.relative_to(REPO_ROOT)}")
    return 0


# --- search ----------------------------------------------------------------

def load_index():
    if not INDEX_PATH.exists():
        return build_index(load_concepts())
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def bm25_search(index, query, k1=1.5, b=0.75):
    q_terms = [t for t in tokenize(query) if len(t) >= 2]
    n = index["count"] or 1
    avgdl = index["avgdl"] or 1.0
    df = index["df"]
    results = []
    for doc in index["concepts"]:
        score = 0.0
        dl = doc["length"] or 1
        for term in q_terms:
            f = doc["tf"].get(term, 0)
            if f == 0:
                continue
            idf = math.log(1 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        if score > 0:
            results.append((score, doc))
    results.sort(key=lambda x: x[0], reverse=True)
    return results


def apply_filters(results, visibility=None, type=None, domain=None, limit=10):
    out = []
    for score, doc in results:
        if visibility and doc.get("visibility") != visibility:
            continue
        if type and doc.get("type") != type:
            continue
        if domain and doc.get("domain") != domain:
            continue
        out.append((score, doc))
        if len(out) >= limit:
            break
    return out


def cmd_search(args):
    index = load_index()
    results = bm25_search(index, args.query)
    out = apply_filters(results, args.visibility, args.type, args.domain, args.limit)
    if args.json:
        print(json.dumps([
            {"score": round(s, 4), "id": d["id"], "path": d["path"],
             "title": d["title"], "type": d["type"], "visibility": d["visibility"]}
            for s, d in out
        ], indent=2))
        return 0
    if not out:
        print("No matches.")
        return 0
    for score, doc in out:
        print(f"{score:6.3f}  {doc['title']}  [{doc.get('type')}/{doc.get('visibility')}]")
        print(f"        {doc['path']}")
    return 0


# --- lint ------------------------------------------------------------------

def lint_concepts(concepts):
    findings = []
    ids = {c.id for c in concepts}
    inbound: dict = {c.id: 0 for c in concepts}
    titles: dict = {}

    for c in concepts:
        for field in REQUIRED_FIELDS:
            if not c.fm.get(field):
                findings.append({"level": "error", "concept": c.id,
                                 "kind": "missing-field", "detail": f"missing required `{field}`"})
        vis = c.fm.get("visibility")
        if vis and vis not in VALID_VISIBILITY:
            findings.append({"level": "error", "concept": c.id, "kind": "bad-visibility",
                             "detail": f"visibility `{vis}` not in {VALID_VISIBILITY}"})
        # privacy: personal-domain concept marked shareable — warn so override is confirmed
        domain = c.fm.get("domain")
        if domain in PERSONAL_DOMAINS and vis == "shareable":
            findings.append({"level": "warn", "concept": c.id, "kind": "privacy",
                             "detail": f"personal domain `{domain}` is shareable — confirm override is intentional"})
        title = (c.fm.get("title") or "").strip().lower()
        if title:
            titles.setdefault(title, []).append(c.id)
        for target in c.links:
            if target in ids:
                inbound[target] += 1
            else:
                findings.append({"level": "warn", "concept": c.id, "kind": "broken-link",
                                 "detail": f"links to missing concept `{target}`"})

    for cid, count in inbound.items():
        if count == 0:
            findings.append({"level": "info", "concept": cid, "kind": "orphan",
                             "detail": "no inbound links"})
    for title, owners in titles.items():
        if len(owners) > 1:
            findings.append({"level": "warn", "concept": ", ".join(sorted(owners)),
                             "kind": "duplicate", "detail": f"shared title '{title}'"})
    return findings


def cmd_lint(args):
    concepts = load_concepts()
    findings = lint_concepts(concepts)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        if not findings:
            print(f"lint: {len(concepts)} concept(s), no findings.")
        else:
            order = {"error": 0, "warn": 1, "info": 2}
            for f in sorted(findings, key=lambda x: order.get(x["level"], 9)):
                print(f"[{f['level']:5}] {f['kind']}: {f['concept']} — {f['detail']}")
            counts = {}
            for f in findings:
                counts[f["level"]] = counts.get(f["level"], 0) + 1
            print(f"\n{len(concepts)} concept(s); "
                  + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    # Never hard-fail unless --strict and there are errors.
    if args.strict and any(f["level"] == "error" for f in findings):
        return 1
    return 0


# --- view (local server + browser) -----------------------------------------

def viewer_url(port):
    return f"http://{LOOPBACK}:{port}/tools/viewer.html"


def cmd_view(args):
    """Build the index, serve the repo locally, and open the graph viewer."""
    import functools
    import http.server
    import webbrowser

    if not args.no_index:
        concepts = load_concepts()
        index = build_index(concepts)
        INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        write_provenance(concepts)
        print(f"Indexed {index['count']} concept(s).")

    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):  # silence per-request logging
            pass

    handler = functools.partial(_QuietHandler, directory=str(REPO_ROOT))
    try:
        httpd = http.server.ThreadingHTTPServer((LOOPBACK, args.port), handler)
    except OSError:
        # Requested port busy/unavailable -> let the OS pick a free one.
        httpd = http.server.ThreadingHTTPServer((LOOPBACK, 0), handler)
    port = httpd.server_address[1]
    url = viewer_url(port)
    print(f"OKF graph viewer: {url}")
    print("Press Ctrl+C to stop.")
    print(f"Note: serving on loopback ({LOOPBACK}) only — not exposed to the network.",
          file=sys.stderr)
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0

# --- suggest-links (find missing semantic cross-links) ---------------------


def _tag_set(fm: dict) -> set:
    """Extract lowercase tag set from frontmatter."""
    return {t.strip().lower() for t in as_list(fm.get("tags")) if t.strip()}


def suggest_links(index, max_pairs: int = 100, min_tag_overlap: int = 2, min_score: float = 0.5, concept_id: str = None):
    """Find concept pairs that should probably be linked but aren't.
    
    When concept_id is set, only returns pairs involving that concept (fast, ingest-time use).
    When concept_id is None, scans all orphans + tag pairs (vault-wide audit).
    """
    concepts = {d["id"]: d for d in index["concepts"]}
    ids = set(concepts.keys())
    
    if concept_id and concept_id not in concepts:
        return []
    
    # Build existing-link set for quick lookup (undirected)
    existing = set()
    for d in index["concepts"]:
        for t in d["links"]:
            if t in ids:
                pair = tuple(sorted([d["id"], t]))
                existing.add(pair)
    
    # Build tag inverted index (skip in scoped mode — we iterate directly instead)
    tag_index: dict = {}
    if not concept_id:
        for cid, d in concepts.items():
            for tag in _tag_set(d):
                tag_index.setdefault(tag, []).append(cid)
    
    # Phase 1: tag-based candidate pairs
    tag_candidates: dict = {}  # (id_a, id_b) -> shared_tags
    if concept_id:
        # Scoped: iterate all concepts, check tag overlap with target
        target_tags = _tag_set(concepts[concept_id])
        for cid, d in concepts.items():
            if cid == concept_id:
                continue
            pair = tuple(sorted([concept_id, cid]))
            if pair in existing:
                continue
            shared = target_tags & _tag_set(d)
            if len(shared) >= min_tag_overlap:
                tag_candidates[pair] = shared
    else:
        for tag, cids in tag_index.items():
            if len(cids) < 2:
                continue
            for i in range(len(cids)):
                for j in range(i + 1, len(cids)):
                    pair = tuple(sorted([cids[i], cids[j]]))
                    if pair in existing:
                        continue
                    tag_candidates[pair] = tag_candidates.get(pair, set()) | {tag}
    # Filter out same-stem cross-domain duplicates (e.g. learning/skills/X ↔ tools/agents/X)
    def _slug_match(a: str, b: str) -> bool:
        return a.rsplit("/", 1)[-1] == b.rsplit("/", 1)[-1]
    
    scored: dict = {}  # pair -> (score, reason)
    
    # Score tag candidates
    for pair, shared_tags in tag_candidates.items():
        if len(shared_tags) < min_tag_overlap:
            continue
        id_a, id_b = pair
        if _slug_match(id_a, id_b):
            continue
        weight = len(shared_tags) * 10.0  # strong signal
        reason = f"tags: {', '.join(sorted(shared_tags))}"
        scored[pair] = (weight, reason)
    # Phase 2: BM25 cross-scoring
    # When concept_id set: score that concept against all others
    # When global: score orphans (0 inbound) against all others
    n = index["count"] or 1
    avgdl = index["avgdl"] or 1.0
    df = index["df"]
    k1, b = 1.5, 0.75
    
    def _make_query(d: dict) -> str:
        parts = []
        title = (d.get("title") or "").strip()
        desc = (d.get("description") or "").strip()
        if title:
            parts.append(title)
        if desc:
            parts.append(desc)
        parts.extend(_tag_set(d))
        return " ".join(parts)
    
    if concept_id:
        targets = {concept_id: _make_query(concepts[concept_id])}
    else:
        inbound = {cid: 0 for cid in ids}
        for d in index["concepts"]:
            for t in d["links"]:
                if t in ids:
                    inbound[t] += 1
        targets = {cid: _make_query(concepts[cid]) for cid in ids if inbound[cid] == 0}
    
    for target_id, query in targets.items():
        if not query.strip():
            continue
        q_terms = [t for t in tokenize(query) if len(t) >= 2]
        if not q_terms:
            continue
        
        for cid, d in concepts.items():
            if cid == target_id:
                continue
            pair = tuple(sorted([target_id, cid]))
            if pair in existing:
                continue
            if _slug_match(target_id, cid):
                continue
            
            score = 0.0
            dl = d["length"] or 1
            for term in q_terms:
                f = d["tf"].get(term, 0)
                if f == 0:
                    continue
                idf = math.log(1 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
                score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
            
            if score > min_score:
                pair_key = pair
                if pair_key not in scored or scored[pair_key][0] < score:
                    d_terms = set(d["tf"].keys())
                    q_set = set(q_terms)
                    shared = d_terms & q_set
                    reason = f"BM25: {score:.2f}; terms: {', '.join(sorted(shared)[:5])}"
                    scored[pair_key] = (score, reason)
    
    # Rank and return top N
    results = sorted(scored.items(), key=lambda x: -x[1][0])
    return [(score, id_a, id_b, reason) for (id_a, id_b), (score, reason) in results[:max_pairs]]


def cmd_suggest_links(args):
    """Suggest missing cross-links between concepts based on tags and BM25 similarity."""
    idx = load_index()
    pairs = suggest_links(
        idx,
        max_pairs=args.max,
        min_tag_overlap=args.min_tags,
        min_score=args.min_score,
        concept_id=getattr(args, "concept", None),
    )
    
    if not pairs:
        print("No candidate links found above thresholds.")
        return 0
    
    if args.json:
        out = [{"score": s, "a": a, "b": b, "reason": r} for s, a, b, r in pairs]
        print(json.dumps(out, indent=2))
    else:
        print(f"Top {len(pairs)} missing link candidates:")
        print()
        for rank, (score, id_a, id_b, reason) in enumerate(pairs, 1):
            print(f"{rank:3d}. score={score:.2f}")
            print(f"     {id_a}")
            print(f"     ↔ {id_b}")
            print(f"     {reason}")
            print()
    
    print(f"Hint: okf suggest-links --json | jq '.[].a' | xargs -I{{}} echo '{{}}' > /tmp/pairs.txt")
    return 0


# --- relink (canonicalize intra-corpus links) ------------------------------

_RELINK_RE = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\))")
# Original-structure path segment -> canonical domain (for disambiguating slugs).
DOMAIN_HINTS = {
    "ecosystem": "tools", "terminals": "tools", "orchestration": "tools",
    "governance": "tools", "execution-surfaces": "tools", "ai-coding-agents": "tools",
    "protocols": "tools", "tools": "tools",
    "specs": "specs", "skills": "skills", "learning": "learning",
    "topics": "life", "habits": "life", "goals": "life", "projects": "life",
    "resources": "learning", "life": "life",
    "people": "people", "organizations": "orgs", "orgs": "orgs",
    "documents": "documents",
}


def _slug(stem):
    return re.sub(r"[^a-z0-9]+", "-", stem.strip().lower()).strip("-")


def build_slug_map(concepts):
    """slug -> [concept_id, ...] (a slug may exist in more than one domain)."""
    m: dict = {}
    for c in concepts:
        m.setdefault(c.id.rsplit("/", 1)[-1], []).append(c.id)
    return m


# Repo-root / non-concept path prefixes that must never be rewritten to concepts/.
_ROOT_LINK_PREFIXES = (
    "/IDENTITY.md", "/CONTEXT.md", "/AGENTS.md", "/CLAUDE.md", "/GEMINI.md",
    "/index.md", "/log.md", "/decisions.md",     "/_config/", "/rules/", "/skills/", "/tools/", "/themes/", "/specs/",
    "/raw/", "/provenance/", "/inbox/",
)


def _is_protected_root_link(path: str) -> bool:
    """True for vault orientation/tooling paths that are not concept ids."""
    if not path:
        return False
    # Normalize: strip leading ./ and collapse
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    # Absolute-from-repo-root style
    if p.startswith("/"):
        if any(p == pref.rstrip("/") or p.startswith(pref) for pref in _ROOT_LINK_PREFIXES):
            return True
        # bare root files without leading path segments beyond one
        if p.count("/") == 1 and p.endswith(".md"):
            name = p[1:]
            if name in {
                "IDENTITY.md", "CONTEXT.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
                "index.md", "log.md", "decisions.md",             }:
                return True
        return False
    # relative link to root file from a concept (../ or multi-up) ending at known root files
    base = p.rsplit("/", 1)[-1]
    if base in {
        "IDENTITY.md", "CONTEXT.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
        "index.md", "log.md", "decisions.md",     }:
        # only protect if not clearly under concepts/
        if "concepts/" not in p:
            return True
    if p.startswith(("_config/", "rules/", "skills/", "tools/", "themes/", "specs/", "raw/", "provenance/", "inbox/")):
        return True
    return False


def resolve_to_concept(url, source_id, slug_map):
    """Map a markdown link URL to a canonical concept id, or None to leave it alone."""
    path = url.split("#", 1)[0].split("?", 1)[0]
    if not path or path.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if _is_protected_root_link(path):
        return None  # orientation / tooling paths — never map to concept slugs
    if not path.endswith(".md") or path.startswith("/concepts/"):
        return None  # not a concept link, or already canonical
    slug = _slug(path.rsplit("/", 1)[-1][:-3])
    cands = slug_map.get(slug)
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    # Disambiguate: domain hinted by the original path, else the source's domain.
    segs = [p.lower() for p in path.split("/") if p]
    hint = next((DOMAIN_HINTS[s] for s in segs if s in DOMAIN_HINTS), None)
    src_domain = source_id.split("/", 1)[0]
    by_hint = next((c for c in cands if c.split("/", 1)[0] == hint), None) if hint else None
    return by_hint or next((c for c in cands if c.split("/", 1)[0] == src_domain), None)

def rewrite_links(text, source_id, slug_map):
    """Rewrite resolvable [text](old.md) links to /concepts/<id>.md. Returns (new_text, count)."""
    count = [0]

    def repl(m):
        pre, url, post = m.group(1), m.group(2), m.group(3)
        # Split off fragment (#) and query (?) — preserve both in output.
        base, rest = (url.split("#", 1) + [""])[:2]
        query = ""
        if "?" in base:
            base, query = (base.split("?", 1) + [""])[:2]
        tid = resolve_to_concept(base, source_id, slug_map)
        if not tid or tid == source_id:
            return m.group(0)
        count[0] += 1
        suffix = ""
        if query:
            suffix += f"?{query}"
        if rest:
            suffix += f"#{rest}"
        return f"{pre}/concepts/{tid}.md{suffix}{post}"

    return _RELINK_RE.sub(repl, text), count[0]


def cmd_relink(args):
    concepts = load_concepts()
    slug_map = build_slug_map(concepts)
    total, files = 0, 0
    for c in concepts:
        text = c.path.read_text(encoding="utf-8")
        new, n = rewrite_links(text, c.id, slug_map)
        if n and new != text:
            total += n
            files += 1
            if not args.dry_run:
                c.path.write_text(new, encoding="utf-8")
    verb = "Would rewrite" if args.dry_run else "Rewrote"
    print(f"{verb} {total} link(s) across {files} file(s).")
    if not args.dry_run and total:
        print("Now run `okf index` then `okf lint`.")
    return 0



# --- link (apply suggested cross-links) ------------------------------------

def _append_related_links(path: Path, target_id: str, reason: str):
    """Append a related concept link under ## Related Concepts.
    Returns True if a link was added, False if it already existed."""
    target_path = CONCEPTS_DIR / (target_id + ".md")
    if not target_path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    target_link = f"/concepts/{target_id}.md"
    if target_link in text:
        return False
    title = target_id.rsplit("/", 1)[-1].replace("-", " ").title()
    link_line = f"- [{title}](/concepts/{target_id}.md) — {reason}"
    fm, body = split_frontmatter(text)
    if "## Related Concepts" in body:
        lines = body.split("\n")
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.strip() == "## Related Concepts":
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("## "):
                        insert_idx = j
                        break
                    if lines[j].strip() and not lines[j].strip().startswith("- "):
                        insert_idx = j
                        break
                else:
                    insert_idx = len(lines)
                break
        lines.insert(insert_idx, link_line)
        body = "\n".join(lines)
    else:
        body = body.rstrip("\n") + "\n\n## Related Concepts\n" + link_line + "\n"
    fm_end = text.index("---", 3) + 3
    path.write_text(text[:fm_end] + "\n" + body, encoding="utf-8")
    return True


def cmd_link(args):
    """Apply cross-links from suggest-links output or inline specs."""
    idx = load_index()
    if args.auto:
        pairs = suggest_links(idx, max_pairs=args.max, min_tag_overlap=args.min_tags, min_score=args.min_score, concept_id=getattr(args, "concept", None))
        noise_targets = {"tools/cc-switch"}
        pairs = [(s, a, b, r) for s, a, b, r in pairs if a not in noise_targets and b not in noise_targets]
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON on stdin: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, list):
            print(f"Error: expected a JSON array on stdin, got {type(data).__name__}", file=sys.stderr)
            return 1
        _LINK_KEYS = ("score", "a", "b", "reason")
        pairs = []
        for i, d in enumerate(data):
            missing = [k for k in _LINK_KEYS if k not in d]
            if missing:
                print(f"Error: entry {i} missing required keys: {', '.join(missing)}", file=sys.stderr)
                return 1
            pairs.append((d["score"], d["a"], d["b"], d["reason"]))
    applied = 0
    skipped = 0
    for score, id_a, id_b, reason in pairs:
        path_a = CONCEPTS_DIR / (id_a + ".md")
        path_b = CONCEPTS_DIR / (id_b + ".md")
        if not path_a.exists() or not path_b.exists():
            skipped += 1
            continue
        # Parse reason: "BM25: 108.58; terms: 3blue1brown, and, animation, by, for"
        # or "tags: math, physics, visualization"
        clean = reason.split(";", 1)[-1] if ";" in reason else reason
        clean = clean.split(":", 1)[-1].strip() if ":" in clean else clean.strip()
        tokens = [t.strip() for t in clean.split(",") if t.strip() and t.strip() not in ("and", "by", "the", "of", "for", "in", "as", "an", "a")]
        if tokens:
            prose = ", ".join(tokens[:5])
        else:
            prose = "related topic"
        added_a = _append_related_links(path_a, id_b, prose)
        added_b = _append_related_links(path_b, id_a, prose)
        if added_a or added_b:
            applied += 1
            if not args.quiet:
                print(f"linked: {id_a} ↔ {id_b}")
        else:
            skipped += 1
    print(f"Applied: {applied} pairs; Skipped: {skipped}")
    return 0

# --- sql (ad-hoc DuckDB analytical queries) --------------------------------

_SQL_SCHEMA_VERSION = 1


def _try_duckdb():
    try:
        import duckdb
        return duckdb
    except ImportError:
        print(
            "DuckDB is not installed. Install it with:\n"
            '  pip install "okf-tools[sql]"  # or: pip install duckdb',
            file=sys.stderr,
        )
        sys.exit(1)


def _get_concepts_mtime():
    """Return the max mtime of any file under concepts/."""
    best = 0.0
    for p in CONCEPTS_DIR.rglob("*.md"):
        try:
            mt = p.stat().st_mtime
            if mt > best:
                best = mt
        except OSError:
            pass
    return best


def _cache_is_fresh():
    """Check whether the cached DB exists and is at least as recent as concepts/."""
    if not SQL_CACHE.exists():
        return False
    try:
        cache_mtime = SQL_CACHE.stat().st_mtime
    except OSError:
        return False
    # Read schema version from cache
    duckdb = _try_duckdb()
    try:
        con = duckdb.connect(str(SQL_CACHE))
        con.execute("PRAGMA enable_external_access=false")
        row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        con.close()
        if row is None or int(row[0]) != _SQL_SCHEMA_VERSION:
            return False
        return cache_mtime >= _get_concepts_mtime()
    except Exception:
        return False


def _populate_duck(con, concepts):
    """Load concepts, tags, and links into DuckDB tables."""
    con.execute("""
        CREATE TABLE concepts (
            id         TEXT PRIMARY KEY,
            path       TEXT,
            domain     TEXT,
            type       TEXT,
            visibility TEXT,
            title      TEXT,
            status     TEXT,
            body       TEXT
        )
    """)
    con.execute("CREATE TABLE tags (concept_id TEXT, tag TEXT)")
    con.execute("CREATE TABLE links (source_id TEXT, target_id TEXT)")
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("INSERT INTO meta VALUES (?, ?)", ('schema_version', str(_SQL_SCHEMA_VERSION)))

    concept_rows = [
        (
            c.id,
            str(c.path),
            c.fm.get("domain", "") or "",
            c.fm.get("type", "") or "",
            c.fm.get("visibility", "") or "",
            c.fm.get("title", "") or "",
            c.fm.get("status", "") or "",
            c.body or "",
        )
        for c in concepts
    ]
    if concept_rows:
        con.executemany("INSERT INTO concepts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", concept_rows)

    tag_rows = [
        (c.id, t)
        for c in concepts
        for t in as_list(c.fm.get("tags"))
    ]
    if tag_rows:
        con.executemany("INSERT INTO tags VALUES (?, ?)", tag_rows)

    # Build a set of known ids for filtering orphans
    known_ids = {c.id for c in concepts}
    link_rows = [
        (c.id, t)
        for c in concepts
        for t in c.links
        if t in known_ids
    ]
    if link_rows:
        con.executemany("INSERT INTO links VALUES (?, ?)", link_rows)


def _atomic_cache_swap(temp_path: Path, target: Path):
    """Atomically replace target with temp_path, cleaning up WAL files."""
    # Clean up stale WAL/SHM files from previous crashed runs
    for ext in (".wal", "-shm"):
        wal = target.with_name(target.name + ext)
        if wal.exists():
            wal.unlink()
    # Move current target aside
    if target.exists():
        shutil.move(str(target), str(target) + ".old")
    # Move new cache into place
    shutil.move(str(temp_path), str(target))
    # Clean up old cache artifacts
    for ext in (".old", ".old.wal", ".old-shm"):
        old = target.with_name(target.name + ext)
        if old.exists():
            old.unlink(missing_ok=True)


_FORBIDDEN_SQL_RE = re.compile(
    r"\b(ATTACH|PRAGMA|CREATE|INSERT|UPDATE|DELETE|DROP|readfile|read_csv)\b",
    re.IGNORECASE,
)
_MAX_QUERY_BYTES = 1_048_576  # 1 MB


def _is_select(sql: str) -> bool:
    """Check if SQL is a safe read-only SELECT query."""
    if not sql.lstrip().upper().startswith("SELECT"):
        return False
    if _FORBIDDEN_SQL_RE.search(sql):
        return False
    return True


def cmd_sql(args):
    """Run an ad-hoc SQL query over the corpus using DuckDB."""
    duckdb = _try_duckdb()

    # Read query before opening any DB connection
    if args.query:
        sql = " ".join(args.query).strip()
    else:
        if sys.stdin.isatty():
            print("Read SQL from stdin (Ctrl-D to execute), or pass query as positional arg.", file=sys.stderr)
            sys.exit(1)
        sql = sys.stdin.read().strip()

    if not sql:
        print("Empty query.", file=sys.stderr)
        sys.exit(1)

    # Enforce query size limit
    if len(sql.encode("utf-8", errors="replace")) > _MAX_QUERY_BYTES:
        print(f"Query too large (limit {_MAX_QUERY_BYTES >> 20} MB).", file=sys.stderr)
        sys.exit(1)

    # Restrict to read-only queries
    if not _is_select(sql):
        print("Only SELECT queries are supported.", file=sys.stderr)
        sys.exit(1)

    # Use disk cache if fresh; otherwise rebuild
    if _cache_is_fresh():
        con = duckdb.connect(str(SQL_CACHE))
        con.execute("PRAGMA enable_external_access=false")
        con.execute("PRAGMA lock_configuration=true")
    else:
        # Rebuild into a temp file for atomic swap
        fd, tmp = tempfile.mkstemp(suffix=".duckdb", dir=str(SQL_CACHE.parent))
        os.close(fd)
        os.unlink(tmp)  # remove empty file so DuckDB can create it fresh
        temp_path = Path(tmp)
        try:
            con = duckdb.connect(str(temp_path))
            con.execute("PRAGMA enable_external_access=false")
            con.execute("PRAGMA lock_configuration=true")
            concepts = load_concepts()
            _populate_duck(con, concepts)
            con.commit()
            con.close()
            # Atomic swap: move temp → final location
            _atomic_cache_swap(temp_path, SQL_CACHE)
            # Re-open the final cache for querying
            con = duckdb.connect(str(SQL_CACHE))
            con.execute("PRAGMA enable_external_access=false")
            con.execute("PRAGMA lock_configuration=true")
        except Exception:
            # Clean up temp on failure
            if temp_path.exists():
                temp_path.unlink()
            raise

    # Escape tabs and newlines in values for TSV safety
    def _cell(v):
        s = str(v) if v is not None else ""
        return s.replace("\n", "\\n").replace("\t", "\\t")

    try:
        cur = con.execute(sql)
        headers = [desc[0] for desc in cur.description] if cur.description else []
        if headers:
            print("\t".join(headers))
        for row in cur.fetchall():
            print("\t".join(_cell(v) for v in row))
    except duckdb.Error as e:
        print(f"Query failed: {e}", file=sys.stderr)
        con.close()
        sys.exit(1)
    finally:
        con.close()

# --- doctor (agent-surface integrity) --------------------------------------

_FBC_MARKERS = (
    "full-body",
    "FULL-BODY",
    "FBC",
    "read-FULL",
    "read the full body",
    "full body",
)


def cmd_doctor(args):
    """Check ICM orientation, AGENTS uniqueness, skill routing, AAAK parity."""
    issues = []  # (level, code, msg)
    def err(code, msg):
        issues.append(("error", code, msg))
    def warn(code, msg):
        issues.append(("warn", code, msg))
    def info(code, msg):
        issues.append(("info", code, msg))

    # ICM files
    for name in ("IDENTITY.md", "CONTEXT.md"):
        if not (REPO_ROOT / name).exists():
            err("icm.missing", f"missing {name}")
    tax = REPO_ROOT / "_config" / "taxonomy.md"
    if not tax.exists():
        warn("tax.missing", "missing _config/taxonomy.md (P1 reference map)")

    agents = REPO_ROOT / "AGENTS.md"
    if agents.exists():
        at = agents.read_text(encoding="utf-8", errors="replace")
        n = at.count("# OKF Brain — Operating Contract")
        if n != 1:
            err("agents.dup", f"AGENTS.md Operating Contract heading count={n}, want 1")
        if "Only `skills/` and `inbox/`" in at or "Only `skills/` and `inbox/`" in at:
            err("agents.path", "AGENTS.md still has obsolete skills+inbox-only path rule")
        if "rules/path-access-control.md" not in at:
            warn("agents.path_ref", "AGENTS.md missing path-access-control reference")
    else:
        err("agents.missing", "missing AGENTS.md")

    # Skills vs CONTEXT routing
    skills_dir = REPO_ROOT / "skills"
    skill_names = []
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir()):
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue
            if (d / "SKILL.md").exists():
                skill_names.append(d.name)
    ctx_path = REPO_ROOT / "CONTEXT.md"
    ctx = ctx_path.read_text(encoding="utf-8", errors="replace") if ctx_path.exists() else ""
    for name in skill_names:
        if name not in ctx and f"skills/{name}" not in ctx:
            warn("route.skill", f"skill {name} not mentioned in CONTEXT.md routing")

    # AAAK dual-layer
    for name in skill_names:
        sm = skills_dir / name / "SKILL.md"
        sf = skills_dir / name / "SKILL.full.md"
        if not sm.exists():
            continue
        sm_t = sm.read_text(encoding="utf-8", errors="replace")
        if sf.exists():
            sf_t = sf.read_text(encoding="utf-8", errors="replace")
            def fm_field(t, key):
                if not t.startswith("---"):
                    return None
                lines = t.splitlines()
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        break
                    if line.startswith(f"{key}:"):
                        return line.split(":", 1)[1].strip().strip('"').strip("'")
                return None
            for key in ("name", "description"):
                a, b = fm_field(sm_t, key), fm_field(sf_t, key)
                if a != b:
                    err("aaak.fm", f"{name}: SKILL.md {key} != SKILL.full.md")
            if "FMT:AAAK" in sm_t or "lossy-agent-overlay" in sm_t:
                info("aaak.compressed", f"{name}: compressed overlay present")
            if name in ("okf-ingest", "okf-batch-ingest", "okf-ingest-channel", "okf-core"):
                if not any(m in sm_t for m in _FBC_MARKERS):
                    warn("aaak.fbc", f"{name}: compressed SKILL.md may lack FBC mandate markers")
        else:
            if name != "okf-icm-sync":
                info("aaak.no_full", f"{name}: no SKILL.full.md (ok if never compressed)")

    # Stale bad links — scan only skills concept subtree (fast path)
    skills_cx = REPO_ROOT / "concepts" / "skills"
    if skills_cx.exists():
        for path in skills_cx.rglob("*.md"):
            try:
                t = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if "okf-ingest.md-channel" in t:
                warn("stale.link", f"{path.relative_to(REPO_ROOT)}: okf-ingest.md-channel")

    # Summarize
    counts = {"error": 0, "warn": 0, "info": 0}
    for level, code, msg in issues:
        counts[level] = counts.get(level, 0) + 1
        if args.json:
            continue
        print(f"{level:5} {code}: {msg}")
    if args.json:
        print(json.dumps({"issues": [
            {"level": l, "code": c, "msg": m} for l, c, m in issues
        ], "counts": counts}, indent=2))
    else:
        print(f"doctor: {counts['error']} error(s), {counts['warn']} warning(s), {counts['info']} info")
    if args.strict and counts["error"]:
        return 1
    return 0



# --- icm-sync (refresh CONTEXT skill routing) -------------------------------

def _list_invocable_skills():
    skills_dir = REPO_ROOT / "skills"
    names = []
    if not skills_dir.exists():
        return names
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        if (d / "SKILL.md").exists():
            names.append(d.name)
    return names


def cmd_icm_sync(args):
    """Diff invocable skills vs CONTEXT.md; optionally append missing routing rows."""
    skills = _list_invocable_skills()
    ctx_path = REPO_ROOT / "CONTEXT.md"
    if not ctx_path.exists():
        print("error: CONTEXT.md missing", file=sys.stderr)
        return 1
    ctx = ctx_path.read_text(encoding="utf-8", errors="replace")
    missing = [s for s in skills if s not in ctx and f"skills/{s}" not in ctx]
    present = [s for s in skills if s in ctx or f"skills/{s}" in ctx]
    print(f"icm-sync: {len(skills)} skill(s); {len(present)} routed; {len(missing)} missing")
    for s in missing:
        print(f"  missing: {s}")
    if args.dry_run or not args.write:
        if missing and not args.write:
            print("hint: re-run with --write to append stub rows to CONTEXT.md")
        return 0 if not missing else (1 if args.strict else 0)
    if not missing:
        return 0
    # Append a small section before ## Do not if present
    rows = []
    for s in missing:
        rows.append(f"| Skill `{s}` | `skills/{s}/` | Auto-added by okf icm-sync; refine notes |")
    block = "\n".join(rows) + "\n"
    if "| Deep vault ops skill |" in ctx:
        ctx = ctx.replace(
            "| Deep vault ops skill |",
            block + "| Deep vault ops skill |",
            1,
        )
    else:
        ctx = ctx.rstrip() + "\n\n## Auto-routed skills\n" + block + "\n"
    if not args.dry_run:
        # Atomic write: temp file + os.replace to avoid partial writes
        fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=str(ctx_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(ctx)
            os.replace(tmp, str(ctx_path))
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        print(f"wrote {len(missing)} routing stub(s) into CONTEXT.md")
    return 0


# --- cli -------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="okf", description="OKF brain tooling.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("index", help="Build search index + provenance map.")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("search", help="Search concepts (BM25).")
    sp.add_argument("query")
    sp.add_argument("--visibility", choices=VALID_VISIBILITY)
    sp.add_argument("--type")
    sp.add_argument("--domain")
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("lint", help="Health-check the corpus.")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--strict", action="store_true", help="Exit non-zero on errors.")
    sp.set_defaults(func=cmd_lint)

    sp = sub.add_parser("view", help="Build index, serve locally, and open the graph viewer in a browser.")
    sp.add_argument("--port", type=int, default=8000, help="Port to serve on (auto-picks a free one if busy).")
    sp.add_argument("--no-open", action="store_true", help="Start the server but don't open a browser.")
    sp.add_argument("--no-index", action="store_true", help="Skip rebuilding the index before serving.")
    sp.set_defaults(func=cmd_view)

    sp = sub.add_parser("relink", help="Rewrite intra-corpus markdown links to canonical /concepts/<id>.md ids.")
    sp.add_argument("--dry-run", action="store_true", help="Preview rewrites; write nothing.")
    sp.set_defaults(func=cmd_relink)

    sp = sub.add_parser("doctor", help="Agent-surface integrity (ICM, AGENTS, AAAK, routing).")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--strict", action="store_true", help="Exit non-zero on errors.")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("icm-sync", help="Diff skills/ vs CONTEXT.md routing; optional --write stubs.")
    sp.add_argument("--write", action="store_true", help="Append missing skill rows to CONTEXT.md")
    sp.add_argument("--dry-run", action="store_true", help="Report only (default if --write omitted)")
    sp.add_argument("--strict", action="store_true", help="Exit 1 if any skill missing from CONTEXT")
    sp.set_defaults(func=cmd_icm_sync)

    sp = sub.add_parser("link", help="Apply cross-links from suggest-links candidates.")
    sp.add_argument("--auto", action="store_true", help="Auto-generate and apply links (default: read JSON pairs from stdin).")
    sp.add_argument("--max", type=int, default=50, help="Max candidate pairs to apply (default 50).")
    sp.add_argument("--min-tags", type=int, default=2, help="Min shared tags for tag-based candidates.")
    sp.add_argument("--min-score", type=float, default=10.0, help="Min BM25 score to apply (default 10.0).")
    sp.add_argument("--concept", help="Scope to a single concept id (e.g. learning/dev/javascript)")
    sp.add_argument("--quiet", action="store_true", help="Suppress per-pair output.")
    sp.set_defaults(func=cmd_link)

    sp = sub.add_parser("suggest-links", help="Find missing cross-links between concepts.")
    sp.add_argument("--max", type=int, default=50, help="Max candidate pairs to output (default 50).")
    sp.add_argument("--min-tags", type=int, default=2, help="Min shared tags for tag-based candidates (default 2).")
    sp.add_argument("--min-score", type=float, default=0.5, help="Min BM25 score for orphan candidates (default 0.5).")
    sp.add_argument("--concept", help="Scope to a single concept id (e.g. learning/dev/javascript)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_suggest_links)

    sp = sub.add_parser("sql", help="Run ad-hoc SQL queries over the corpus (requires duckdb).")
    sp.add_argument("query", nargs="*", help="SQL query (read from stdin if omitted).")
    sp.set_defaults(func=cmd_sql)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
