---
type: infrastructure
---

---
type: skill
visibility: private
title: Agents Framework
description: Central documentation for the OKF Agents system – defines concepts, workflows, and standards for building and coordinating AI agents within the OKF brain.
domain: tools
tags: [agents, framework, documentation]
trust_tier: medium
verified: false
---
# OKF Brain — Operating Contract

This repository is a personal **Open Knowledge Format (OKF)** brain: a single canonical, agent- and human-friendly knowledge corpus. This vault is the **sole source of truth** — there are no external origin repositories to read from or sync against. **Session start (ICM):** read `IDENTITY.md` → `CONTEXT.md` → only the skill/stage needed; use this file as the deep contract, not the default full dump. Rationale lives in `decisions.md`; the feature spec/plan live in `specs/001-okf-brain-v1/`.

## ICM orientation (thin layers)
- `IDENTITY.md` — Layer 0 workspace map (where am I?)
- `CONTEXT.md` — Layer 1 task router (where do I go?)
- `_config/` — conventions, glossary, **taxonomy.md** (extensible FBC reference — not a closed classifier)
- `skills/okf-ingest/stages/` — single-ingest stage contracts (01–04)
- `skills/okf-ingest-channel/stages/` — channel pipeline stages (01 fetch → 08 QA)
- `skills/okf-icm-sync/` — keep IDENTITY/CONTEXT aligned with disk
Do **not** restructure `concepts/` into pipeline stage folders. ICM overlays orientation + multi-step ops only.

## Session startup
**Before any work:** pull latest changes from origin to reduce merge conflicts.
```sh
git pull --rebase origin main
```
If conflicts arise, abort (`git rebase --abort`) and tell the user what needs manual resolution. Do not auto-resolve conflicts.

## Golden rules
1. **This vault is the source of truth.** All knowledge lives here. There are no external origin repos (historical origin repos) to read from, sync against, or preserve. Historical `source:` provenance refs and `raw/` snapshots are kept as an archive of where content originally came from, but they are not authoritative and are never re-read.
2. **Plain markdown, portable core.** Every concept is a readable, diffable markdown file. Every operation must be expressible with ordinary filesystem actions so any LLM agent can perform it. No proprietary runtime required.
3. **Privacy by domain, overridable.** Personal domains (`life`, `people`, `orgs`, `documents`, `work`) default to `visibility: private` — this covers journal entries, therapy notes, health records, personal topics, internal enterprise notes, and anything sensitive. Other domains (`tools`, `skills`, `specs`, `learning`, `creators`) default to `shareable`. The author MAY explicitly set `visibility` to either value for any concept. When a personal-domain concept is marked `shareable`, lint flags it as a warning so the author confirms the override was intentional. When unsure, treat as `private`. `private` concepts are NEVER emitted in a shareable export.
4. **One concept per file.** The file path is the concept's identity (concept id = path under `concepts/` without `.md`).
5. **Provenance is historical.** Existing `source:` fields record where content originally came from. New concepts should record their source (a URL, `self:`, or supporting concept links). Provenance is informational, not authoritative.

## Repository layout
- `concepts/<domain>/<slug>.md` — canonical OKF concept files. Domains: `life`, `people`, `orgs`, `documents`, `tools`, `specs`, `skills`, `learning`, `creators`, `work`.
- `concepts/<domain>/<subdomain>/<slug>.md` — subdomain concepts (e.g., `learning/health`, `tools/agents`, `learning/skills`)
- `concepts/<domain>/<subdomain>/<subsubdomain>/<slug>.md` — subsubdomain concepts (e.g., `learning/health/nutrition`, `learning/music/vocal-technique`, `learning/skills/journaling`)
- `raw/` — verbatim snapshots of originally-ingested source files (historical archive; read-only, not authoritative, not re-read).
- `provenance/map.json` (+ generated `provenance/map.md`) — concept → source mapping (historical; generated from frontmatter).
- `index.md` — progressive-disclosure catalog. `log.md` — append-only history.
- `tools/` — dependency-free `okf.py` CLI (`index`/`search`/`lint`/`relink`/`view`), `ingest.py` (URL/document ingest), and `viewer.html`.
- `IDENTITY.md`, `CONTEXT.md`, `_config/` — ICM agent orientation (map + router + short reference); not a second corpus.
- `skills/` — invocable agent skills; ingest stage contracts under `skills/okf-ingest/stages/`.

## Actor Convention
Vault uses OKF v0.2 actor convention for `generated` and `verified` fields.

