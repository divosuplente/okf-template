---
type: skill
name: okf-core
description: "OKF core operations — base knowledge layer for the OKF brain vault. FORCE-loaded (not discovery-dispatchable) as foundational context for any session working in the OKF repo. Covers the operating contract, visibility rules, tag conventions, link conventions, CLI tools, and domain defaults. Not invocable by user; loaded automatically when okf-* skills are active."
---

# OKF Core — Operating Model for the Brain Vault

## Taxonomy reference (do not paste tables here)
- Shared map: `_config/taxonomy.md` (`@tax`)
- **FBC mandatory:** read FULL source body to choose domain/subdomain/subsubdomain and semantic tags.
- Map is extensible — if content does not fit, extend `@tax` + hubs (see extension protocol there).
- Tag *cleanup* (banned noise tags, singular/lowercase) is in `@tax`; do not keyword-assign tags.

## Full-body classification (non-negotiable)
1. Read the entire source body/transcript.
2. Place and tag from actual meaning — not filename, title keywords, or static enums alone.
3. Prefer known leaves in `_config/taxonomy.md` when they fit.
4. Otherwise extend the map per taxonomy extension protocol.


## What OKF Is
A personal Open Knowledge Format brain at `<repo-root>`. It is the **single source of truth** — all knowledge lives here as plain markdown concept files.

## Repository Layout
```
concepts/<domain>/<sub>/<slug>.md        # Concepts in subdomain folders
concepts/<domain>/<sub>/<ssub>/<slug>.md # Concepts in subsubdomain folders
concepts/<domain>/<domain>.md            # Domain hub — links to subdomain hubs
concepts/<domain>/<sub>.md              # Subdomain hub — links to all child concepts in <domain>/<sub>/
concepts/<domain>/<sub>/<ssub>.md       # Subsubdomain hub — links to all child concepts in <domain>/<sub>/<ssub>/
raw/youtube/                            # Raw snapshots of YouTube ingests
raw/forge-ai-gateway/                   # Raw snapshots of gateway ingests
raw/web/                                # Raw snapshots of web article ingests
raw/attachments/                        # Attachments for folder ingests
themes/<slug>.md                        # Knowledge domain synthesis files (navigational overlays)
themes/index.md                         # Theme catalog with concept counts
tools/taxonomy.json                     # Theme → slug[] groupings
provenance/map.json                     # Auto-generated concept→source map
index.md                                # Catalog with counts
log.md                                  # Append-only history
tools/okf.py                            # CLI: index, search, lint, relink, view, ingest
tools/viewer.html                       # Browser-based concept graph
```

## Frontmatter Schema
```yaml
---
type: <type>                    # REQUIRED
visibility: private | shareable # REQUIRED
title: <display name>           # recommended
description: <one-line>          # recommended
domain: life | tools | learning | skills | specs | people | orgs | documents | creators | work
tags: [<tag>, ...]
resource: <uri>                  # optional
source:                          # optional — external origins only
  - youtube:watch?v=<id>
timestamp: <ISO 8601>           # last meaningful change
status: active | dormant | archived  # optional
---
```

## Source Convention
- OKF-native concepts: **no `source:` field** (OKF is the source of truth)
- External origins: `source: youtube:watch?v=...` or `source: url:https://...`
- `raw/` snapshots only for external sources

## Visibility Rules
- `private` — journaling, therapy, health, personal docs, private contacts. NEVER exported.
- `shareable` — public content (tools, articles, talks, creators). Eligible for export.
- When unsure → `private`
- **Domain defaults**: `PERSONAL_DOMAINS = {"life", "people", "orgs", "documents", "work"}` default to `private`. All other domains default to `shareable`. The author can override either default by setting `visibility` explicitly.
- **Lint warning**: when a personal-domain concept is marked `shareable`, lint reports a `privacy` warning so the author confirms the override was intentional.

## Domains, Subdomains & Subsubdomains

### Domains / subdomains
See `_config/taxonomy.md` (extensible reference). FBC still required.


## Full-Body Classification (Subdomain Routing)

When creating a new concept, determine its domain/subdomain/subsubdomain by **reading the FULL body** of the source document. Do NOT rely on keyword matching, tag tables, or filename hints alone. Classify based on what the content is actually about.

