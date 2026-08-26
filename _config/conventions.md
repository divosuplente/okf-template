---
type: infrastructure
---

# Conventions (OKF)

> Layer 3 slice. Full text: `AGENTS.md`. Keep this file short.

## Concept files
- Path = identity: `concepts/<domain>/<…>/<slug>.md`
Required frontmatter: `type`, `visibility`
Recommended: `title`, `description`, `domain`, `tags`, `source`, `status`, `generated`
Vault extension: `source` is a flat list (not v0.2's structured `sources`); `status` uses `active|dormant|archived` (not v0.2's `stable|draft|deprecated`)
Links: bundle-relative from repo root, e.g. `[Nub](/concepts/tools/nub.md)` (prefer current subdomain paths)
Broken links tolerated (lint reports; not fatal)

## Visibility
| Default | Domains |
|---------|---------|
| `private` | `life`, `people`, `orgs`, `documents`, `work` |
| `shareable` | `tools`, `skills`, `specs`, `learning`, `creators` |

Author may override. Lint warns on personal-domain + `shareable`. Unsure → `private`. Export = shareable only.

## Tags
- lowercase, hyphenated, **singular**
- ≥1 meaningful tag; no domain-name tags; never `clippings`
- `dev` = broad parent; add specific tags (`typescript`, `react`, …) when applicable

## Skills vs concepts/skills
- **Invocable:** top-level `skills/<name>/` (id = folder name, e.g. `okf-ingest`)
- **Knowledge only:** `concepts/skills/**` — not agent-invocable

## Hubs
Every new concept links to its parent hub (depth-conditional). Hubs: `concepts/<dom>/<dom>.md`, subdomain hubs, etc. See `okf-core`.
## Actors
OKF v0.2 `generated` / `verified` fields use this convention:
- `human:user` (vault owner)
- `agent:<tool>` (e.g. `agent:<tool>`)
- `process:<name>` (e.g. `process:okf-ingest`)
## After corpus edits
```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
# relink for real only if dry-run shows needed rewrites
# append log.md; refresh index.md counts if totals changed
```

## Tooling
- Stdlib Python via `uv` / `python3` — no external runtime deps for core CLI
- `python3 tools/ingest.py` / `okf.py ingest` for mechanical snapshot+stub; agent skill owns quality path
