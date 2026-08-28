# OKF Brain — Template

A starter repository for a personal **Open Knowledge Format (OKF)** knowledge vault: plain markdown concepts, filesystem-first agent workflows, and portable tooling with **no required proprietary runtime**.

Designed so **humans and LLM agents** can read, query, and extend the same corpus. The vault is the **sole source of truth** for its knowledge.

## What you get

| Layer | Purpose |
|-------|---------|
| `concepts/` | Canonical wiki — one concept per file, domain/subdomain tree |
| `IDENTITY.md` → `CONTEXT.md` | Thin agent orientation (ICM Layers 0–1) |
| `AGENTS.md` | Deep operating contract for agents |
| `_config/` | Conventions, glossary, extensible taxonomy reference |
| `skills/` | Invocable agent skills (+ staged pipelines) |
| `tools/` | Python CLI (`okf.py`, ingest, validation) |
| `.omp/extensions/` | Project-local agent hooks (OMP extensions) |
| `themes/` | Cross-domain navigational overlays |
| `raw/` | Historical source snapshots (archive, not authoritative) |

## Quick start

### Requirements

- Python 3.10+ (3.12+ recommended)
- Optional: [uv](https://github.com/astral-sh/uv) for virtualenv management
- Any markdown-friendly editor; any coding agent that can read a repo root

### Setup

```bash
git clone https://github.com/divosuplente/okf-template.git okf && cd okf

# Create virtual environment
uv venv

# Build search index
.venv/bin/python tools/okf.py index

# Health check
.venv/bin/python tools/okf.py lint
```

Full setup (book pipeline, study stack, all deps): see [SETUP.md](SETUP.md).

### Optional PATH wrapper

```bash
ln -sf "$PWD/tools/okf" ~/.local/bin/okf
okf search "your query"
```

## Architecture

### Design principles

1. **Vault is SSOT** — no live dependency on external origin repos.
2. **Plain markdown, portable core** — ordinary filesystem ops; Python stdlib for core tools.
3. **Privacy by domain (overridable)** — personal domains default `private`; export must hard-filter to `shareable`.
4. **One concept per file** — concept id = path under `concepts/` without `.md`.
5. **Full-body classification (FBC)** — agents read the entire source body to choose domain/subdomain/tags; `_config/taxonomy.md` is an extensible reference, not a closed classifier.
6. **Layered context** — load IDENTITY → CONTEXT → one skill/stage; not the whole contract every turn.
7. **Mechanical vs judgment** — scripts handle index/lint/relink; LLMs handle synthesis and FBC.

### Domain structure

| Domain | Default visibility | Purpose |
|--------|-------------------|---------|
| `life` | private | Personal: key elements, goals, habits, projects, topics |
| `people` | private | Individuals, contacts |
| `orgs` | private | Organizations, companies |
| `documents` | private | Identity/records stubs |
| `work` | private | Enterprise/internal notes |
| `tools` | shareable | Products, CLIs, agent frameworks, devices |
| `specs` | shareable | Specifications and standards |
| `skills` | shareable | Reusable expertise — knowledge about skills |
| `learning` | shareable | Articles, courses, talks |
| `creators` | shareable | Public creators, channels, authors |

### Frontmatter (minimal)

```yaml
---
type: tool | learning | skill | reference | topic | note | ...
visibility: private | shareable
title: Display name
description: One line
domain: tools
tags: [agent, orchestration]
source:
  - https://example.com
---
```

Required: `type`, `visibility`. See `_config/taxonomy.md` for the full type vocabulary.

## Skills

Invocable agent skills live in `skills/`. Each is a self-contained workflow:

| Skill | Role |
|-------|------|
| `okf-core` | Vault ops, hubs, CLI reference |
| `okf-ingest` | Single URL/video/article ingest |
| `okf-batch-ingest` | Folder/inbox batch ingest |
| `okf-ingest-channel` | YouTube channel transcript pipeline |
| `okf-query` | Search & cite from the vault |
| `okf-journal` | Private journal/therapy note ingest |
| `okf-review` | Spaced repetition review scheduling |
| `okf-study` | Study loop with retrieval practice |
| `okf-book-ingest` | Textbook chapter ingestion |
| `okf-teach` | Teaching workspace engine |
| `okf-tasks` | Cross-session task tracking |
| `okf-problem-journal` | Problem tracking for study |
| `okf-aaak-compression` | Skill token compression |

## Tooling

Core vault ops are stdlib-only and run with any Python:

```bash
.venv/bin/python tools/okf.py index              # build search index
.venv/bin/python tools/okf.py search "query"     # search concepts
.venv/bin/python tools/okf.py lint               # health check
.venv/bin/python tools/okf.py relink --dry-run   # canonicalize links
.venv/bin/python tools/okf.py doctor             # vault integrity
.venv/bin/python tools/okf.py view --port 8000   # browser concept graph
.venv/bin/python tools/okf.py sql "SELECT ..."   # ad-hoc SQL (requires duckdb)

.venv/bin/python tools/ingest.py <url|file>       # ingest single item
```

Tests: `.venv/bin/python -m pytest tools/tests -q`.

## Agent hooks (OMP extensions)

The template ships with `.omp/extensions/` for project-local agent hooks. These are small `.js` files that intercept agent lifecycle events — blocking tool calls, validating writes, or running pre-flight checks.

Three extensions ship with the template:

| Extension | What it does |
|-----------|-------------|
| `path-guard.js` | Enforces `rules/path-access-control.md` allow/deny list |
| `concept-guard.js` | Validates frontmatter (`type`, `visibility`, `source`) on concept writes |
| `git-sync.js` | Auto-syncs `git pull --rebase` on first tool call |

See [SETUP.md §9](SETUP.md#9-agent-hooks-omp-extensions) for the full extension contract and how to write your own.

## Agent session protocol

1. Read `IDENTITY.md` (where am I?)
2. Read `CONTEXT.md` (where do I go?)
3. Open **only** the skill or stage named for the task
4. Use `AGENTS.md` / `_config/*` when deep rules are required

## Privacy

- Personal domains (`life`, `people`, `orgs`, `documents`, `work`) default to `visibility: private`.
- Any public bundle **must** exclude `private` concepts.
- Agent path policy: `rules/path-access-control.md`.
- `.omp/` runtime artifacts are gitignored.

## Layout

```
okf/
├── IDENTITY.md          # ICM Layer 0
├── CONTEXT.md           # ICM Layer 1 task router
├── AGENTS.md            # Deep operating contract
├── README.md            # This file
├── SETUP.md             # Full setup runbook
├── decisions.md         # Technical decisions
├── index.md             # Progressive catalog (generated)
├── log.md               # Append-only ops history
├── _config/             # conventions, glossary, taxonomy
├── rules/               # path-access-control.md
├── .omp/extensions/     # Project-local agent hooks
├── concepts/<domain>/   # Canonical knowledge (empty — your vault)
├── themes/              # Cross-domain synthesis overlays
├── skills/              # Invocable skills + stages/
├── tools/               # okf.py, ingest, validation
├── raw/                 # Historical snapshots (read-only)
├── provenance/          # Generated concept → source maps
├── specs/               # Feature specs
└── inbox/               # Optional ingest staging
```

## Methodology

This system combines several published ideas:

1. **Open Knowledge Format (OKF)** — plain markdown concepts with YAML frontmatter, progressive disclosure, and living-wiki operations.
2. **Interpretable Context Methodology (ICM)** — folder structure as agent architecture (Van Clief & McDermott). Applied here as a thin `IDENTITY`/`CONTEXT` overlay + stage contracts under skills.
3. **Karpathy-style LLM knowledge compile loop** — raw → compile → wiki → Q&A.
4. **Unix lineage** — plain text interfaces, composable stages, scripts for non-LLM work.

## Credits

- OKF / vault design — this repository's `specs/` and `decisions.md`
- ICM — Jake Van Clief & David McDermott; community template ktnCodes/icm-template
- Compile-loop framing — Andrej Karpathy (LLM knowledge base pattern)