**Decision flow:**
1. Read the entire source document body.
2. Based on the full content, determine:
   - Is it personal (diary, therapy, personal topics)? → `life` + appropriate subdomain
   - Is it a learning topic (health, language, code, music)? → `learning` + appropriate subdomain/subsubdomain
   - Is it a tool/app/device? → `tools` + appropriate subdomain/subsubdomain
   - Is it a private contact (doctor, therapist, tech)? → `people` + appropriate subdomain
   - Is it work-related (enterprise/internal notes)? → `work` + appropriate subdomain
   - Is it an agent skill? → `skills` + appropriate subdomain
   - Is it a public creator/figure? → `creators/general`
   - Is it an organization? → `orgs/general`
   - Is it a document/record? → `documents/general`
   - Is it a specification? → `specs/general`
   - No domain is flat — every domain routes through a subdomain
3. For subsubdomains within `learning/dev`, `learning/health`, `learning/languages`, `learning/music`, `tools/agents`, `tools/dev`, `tools/general`: check the valid subsubdomain tables above.

**Examples:**
- A YouTube video about React hooks → full body discusses React → `learning/dev/react`
- A personal therapy reflection → full body is personal journaling → `life/personal`
- A health science article → full body discusses health → `learning/health`
- An AI coding agent tool → full body describes a tool → `tools/agents/coding-agents`

## Tag Cleanup During Ingest

After reading the full body and before writing the concept, audit tags:

### Deletion Rules
- **Delete** `youtube` tag — redundant with source provenance
- **Delete** `clippings` tag — Obsidian clipping artifact, carries no meaning
- **Delete** domain-redundant tags (e.g., `tools` on a `domain: tools` concept, `learning` on a `domain: learning` concept)
- **Delete** garbage tags (hex strings, pure numeric, empty strings, single characters)
- **Keep** `dev` tag — broad catch-all with genuine filtering value

### Normalization Rules
- All tags lowercase, hyphenated (`self-hosting` not `Self-Hosting`)
- At least **one meaningful tag** required per concept
- Normalize near-duplicates to a single canonical form

### Common Merge Mappings (sample — not exhaustive)

| From | To | Reason |
|------|----|--------|
| `ai-skills` | `ai` | Redundant qualifier |
| `agenticcoding` | `agentic-engineering` | Correct canonical form |
| `blood-sugar` | `glucose` | Scientific term preferred |
| `progamming` | `programming` | Typo fix |
| `selfhosting` | `self-hosted` | Hyphenated form |
| `webdev` | `web-development` | Expanded form |
| `youtube-channel` | `youtube` | Redundant in creators context |
| `long-covid` | `covid` | Shorter canonical |
| `heart-health` | `cardiovascular` | Scientific term preferred |
| `lowcarb` | `low-carb` | Hyphenated form |
| `terminal-tools` | `terminal` | Shorter form |
| `coding-agent` | `coding-agents` | Singular→plural convention |

## Depth-Conditional Backlinks (Hub Update on Ingest)

After creating any new concept, add a backlink to its parent hub. The target hub depends on the concept's depth:

| Concept depth | Backlink target | Example |
|--------------|----------------|---------|
| Subsubdomain concept (`<dom>/<sub>/<ssub>/<slug>.md`) | `concepts/<dom>/<sub>/<ssub>.md` | `learning/dev/react/my-hook.md` → backlink in `learning/dev/react.md` |
| Subdomain concept (`<dom>/<sub>/<slug>.md`, no ssub) | `concepts/<dom>/<sub>.md` | `learning/dev/react/my-hook.md` → backlink in `learning/dev/react.md`; `creators/general/3b1b.md` → backlink in `creators/general.md` |
| *(No flat-domain concepts — every domain has subdomains)* | — | — |

The domain hub auto-covers new concepts via its link to the subdomain hub — no update needed unless a new subdomain is created.

## Theme Reconciliation

After classifying a new concept, check if it belongs to an existing theme:

1. Read `tools/taxonomy.json` and `themes/index.md` for existing themes and their characteristic tags/slugs.
2. If the concept has **≥2 tags that overlap** with a theme's characteristic tags → assign the concept to that theme by adding a reference in the theme file.
3. If **5+ new concepts** land in the same theme over time, update `themes/<slug>.md` with a refresh of the concept list and improvement notes.
4. Themes are **navigational overlays** — they don't replace the `concepts/` hierarchy but provide curated entry points into related concepts scattered across domains.

