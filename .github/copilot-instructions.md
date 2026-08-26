---
type: topic
---


# GitHub Copilot Instructions

Use these project-local rules before suggesting edits.

## Adopted from AGENTS.md

# OKF Brain — Operating Contract


**Before any work:** Read `AGENTS.md` for the vault operating contract and session startup rules (including mandatory origin sync).
This repository is a personal **Open Knowledge Format (OKF)** brain: a single canonical, agent- and human-friendly knowledge corpus. This vault is the **sole source of truth** — there are no external origin repositories to read from or sync against. Read this file before editing anything. Rationale lives in `decisions.md`; the feature spec/plan live in `specs/`.

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

## Frontmatter schema (canonical)

Vault uses OKF v0.2 conventions with local extensions. Required on every concept: `type`, `visibility`. Recommended: `title`, `description`, `domain`, `tags`, `source`, `status`, `generated`.

**Vault extensions beyond v0.2:** `visibility` (required), `domain`, `source` (singular flat list), `status: active|dormant|archived` (v0.2 uses `stable|draft|deprecated`).

**Actor Convention (`generated` / `verified`):**
- `human:user` (vault owner)
- `agent:<tool>` (e.g. `agent:<tool>`)
- `process:<name>` (e.g. `process:okf-ingest`)
```yaml
---
type: <unified type>            # REQUIRED
visibility: private | shareable # REQUIRED
title: <display name>           # recommended
description: <one-line summary> # recommended
domain: life | tools | specs | skills | learning | people | orgs | documents | creators | work
tags: [<tag>, ...]
source:                         # provenance — flat list of URLs, self:, or historical refs
  - https://example.com/article
  - self:
generated: { by: agent:<tool>, at: 2026-01-01T00:00:00Z }
status: active | dormant | archived
---
```

Consumers MUST tolerate unknown `type` values and unknown extra keys (preserve them).

## Unified `type` vocabulary
`key-element`, `goal`, `habit`, `project`, `topic`, `person`, `organization`, `document`, `tool`, `spec`, `skill`, `learning`, `source`, `playbook`, `reference`, `note` (fallback). Finer grouping is carried by `domain` + `tags`, not by inventing new types casually.

## Links
- Concepts reference each other with standard markdown links, bundle-relative from the repo root, e.g. `[Nub](/concepts/tools/nub.md)`.
- A link asserts an untyped relationship; the prose around it conveys the kind.
- Broken links are tolerated (they may represent not-yet-written knowledge); `lint` reports them, they are never fatal.

## Tag conventions
- Tags are lowercase, hyphenated, singular (e.g., `self-hosting` not `Self-Hosting`, `agent` not `agents`).
- The `dev` tag is a broad catch-all for development content; specific sub-topic tags (`javascript`, `typescript`, `react`, `css`, `html`, `git`) SHOULD be added alongside `dev` when applicable.
- Avoid tag singular/plural duplicates — pick one form (singular preferred) and use it consistently.
- Each concept should have at least one tag.
- Domain tags (e.g., `tools`, `skills`) are redundant with the `domain` frontmatter — avoid them.
- The `clippings` tag is a byproduct of the Obsidian clipping extension and should NOT be used; it carries no meaningful information. Remove it during ingest if present.

## Conventional body headings
The following headings have conventional meaning and SHOULD be used when applicable:

| Heading | Purpose |
|---------|---------|
| `# Schema` | Structured description of an asset's columns/fields (for tool concepts with structured data). |
| `# Examples` | Concrete usage examples, often as fenced code blocks. |
| `# Citations` | External sources backing claims in the body. Numbered references preferred. |

## Operations
All three are plain-filesystem workflows. `query` is agent-driven; `index`/`search`/`lint` also have a deterministic helper in `tools/okf.py`.
### ingest
1. Read the source (a URL, a document, or an existing file).
2. Snapshot the raw source verbatim into `raw/<slug>.md` (for URLs/docs) or skip if it's already in the vault.
3. Create or update the canonical concept(s) under `concepts/<domain>/`: write required frontmatter (`type`, `visibility`), `source` provenance, and a structured markdown body. Set `visibility` explicitly — do not rely on any origin-based rule.
4. Cross-link related concepts.
5. Update `provenance/map.json` (+ regenerate `map.md`), `index.md`, and append a `log.md` entry.
6. `visibility` defaults by domain: `private` for personal domains (`life`, `people`, `orgs`, `documents`, `work`), `shareable` for others. The author can override either default by setting `visibility` explicitly.
### query
1. Read `index.md`, then the relevant concept files (optionally `tools/okf.py search`).
2. Answer with citations to the exact concept files used. If nothing supports the answer, say so; do not fabricate.
3. If the answer is durable, file it back as a new concept (with provenance `source: [self]` or the supporting concepts) and update `index.md`/`log.md`.
### lint
Report (never hard-fail): missing required frontmatter (`type`, `visibility`), broken/missing concept links, orphan concepts (no inbound links), duplicate/possible-conflict concepts, invalid `visibility` values, and personal-domain concepts marked `shareable` (warning — confirms the override was intentional).

## Visibility & export
- `visibility: private` — personal/sensitive; stays local; never exported.
- `visibility: shareable` — eligible for a future shareable/sellable bundle.
- Any export MUST hard-filter to `shareable` only. When unsure, treat as `private`.
- **Domain defaults**: personal domains (`life`, `people`, `orgs`, `documents`, `work`) default to `private`; all other domains default to `shareable`. The author can override either default by setting `visibility` explicitly.
- **Lint warning**: when a personal-domain concept is marked `shareable`, lint reports a `privacy` warning so the author confirms the override was intentional. This is informational, not an error.
## Tooling
- `python3 tools/ingest.py <url|file>` — ingest a URL or local document into the vault (snapshots raw, creates concept, sets provenance).
- `python3 tools/okf.py index` — build the search index (`tools/index.json`, gitignored).
- `python3 tools/okf.py search "<query>" [--visibility shareable] [--type tool] [--domain tools]`.
- `python3 tools/okf.py lint [--json]`.
- `python3 tools/okf.py relink [--dry-run]` — rewrite intra-corpus markdown links to canonical `/concepts/<id>.md` ids (run after `ingest`).
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
- * `skills/okf-ingest`
- * `skills/okf-batch-ingest`
- * `skills/okf-core`
- - When referencing a skill in an agent prompt, use the **skill identifier** that matches the folder name under `skills/`.
- For example, if the skill lives in `skills/okf-ingest`, you can invoke it as `skill:okf-ingest`.
- This avoids repeating the `skills/` prefix and keeps references concise.
Tooling is Python stdlib only (run via `uv`) and has no external/runtime dependencies.
## Path-Access Rule – Agents MUST consult `rules/path-access-control.md` before accessing any filesystem path. Only `skills/` and `inbox/` (for ingestion) are permitted; all other directories are blocked. This prevents accidental disclosure of global artefacts and enforces secure, predictable file‑system usage. **Example:** when referencing a file, first check `path.within_allowed(candidate_path)`; if false, abort or request permission.


