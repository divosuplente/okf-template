---
name: okf-core
description: >-
  OKF core operations skill — how to work with the OKF brain vault. Loaded as
  base knowledge for any session working in the OKF repo. Covers the operating
  contract (AGENTS.md), the ingest pipeline, query/search, lint, relink, the
  source-of-truth convention, visibility rules for private content, the creators
  domain, and how to run the okf.py CLI tools. Triggered when working in the OKF
  repo, managing concepts, or when any okf-* skill is active.
type: skill
---

# OKF Core — Operating Model for the Brain Vault

## What OKF Is
A personal Open Knowledge Format brain at `~/okf`. It is the **single source of truth** — all knowledge lives here as plain markdown concept files. No external origin folders (pka, toolswiki are deprecated).

## Repository Layout
```
concepts/<domain>/<slug>.md   # Canonical concepts (the brain)
concepts/creators/            # YouTube channels, content creators, authors
raw/youtube/                  # Raw snapshots of YouTube ingests
raw/forge-ai-gateway/         # Raw snapshots of gateway ingests
raw/web/                      # Raw snapshots of web article ingests
raw/attachments/               # Attachments for folder ingests
provenance/map.json           # Auto-generated concept→source map
index.md                      # Catalog with counts
log.md                        # Append-only history
tools/okf.py                  # CLI: index, search, lint, relink, view, ingest
tools/viewer.html             # Browser-based concept graph
```

## Frontmatter Schema
```yaml
---
type: <type>                    # REQUIRED
visibility: private | shareable # REQUIRED
title: <display name>           # recommended
description: <one-line>          # recommended
domain: life | tools | learning | skills | specs | people | orgs | documents | creators
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

## Domains & Types
- `life` — topics, habits, goals, projects, key elements, journal entries (mostly private)
- `learning` — articles, courses, talks, video concepts
- `tools` — AI/dev tools, ecosystem utilities, products
- `creators` — YouTube channels, content creators, authors (public figures, shareable)
- `skills` — agent skills, reusable expertise
- `specs` — specifications, standards
- `people` — private contacts (therapy, doctors) — NOT for public creators
- `orgs` — organizations
- `documents` — identity/records

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

## Standard Pipeline (after any change)
1. `python3 tools/okf.py index`
2. `python3 tools/okf.py lint`
3. `python3 tools/okf.py relink --dry-run`
4. `python3 tools/okf.py relink` (only if dry-run shows rewrites)
5. Update `index.md` counts if total changed
6. Append `log.md` entry

## Cross-Linking
- Use bundle-relative markdown links: `[Title](/concepts/domain/slug.md)`
- Add links bidirectionally when possible
- Broken links are tolerated (may represent not-yet-written knowledge)
- Run `okf relink --dry-run` after creating concepts to check links

## Key Distinction: People vs Creators
- `concepts/people/` — private contacts you have a direct relationship with (therapy, doctors)
- `concepts/creators/` — public content creators (YouTube channels, authors, speakers)
- `people/` entries are typically `visibility: private`
- `creators/` entries are typically `visibility: shareable`