**Example:** A new concept with tags `agent`, `mcp`, `orchestration` overlaps 3 tags with the "AI Agent Ecosystem" theme → add a reference to the concept in `themes/ai-agent-ecosystem.md`.

## Unified Type Vocabulary
`key-element`, `goal`, `habit`, `project`, `topic`, `person`, `organization`, `document`, `tool`, `spec`, `skill`, `learning`, `source`, `playbook`, `reference`, `note` (fallback).

## CLI Commands
```bash
python3 tools/okf.py index              # rebuild index + provenance map
python3 tools/okf.py search "<query>"   # search concepts
python3 tools/okf.py lint               # health check (never hard-fails)
python3 tools/okf.py relink --dry-run   # check broken links
python3 tools/okf.py relink             # fix link paths
python3 tools/okf.py view               # browser viewer
python3 tools/okf.py ingest --url "..." --tags "#ai #review"  # quick concept creation
python3 tools/okf.py ingest --note "..." --domain life         # direct note
python3 tools/okf.py ingest --journal "..."                     # private journal entry
```

### Postcondition Guardrail
`ingest_inbox.sh` enforces a postcondition: an inbox item is only moved to `processed/` if **at least one concept was actually created**. Failed items are moved to `inbox/failed/` with reasons logged to `inbox/failed/reasons.log`. This prevents silent data loss where an item appears "processed" but nothing was written.

### Purge Stale Processed Files
On every inbox pass, purge any file in `inbox/processed/` that has been sitting there for more than 7 days (mtime-based — `mv` preserves mtime, so it reflects time in the folder). Only the `processed` subfolder is touched:
```bash
find "$VAULT/inbox/processed" -maxdepth 1 -type f -mtime +7 -delete
```

## `ingest.py` Caveats

`tools/ingest.py` has known limitations that require a **mandatory post-ingest cleanup pass**:

1. **Slug-from-path bug**: When `parse_source()` fails to extract a title from the source, `slugify()` falls back to the `source_ref` (file path or URL), producing garbage slugs like `users-<user>-okf-inbox-...` or `inbox-...`. Always verify slugs after ingest and rename files to proper title-derived slugs.
2. **No subdomain support**: `ingest.py` only accepts a top-level `--domain` flag. It writes all concepts to `concepts/<domain>/<slug>.md`. Subdomain routing (`concepts/<domain>/<sub>/<slug>.md`) must be done post-ingest via file moves.
3. **Title extraction may fail**: For inbox files with Obsidian clipping frontmatter, the title often comes through mangled (emoji prefixes, triple-quoted strings, raw URLs as description). Always inspect frontmatter after ingest.
4. **Post-ingest cleanup is mandatory**: After running `ingest.py`, you MUST:
   - Rename garbage-slug files to proper title-derived slugs
   - Move files from `concepts/<domain>/` to their correct `concepts/<domain>/<sub>/` or `concepts/<domain>/<sub>/<ssub>/` paths
   - Fix frontmatter `title`, `description`, `tags` fields
   - Delete duplicate files (when `ingest.py` says "already ingested", check the existing file's quality — it may need a merge)
5. **Title extraction from headings**: When extracting a title from `##` headings in the body, skip structural headings: `Transcript`, `Features`, `Installation`, `Readme`, `Overview`, `Introduction` — these are not suitable concept titles.

## Standard Pipeline (after any change)
1. `python3 tools/okf.py index`
2. `python3 tools/okf.py lint`
3. `python3 tools/okf.py relink --dry-run`
4. `python3 tools/okf.py relink` (only if dry-run shows rewrites)
5. Update `index.md` counts if total changed
6. Append `log.md` entry

## Cross-Linking
- Use bundle-relative markdown links: `[Title](/concepts/<domain>/<sub>/<slug>.md)` for subdomain concepts, or `[Title](/concepts/<domain>/<sub>/<ssub>/<slug>.md)` for subsubdomain concepts
- Add links bidirectionally when possible
- Every new concept MUST add a link entry to its parent hub (depth-conditional — see Hub section)
- Broken links are tolerated (may represent not-yet-written knowledge)
- Run `okf relink --dry-run` after creating concepts to check links

## Key Distinction: People vs Creators
- `concepts/people/` — private contacts you have a direct relationship with (therapy, doctors)
- `concepts/creators/` — public content creators (YouTube channels, authors, speakers)
- `people/` entries are typically `visibility: private`
- `creators/` entries are typically `visibility: shareable` (public figures)
