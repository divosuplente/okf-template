---
type: topic
---
# OKF Brain

A personal **Open Knowledge Format (OKF)** knowledge vault: plain markdown concepts, filesystem-first agent workflows, and portable tooling with **no required proprietary runtime**.

This repository is designed so **humans and LLM agents** can read, query, and extend the same corpus. The vault is the **sole source of truth** for its knowledge.

> **Packaging note:** A future public share should export **`visibility: shareable` only**. Personal domains default to `private`. Review `rules/path-access-control.md` and frontmatter before publishing.

---

## What you get

| Layer | Purpose |
|-------|---------|
| `concepts/` | Canonical wiki — one concept per file, domain/subdomain tree |
| `IDENTITY.md` → `CONTEXT.md` | Thin agent orientation (ICM Layers 0–1) |
| `AGENTS.md` | Deep operating contract |
| `_config/` | Conventions, glossary, extensible taxonomy reference |
| `skills/` | Invocable agent skills (+ staged pipelines) |
| `tools/` | Python CLI (`okf.py`, ingest, validation, smoke); `sql` subcommand requires duckdb |
| `themes/` | Cross-domain navigational overlays |
| `raw/` | Historical source snapshots (archive, not authoritative) |

---

## Methodology sources

This system combines several published ideas:

1. **Open Knowledge Format (OKF)** — plain markdown concepts with YAML frontmatter, progressive disclosure, and living-wiki operations (ingest / query / lint). See vault concept [Open Knowledge Format](concepts/specs/open-knowledge-format.md) and `specs/001-okf-brain-v1/`.