| Actor Type | Format | Examples |
|---|---|---|
| Human | `human:<id>` | `human:user` (canonical vault owner) |
| Agent | `agent:<tool>` | `agent:<tool-1>`, `agent:<tool-2>` |
| Process | `process:<name>` | `process:okf-ingest`, `process:okf-index` |

New concepts should set `generated` instead of `timestamp`.
## Frontmatter schema (canonical)

Vault uses OKF v0.2 conventions with local extensions. Canonical keys and examples: `_config/conventions.md` and `_config/glossary.md`.
**Required on every concept:** `type`, `visibility`. Recommended: `title`, `description`, `domain`, `tags`, `source`, `status`, `generated`.
**Vault extensions beyond v0.2:** `visibility` (required), `domain`, `source` (singular flat list), `status: active|dormant|archived` (v0.2 uses `stable|draft|deprecated`). Consumers MUST tolerate unknown `type` values and unknown extra keys.

## Unified `type` vocabulary

See `_config/taxonomy.md` / `_config/glossary.md` for the unified type list. Prefer `domain` + `tags` over inventing new types.

## Links
- Concepts reference each other with standard markdown links, bundle-relative from the repo root, e.g. `[Nub](/concepts/tools/nub.md)`.
- A link asserts an untyped relationship; the prose around it conveys the kind.
- Broken links are tolerated (they may represent not-yet-written knowledge); `lint` reports them, they are never fatal.

## Tag conventions

See `_config/taxonomy.md` (tag cleanup) and `_config/conventions.md`.
Summary: lowercase hyphenated singular; ≥1 tag; no domain-redundant or `clippings` tags; `dev` may pair with specific sub-tags.
Semantic tags are chosen via **full-body classification**, not keyword tables.

## Conventional body headings

When applicable: `# Schema`, `# Examples`, `# Citations`. Details in conventions if needed.

## Operations
All three are plain-filesystem workflows. `query` is agent-driven; `index`/`search`/`lint` also have a deterministic helper in `tools/okf.py`.
### ingest
1. Read the source (a URL, a document, or an existing file).
2. Snapshot the raw source verbatim into `raw/<slug>.md` (for URLs/docs) or skip if it's already in the vault.
3. Create or update the canonical concept(s) under `concepts/<domain>/`: write required frontmatter (`type`, `visibility`), `source` provenance, and a structured markdown body. Set `visibility` explicitly — do not rely on any origin-based rule.
4. Cross-link related concepts.
5. Update `provenance/map.json` (+ regenerate `map.md`), `index.md`, and append a `log.md` entry.
6. `visibility` defaults by domain: `private` for personal domains (`life`, `people`, `orgs`, `documents`, `work`), `shareable` for others. The author can override either default by setting `visibility` explicitly.
### Content quality — humanizer
**Mandatory post-processing.** After ingesting external content or generating content through teaching/self-study workflows, run the `humanizer` skill on the resulting prose to remove AI-generated writing patterns (significance inflation, promotional language, vague attributions, stock AI vocabulary, passive voice, filler, chatbot artifacts). The vault contains human-readable knowledge, not model output. Apply humanizer before finalizing any concept body or teaching material.
### query
1. Read `index.md`, then the relevant concept files (optionally `tools/okf.py search`).
2. Answer with citations to the exact concept files used. If nothing supports the answer, say so; do not fabricate.
3. If the answer is durable, file it back as a new concept (with provenance `source: [self]` or the supporting concepts) and update `index.md`/`log.md`.
### lint
Report (never hard-fail): missing required frontmatter (`type`, `visibility`), broken/missing concept links, orphan concepts (no inbound links), duplicate/possible-conflict concepts, invalid `visibility` values, and personal-domain concepts marked `shareable` (warning — confirms the override was intentional).

## Visibility & export

Defaults and export gate: `_config/taxonomy.md` (visibility defaults) + golden rule 3 above.
`private` never exported; unsure → `private`. Lint warns on personal-domain + `shareable`.

