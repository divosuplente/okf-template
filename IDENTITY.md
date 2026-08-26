---
type: infrastructure
---

# IDENTITY — OKF Brain

> Layer 0 (~800 tokens). Answer: **Where am I?**  
> Next: read `CONTEXT.md` for task routing. Deep contract: `AGENTS.md`. Do not restructure `concepts/`.

## What this is
Personal **Open Knowledge Format (OKF)** brain at repo root. **Sole source of truth** — no external origin repos. Knowledge = plain markdown concepts any agent can edit with ordinary filesystem ops.

## Golden rules (short)
1. Vault is SSOT. `raw/` is historical archive only — never authoritative, never re-read for truth.
2. Plain markdown, portable core. No proprietary runtime required.
3. Privacy by domain (overridable): personal `life|people|orgs|documents|work` → default `private`; else default `shareable`. Unsure → `private`.
4. One concept per file. Id = path under `concepts/` without `.md`.
5. `source:` is informational provenance only.

## Map
| Path | Role |
|------|------|
| `README.md` | Public system overview (methodology, setup) |
| `IDENTITY.md` / `CONTEXT.md` | ICM orientation + task router |
| `AGENTS.md` | Full operating contract |
| `decisions.md` | Technical decisions |
| `index.md` | Progressive catalog (counts) |
| `log.md` | Append-only ops history |
| `concepts/<domain>/…` | Canonical wiki (do not pipeline-renumber) |
| `raw/` | Verbatim snapshots (read-only) |
| `provenance/` | Generated concept→source maps |
| `skills/` | Invocable agent skills (incl. `okf-journal`) |
| `skills/_archive/` | One-shot/migrated host skills (not primary routing) |
| `skills/okf-ingest/stages/` | Single-URL ingest stage contracts |
| `skills/okf-ingest-channel/stages/` | Channel pipeline stage contracts |
| `_config/` | conventions, glossary, **taxonomy** (extensible FBC reference) |
| `tools/` | `okf.py`, `ingest.py`, validation |
| `themes/` | Cross-domain synthesis overlays |
| `specs/` | Feature specs (spec-kit) |
| `rules/` | Path access + agent constraints |
| `inbox/` | Ingest staging |

## Domains
`life` · `people` · `orgs` · `documents` · `tools` · `specs` · `skills` · `learning` · `creators` · `work`

## Compile loop (Karpathy ↔ OKF)
| Stage | OKF |
|-------|-----|
| Raw | `raw/`, `inbox/` |
| Compile | ingest skills + `stages/` |
| Wiki | `concepts/**`, `index.md`, hubs |
| Q&A | `okf search` / agent + cite concept paths |

## Agent load order
1. This file  
2. `CONTEXT.md` → pick task row  
3. Only the skill / stage / concept paths that row names  
4. `AGENTS.md` or `_config/*` only when the stage needs the deep rule  

## Path access
See `rules/path-access-control.md` before touching non-listed paths.

## Adapters
Prefer universal root files (`IDENTITY`/`CONTEXT`/`AGENTS`/`README`). Optional host stubs (`CLAUDE.md`, `GEMINI.md`) should only point at ICM load order — not host-specific packaging requirements.