2. **Interpretable Context Methodology (ICM)** — *folder structure as agent architecture* (Van Clief & McDermott). Sequential stages as numbered folders and markdown contracts instead of multi-agent framework orchestration for human-reviewed pipelines.  
   - Paper: [arXiv:2603.16021](https://arxiv.org/abs/2603.16021) ([HTML](https://arxiv.org/html/2603.16021v2))  
   - Template: [ktnCodes/icm-template](https://github.com/ktnCodes/icm-template)  
   - Applied here as a **hybrid**: thin `IDENTITY`/`CONTEXT` overlay + stage contracts under skills — **not** renumbering `concepts/` into a factory line.  
   - Vault notes: [ICM](concepts/tools/agents/orchestration/interpretable-context-methodology.md), [OKF ICM Layer](concepts/tools/agents/orchestration/okf-icm-layer.md).

3. **Karpathy-style LLM knowledge compile loop** — raw → compile → wiki → Q&A. Mapped to `raw/`/`inbox/` → ingest skills → `concepts/` + `index.md` → `okf search` / agent Q&A.

4. **Unix / pipe-and-filter lineage** (as cited in the ICM paper) — plain text interfaces, composable stages, scripts for non-LLM work.

5. **AAAK dual-layer skills** (MemPalace-inspired) — lossy compressed `SKILL.md` for agent token load + lossless `SKILL.full.md` as edit SSOT. See `skills/okf-aaak-compression/`.

6. **Channel extraction pipeline** (adapted from Cole Medin–style KB builds) — fetch → extract → canonicalize barrier → write → validate → gap/QA. See `skills/okf-ingest-channel/` and [OKF Pipeline](concepts/tools/agents/orchestration/okf-pipeline.md).

---

## Design principles

1. **Vault is SSOT** — no live dependency on external origin repos.
2. **Plain markdown, portable core** — ordinary filesystem ops; Python stdlib for core tools; `sql` subcommand optionally uses duckdb.
3. **Privacy by domain (overridable)** — personal domains default `private`; export must hard-filter to `shareable`.
4. **One concept per file** — id = path under `concepts/` without `.md`.
5. **Full-body classification (FBC)** — agents read the **entire** source body to choose domain/subdomain/tags; `_config/taxonomy.md` is an **extensible reference**, not a closed classifier.
6. **Layered context** — load IDENTITY → CONTEXT → one skill/stage; not the whole contract every turn.
7. **Mechanical vs judgment** — scripts handle index/lint/relink/noise tags; LLMs handle synthesis and FBC.

---

## Quick start

### Requirements

- Python 3.10+ (3.12+ recommended)
- Optional: [uv](https://github.com/astral-sh/uv), `yt-dlp` (channel ingest only)
- Any markdown-friendly editor; agents that can read a repo root

### Setup

```bash
git clone <this-repo> okf && cd okf

# full setup (venv + all deps) — see SETUP.md for details
uv venv
uv pip install -e "tools/book-to-skill[all]" pymupdf pix2tex timm

# build search index
.venv/bin/python tools/okf.py index

# health checks
.venv/bin/python tools/okf.py lint
.venv/bin/python tools/okf.py doctor
.venv/bin/python tools/smoke_agent_surface.py
```

> **New machine?** Read `SETUP.md` — the runbook covers prerequisites, the
> book pipeline (slicing, extraction, formula snapshots), and what lives
> where. The venv is not committed; always run tooling via `.venv/bin/...`.

Optional PATH wrapper:

```bash
ln -sf "$PWD/tools/okf" ~/.local/bin/okf
okf search "your query"
```

### Self-study roadmaps

The vault contains structured self-study curricula for physics and pure mathematics. Both are sequential — each level/phase builds on every previous one. **Solving problems is mandatory**; reading alone produces the illusion of understanding.

| Roadmap | Path | Scope | Levels/Phases |
|---|---|---|---|
| Physics | `concepts/learning/physics/physics-self-study-roadmap.md` | Intro mechanics → graduate QFT (Rigetti curriculum) | 9 undergraduate + 6 graduate |
| Mathematics | `concepts/learning/math/math-self-study-roadmap.md` | Precalculus → algebraic geometry (Bertolucci curriculum) | 36 phases across 3 tracks |

**Key files for agents building lessons or exercises:**

- `concepts/learning/physics/physics-self-study-roadmap.md` — level table, essential texts, math prerequisites per level, owned/book acquisition plans
- `concepts/learning/math/math-self-study-roadmap.md` — phase descriptions, key books, three-track structure (Basic / Undergraduate / Complete)
- `concepts/learning/physics/textbooks/` — one concept per core textbook with progress tracking
- `concepts/learning/math/textbooks/` — same for math texts
- `concepts/learning/study-prerequisite-graph.md` — how math and physics levels interleave
- `concepts/learning/methods/lesson-design-rules.md` — **mandatory rules for agents building lessons**: concise prose, full worked examples, runnable Python code, exercises with answers, verifiable sources only, visual enrichment, Pocock teach method (knowledge → skills → wisdom, zone of proximal development, storage strength over fluency, tight feedback loops)
- `concepts/learning/methods/` — study methodology concepts (retrieval practice, spaced repetition, Feynman technique, deliberate practice, Pólya problem-solving, interleaving, elaborative encoding)
- `concepts/learning/tools/manim.md` — manim evaluation (not a learning tool; watch 3b1b videos for intuition instead)
- `concepts/creators/general/3blue1brown.md` — curated playlist links for visual intuition on roadmap topics
- `SETUP.md §2` + `SETUP.md §8` — study stack install (NumPy/SciPy/SymPy/Matplotlib/Plotly/Jupyter/SymDerive)

**Navigation pattern:** read the roadmap → read `lesson-design-rules.md` → identify current level → read the textbook concept → build lessons with the study stack → verify against problem sets.

### Agent session protocol

1. Read `IDENTITY.md` (where am I?)
2. Read `CONTEXT.md` (where do I go?)
3. Open **only** the skill or stage named for the task
4. Use `AGENTS.md` / `_config/*` when deep rules are required

Model adapters (`CLAUDE.md`, `GEMINI.md`) point at this path. Prefer **universal** root files over host-specific adapters when packaging.

---

## Layout (summary)

```
okf/
├── IDENTITY.md          # ICM Layer 0
├── CONTEXT.md           # ICM Layer 1 task router
├── AGENTS.md            # Deep contract
├── README.md            # This file
├── decisions.md         # Technical decisions (D-xxx)
├── index.md             # Progressive catalog
├── log.md               # Append-only ops history
├── _config/             # conventions, glossary, taxonomy
├── rules/               # path-access-control, etc.
├── concepts/<domain>/   # Canonical knowledge
├── themes/              # Cross-domain synthesis overlays
├── skills/              # Invocable skills + stages/
├── tools/               # okf.py, ingest, validation, smoke
├── raw/                 # Historical snapshots (read-only archive)
├── provenance/          # Generated concept → source maps
├── specs/               # Feature specs (spec-kit)
└── inbox/               # Optional ingest staging
```

### Domains

`life` · `people` · `orgs` · `documents` · `tools` · `specs` · `skills` · `learning` · `creators` · `work`

### Skills

| Skill | Role |
|-------|------|
| `okf-core` | Vault ops, hubs, CLI |
| `okf-ingest` | Single URL/video/article (+ stages 01–04) |
| `okf-batch-ingest` | Folder/inbox batches |
| `okf-ingest-channel` | YouTube channel pipeline (+ stages 01–08) |
| `okf-icm-sync` | Keep IDENTITY/CONTEXT routing aligned |
| `okf-aaak-compression` | Compress/refresh dual-layer skills |

---

## Tooling reference

Core vault ops are stdlib-only and run with any Python; the book pipeline needs the venv (see `SETUP.md`). Use `.venv/bin/python` consistently:

```bash
.venv/bin/python tools/okf.py index
.venv/bin/python tools/okf.py search "query" [--domain tools] [--visibility shareable]
.venv/bin/python tools/okf.py lint [--json] [--strict]
.venv/bin/python tools/okf.py relink [--dry-run]
.venv/bin/python tools/okf.py sql "SELECT domain, COUNT(*) FROM concepts GROUP BY domain"  # requires duckdb
.venv/bin/python tools/okf.py doctor [--json] [--strict]
.venv/bin/python tools/okf.py icm-sync [--write] [--strict]
.venv/bin/python tools/okf.py view [--port 8000]

.venv/bin/python tools/ingest.py <url|file>
.venv/bin/python tools/ingest_postprocess.py --dry-run --paths concepts/...
.venv/bin/python tools/smoke_agent_surface.py
.venv/bin/python tools/validation/audit.py
.venv/bin/python tools/validation/citation_check.py
.venv/bin/python tools/validation/sweep.py
```

Tests: `.venv/bin/python -m pytest tools/tests -q`.

---

## Frontmatter (minimal)

```yaml
---
type: tool | learning | skill | reference | ...
visibility: private | shareable
title: Display name
description: One line
domain: tools
tags: [agent, orchestration]
source:
  - https://example.com
timestamp: 2026-08-06
---
```

Required: `type`, `visibility`. Taxonomy reference (not a cage): `_config/taxonomy.md`.

---

## Ingest sketch

**Single item:** `skills/okf-ingest` stages — snapshot → concept (FBC) → cleanup → index/log.

**Channel:** `skills/okf-ingest-channel` stages — fetch → extract → canonicalize → write → polish → validate → gap → QA.

Always prefer scripts for mechanical steps; never auto-assign domain/tags from keywords alone when judgment is required (FBC).

---

## Privacy & public packaging

- Defaults: personal domains (`life`, `people`, `orgs`, `documents`, `work`) → `private`; others → `shareable`.
- Any public bundle **must** exclude `private` concepts and review `raw/` / `log.md` / work notes.
- Path policy for agents: `rules/path-access-control.md`.
- Optional local tools (e.g. ContextVC) must not be required for other machines.

---

## Decisions & history

- Rationale: `decisions.md` (e.g. D-014 SSOT, D-015 privacy, D-017 ICM, D-018/D-019 agent-surface).
- Ops log: `log.md`.

---

## License

Set a license before public release (not fixed by this README). Content visibility is separate from code license — enforce the `visibility` export gate regardless.

---

## Credits

- OKF / vault design — this repository’s `specs/` and `decisions.md`
- ICM — Jake Van Clief & David McDermott; community template ktnCodes/icm-template
- Compile-loop framing — Andrej Karpathy (LLM knowledge base pattern)
- AAAK skill compression pattern — MemPalace / related dialect work
- Channel pipeline patterns — adapted from public KB pipeline practices (e.g. Cole Medin–style builds)

---

## Contributing (when open)

1. Follow `IDENTITY.md` → `CONTEXT.md` for agent work.
2. One concept per file; FBC for placement and tags.
3. Run `okf doctor`, `okf lint`, and tests before PRs.
4. Do not commit secrets, private journals, or enterprise `work/` content to a public fork.