## Tooling
- `python3 tools/ingest.py <url|file>` — ingest a URL or local document into the vault (snapshots raw, creates concept, sets provenance).
- `python3 tools/okf.py index` — build the search index (`tools/index.json`, gitignored).
- `python3 tools/okf.py search "<query>" [--visibility shareable] [--type tool] [--domain tools]`.
- `python3 tools/okf.py lint [--json]`.
- `python3 tools/okf.py relink [--dry-run]` — rewrite intra-corpus markdown links to canonical `/concepts/<id>.md` ids (run after `ingest`).
- `python3 tools/okf.py doctor [--json] [--strict]` — agent-surface integrity (ICM, AAAK, routing).
- `python3 tools/okf.py icm-sync [--write] [--dry-run]` — refresh CONTEXT skill routing from disk.
- `python3 tools/ingest_postprocess.py` — mechanical noise-tag/slug flags only (never classifies).
- `python3 tools/okf.py view [--port 8000] [--no-open] [--no-index]` — build the index, serve locally, and open the `tools/viewer.html` concept graph in a browser (visibility filter included). The easiest way to explore the brain.
- `tools/viewer.html` — can also be opened directly via `file://` (use its **Load index.json** button) if you don't want a server.
A wrapper at `tools/okf` lets you run these as `okf <cmd>` instead of `python3 tools/okf.py <cmd>` once it's on your PATH (e.g. `ln -sf "$PWD/tools/okf" ~/.local/bin/okf`).

## `ingest.py` Caveats

`tools/ingest.py` has known limitations that require a **mandatory post-ingest cleanup pass**:

1. **Slug-from-path bug**: When `parse_source()` fails to extract a title, `slugify()` falls back to `source_ref` (file path), producing garbage slugs like `users-<user>-okf-inbox-...`. Always verify slugs after ingest and rename files to proper title-derived slugs.
2. **No subdomain support**: `ingest.py` only accepts a top-level `--domain` flag. Subdomain routing must be done post-ingest via file moves.
3. **Title extraction may fail**: For inbox files with Obsidian clipping frontmatter, the title often comes through mangled. Always inspect frontmatter after ingest.
4. **Post-ingest cleanup is mandatory**: Rename garbage slugs → move to correct subdomain/subsubdomain paths → fix frontmatter → delete true duplicates (check existing file quality for merge).
5. **Title extraction from headings**: Skip structural headings (`Transcript`, `Features`, `Installation`, `Readme`, `Overview`, `Introduction`) — not suitable concept titles.
-## Skill organization
- The `concepts/skills/` directory contains **knowledge‑related markdown files only**. They are not directly invocable as skills by agents.
- **Usable skills** that agents can call (e.g., via `/skill/invoke`) live in the top‑level `skills/` directory at the repository root. This folder was created above; it currently contains the migrated OKF‑related skills:
- * `skills/okf-ingest` (plus `stages/01`–`04` ICM contracts)
- * `skills/okf-batch-ingest`
- * `skills/okf-ingest-channel`
- * `skills/okf-core`
- * `skills/okf-icm-sync`
- * `skills/okf-aaak-compression`
- - When referencing a skill in an agent prompt, use the **skill identifier** that matches the folder name under `skills/`.
- For example, if the skill lives in `skills/okf-ingest`, you can invoke it as `skill:okf-ingest`.
- This avoids repeating the `skills/` prefix and keeps references concise.
Tooling: core vault ops (`okf.py`, `ingest.py`) are Python stdlib only. The book pipeline (`book-to-skill`, `book-slicer.py`, `formula-snap.py`) needs the venv deps — see `SETUP.md` for the install command and operating procedure.
## Path-Access Rule

## Learning Agents (ALTER Framework)

`agents/alter/` contains five specialized learning roles from the ALTER self-education framework. An orchestrator invites the right agent by trigger keyword:

| Agent | File | Trigger keywords |
|---|---|---|
| **Advisor** — builds personalized curriculum | `agents/alter/advisor.md` | `advisor`, `build curriculum`, `learn [topic]`, `study plan` |
| **Librarian** — curates sources, filters noise | `agents/alter/librarian.md` | `librarian`, `find sources`, `curate sources`, `anchor knowledge` |
| **Tutor** — socratic questioning, gap diagnosis | `agents/alter/tutor.md` | `tutor`, `teach me`, `test me`, `quiz me`, `find my gap` |
| **Editor** — critiques work, refines delivery | `agents/alter/editor.md` | `editor`, `review this`, `critique`, `tighten`, `challenge my thinking` |
| **Roommate** — cross-disciplinary perspective | `agents/alter/roommate.md` | `roommate`, `cross-pollinate`, `different perspective`, `analogy from` |

Each agent reads its operating contract, follows the rules, and can reference vault knowledge via `python3 tools/okf.py search`. See [ALTER Framework](/concepts/learning/alter-framework.md).



