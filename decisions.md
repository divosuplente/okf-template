---
type: infrastructure
---

# Decisions

Technical decisions for the OKF personal brain. Newest first. Each entry: decision, rationale, and any alternatives rejected.

## 2026-08-06 — Agent-surface optimization

### D-022 Vault SSOT for all okf-* skills + journal primary
**Decision** (2026-08-06): Every `okf-*` skill used by host agents must live under vault `skills/` (import from external sources). One-shot migration/debug/audit skills go to `skills/_archive/`. Primary session skills: core, query, journal, ingest, batch-ingest, ingest-channel, icm-sync, aaak-compression (+ deprecated folder stub). **okf-journal** is required for private life/therapy notes — not a mode buried only inside generic ingest.
**Rejected**: Leaving journal only in global managed-skills; keeping all imported skills in primary routing.

### D-021 Connection-pass triage + theme body refresh
**Decision** (2026-08-06): Treat automated Related links as proposals: drop weak pairing tags (`path`,`repo`,`test`,`personal`,`code-quality`,`<example-tag`,…); convert same-slug cross-domain hits to `## Also filed as` pending merge; keep high-signal topical bridges. Theme files must use path-based counts and current hubs, not pre-subdomain narrative.
**Rejected**: Leaving false positives in the graph; counting themes by overloaded tags alone.

### D-020 Public README + zero untagged + connection/theme pass
**Decision** (2026-08-06): Ship root `README.md` for eventual public packaging (methodology sources, portable setup, privacy export gate). Enforce **every concept has ≥1 tag**. Run corpus connection pass (body-overlap cross-domain Related links + orphan hub links) and refresh `themes/` overlays — without keyword domain reclassification.
**Rejected**: Leaving hubs untagged; host-specific public docs only.

### D-019 Close deferred agent-surface items (portable, no host-specific adapter)
**Decision** (2026-08-06): Finish remaining plan items without a host-specific adapter: (1) channel ICM stages `skills/okf-ingest-channel/stages/01`–`08`; (2) `okf icm-sync` CLI; (4) AGENTS progressive disclosure pointing schema/tags/types/visibility at `_config/*`; (5) structural `map` tags on untagged hubs; (6) universal IDENTITY/CONTEXT/AGENTS only.
**Rationale**: User prefers portable multi-platform entry over host-specific adapters. Corpus P3 is navigation/tag hygiene, not FBC reclassification.
**Rejected**: host-specific adapter; keyword domain reclassification of untagged non-structural concepts.

### Agent-surface metrics (baseline after D-018/D-019)
- AGENTS.md ~11–14KB single Operating Contract (was ~26KB duplicated)
- Compressed skills (SKILL.md): okf-core/ingest/batch/channel ~1.6–1.9KB each; dual-layer AAAK retained
- `okf doctor`: 0 errors; `okf icm-sync`: 6/6 skills routed
- Unit tests: 40 passed (`tools/tests` via `tools/.venv`)
- Tag pairs `agent`/`agents` and `self-hosted`/`self-hosting` already singular-normalized in corpus
- Untagged concepts reduced by tagging structural hubs/maps with `map` (remainder need FBC, not auto-tag)

### D-018 Agent-surface: single AGENTS, taxonomy reference, mechanical tools
**Decision**: Optimize agent instructions/skills/tools without corpus-wide re-link campaigns: (1) single-copy `AGENTS.md`; path-access solely via `rules/path-access-control.md`; (2) `_config/taxonomy.md` as **extensible reference** for known domains/subs/tag-*cleanup* — **not** a deterministic classifier; FBC (full-body read) remains mandatory and may extend the map; (3) keep AAAK dual-layer (`SKILL.md` lossy agent view + `SKILL.full.md` SSOT); (4) `okf relink` must not rewrite root orientation paths; (5) `okf doctor` for instruction integrity; (6) `tools/ingest_postprocess.py` mechanical only (noise tags/garbage-slug flags) — never assigns domain/sub/semantic tags; (7) external context tools are optional/local — must not hard-block portable commits.
**Rationale**: Token and consistency wins come from dedupe and shared reference, not from keyword classification (which contradicts explicit FBC policy) or removing AAAK.
**Rejected**: Closed-world taxonomy enums; single-file skills without `.full.md`; auto domain assignment in scripts; requiring external tools on all machines.
**Refs**: plan OKF agent-surface optimization; D-017 ICM overlay.

## 2026-08-06 — ICM orientation overlay

### D-017 Apply ICM as thin vault overlay + staged ingest only
**Decision**: Adopt Interpretable Context Methodology as a **hybrid**: (1) quick-mode orientation files `IDENTITY.md`, `CONTEXT.md`, and short `_config/` slices; (2) full-mode numbered stage contracts only under `skills/okf-ingest/stages/` (01 snapshot → 04 relink/index/log); (3) `skills/okf-icm-sync` to keep routing aligned with disk. Do **not** restructure `concepts/` into pipeline stage folders. Agent session start is IDENTITY → CONTEXT → skill/stage; `AGENTS.md` remains the deep operating contract.
**Rationale**: OKF already matches ICM philosophy (plain markdown, scripts for mechanical work, raw→compile→wiki). The pain was monolithic context load and underspecified multi-step ingest cleanup, not the domain wiki layout. Full-mode ICM across the corpus would fight progressive disclosure and hub/subdomain taxonomy.
**Rejected**: Full ICM renumbering of `concepts/`; replacing `AGENTS.md` with a generic external scaffold; copying Claude-global ICM skills instead of vault-native `skills/okf-*`.
**Refs**: arXiv:2603.16021; https://github.com/ktnCodes/icm-template; concepts `tools/agents/orchestration/interpretable-context-methodology`, `tools/agents/orchestration/okf-icm-layer`.

## 2026-07-11 — OKF Brain becomes sole source of truth

### D-014 Vault is the SSOT — origins retired
**Decision**: This OKF vault is the sole source of truth. The `<origin-1>` and `<origin-2>` external origin repositories are no longer read from, synced against, or treated as authoritative. Historical `source:` provenance refs and `raw/` snapshots are kept as a read-only archive of where content originally came from, but they are informational only.
**Rationale**: The vault has been fully ingested and is self-contained. Maintaining origin-coupled logic (path resolvers, origin-based privacy heuristics, cross-origin merge rules, non-destructive-to-origin constraints) adds complexity with no remaining benefit.
**Rejected**: Strip all provenance and delete `raw/` (loses historical trace of where content came from — useful for attribution and conflict resolution); keep origin-reading logic "just in case" (dead code that implies a relationship that no longer exists).

### D-015 Privacy by domain, overridable
**Decision**: Remove the automatic `<origin-1>`-derived → `private` privacy heuristic. Replace it with a domain-based default: personal domains (`life`, `people`, `orgs`, `documents`) default to `private` — covering journal entries, therapy notes, health records, and personal topics. All other domains default to `shareable`. The author can override either default by setting `visibility` explicitly. Lint warns when a personal-domain concept is marked `shareable` so the override is confirmed intentional.
**Rationale**: With origins retired, there is no origin signal to drive an auto-rule. Personal content (journals, therapy, health, life topics) should default to `private` without requiring the author to remember every time — forgetting risks leaking sensitive content. Domain is a reliable proxy for personal-ness without being origin-coupled. The lint warning catches accidental `shareable` overrides in personal domains.
**Rejected**: Pure explicit per-concept with no default (forgetting to set `private` on a journal entry risks a privacy leak); keep the `<origin>:` prefix check in lint (checks a condition that can no longer arise for new content).

### D-016 Ingest tool transforms to URL/document ingest
**Decision**: `tools/ingest.py` is rewritten to ingest a single URL or local document into the vault (snapshot to `raw/`, create a concept with frontmatter + provenance). The bulk origin-reading logic (`map_<origin-1>`, `map_<origin-2>`, `walk_origin`, cross-origin merge) is removed.
**Rationale**: The bulk ingest from origins is complete and will not be re-run. Future ingests are incremental — a URL, a document, or a file — not a full re-scan of a retired origin.
**Rejected**: Delete `ingest.py` entirely (the concept-rendering + raw-snapshot logic is still useful for new ingests); keep bulk ingest pointed at `raw/` snapshots (rebuilding concepts from snapshots is not a recurring need; adds complexity).

## 2026-06-29 — OKF Brain v1 foundational decisions

### D-001 Canonical home
**Decision**: The merged system lives in a new repository at `<repo-root>`. `<origin-1>` and `<origin-2>` are read-only inputs.
**Rationale**: A clean canonical target avoids entangling the merge with either origin's existing structure/history.
**Rejected**: Making `<origin-1>` or `<origin-2>` the canonical host (couples the merge to one origin's conventions).
> **Superseded by D-014 (2026-07-11)**: The vault is now the SSOT. `<origin-1>` and `<origin-2>` are retired as inputs.

### D-002 Merge mode = non-destructive ingest
**Decision**: Copy/normalize from the origins into `okf`; never modify the origin repos.
**Rationale**: Safety and reversibility; originals remain a source of truth during the transition.
> **Superseded by D-014 (2026-07-11)**: Origins are no longer read or modified. The non-destructive constraint is moot.

### D-003 Ingest scope
**Decision**: Target scope is all of `<origin-1>/**` plus all of `<origin-2>/**`. v1 performs a pilot ingest only; full batch ingest is deferred.
**Rationale**: Validate schema + tooling on a high-value slice before committing the long tail.
> **Superseded by D-014/D-016 (2026-07-11)**: Bulk ingest from origins is complete and retired. Future ingest is incremental (URL/document).

### D-004 Conflict policy = merged canonical + provenance
**Decision**: When a concept exists in both origins, produce one merged canonical concept that records both origins in provenance; flag genuine conflicts for review rather than dropping a claim.
**Rejected**: Always prefer one origin (loses information).
> **Superseded by D-014 (2026-07-11)**: Cross-origin merge no longer occurs. Existing merged concepts retain their dual provenance as a historical record; new concepts have a single source.


### D-005 Normalization = hybrid
**Decision**: Normalize high-value concepts into canonical OKF files first; keep long-tail content reachable as linked raw artifacts until normalized on demand.
**Rejected**: Full upfront normalization (slow, risky); index-only (too little value early).

### D-006 Top-level structure
**Decision**:
```
okf/
  index.md            # progressive-disclosure root catalog
  log.md              # append-only history
  AGENTS.md           # operating contract / conventions (read before editing)
  decisions.md        # this file
  concepts/           # merged canonical OKF concept files (by domain)
  raw/<origin-1>/  raw/<origin-2>/   # verbatim source snapshots
  provenance/         # concept <-> origin map (md + json)
  tools/              # custom search + viewer (with tools/tests/)
```
**Rationale**: Separates verbatim sources, canonical concepts, provenance, and tooling cleanly.

### D-007 Frontmatter schema
**Decision**: OKF-compliant YAML frontmatter. `type` required (OKF). `visibility` (`private`|`shareable`) required extension. Recommended: `title`, `description`, `domain`, `tags`, `resource`, `timestamp`, `status`. Provenance carried in a `source` list. Origin-specific keys are preserved. Keys are `snake_case` (aligns with `<origin-1>` GL-002).
**Rationale**: One standard reconciles `<origin-1>`'s YAML conventions and `<origin-2>`'s `**Key:** value` metadata; unknown keys preserved per OKF.

### D-008 Unified `type` vocabulary
**Decision**: Single vocabulary spanning both origins: `key-element`, `goal`, `habit`, `project`, `topic`, `person`, `organization`, `document`, `tool`, `spec`, `skill`, `learning`, `source`, `playbook`, `reference`, `note` (fallback). Finer grouping via `domain` + `tags`.

### D-009 Sensitivity model = visibility field
**Decision**: Per-concept `visibility` (`private`|`shareable`), filtered at export. Anything derived from `<origin-1>` defaults to `private`. Export must never emit `private` concepts.
**Rejected**: Physically separate private/shareable directories (less flexible); no boundary (unsafe given product intent).
> **Partially superseded by D-015 (2026-07-11)**: The `<origin-1>`-derived auto-private heuristic is replaced by a domain-based default (personal domains → `private`). Privacy is overridable per concept. The visibility model and export filter remain.

### D-010 v1 capabilities
**Decision**: Ship the merged corpus + operating contract + the three living-wiki operations (ingest, query, lint) + local tooling (search + viewer).

### D-011 Tooling = custom, no external dependencies
**Decision**: Build our own lightweight tools. Indexer/search as a Python CLI run via `uv` (stdlib only, BM25-style ranking, emits a regenerable index). Viewer as a single self-contained HTML file (vanilla JS, plain CSS, embedded SVG icons — no Tailwind, no external deps) that renders the concept graph and filters by visibility.
**Rationale**: Matches the no-external-deps choice and the LLM-agnostic, portable-core philosophy. Tests live in `tools/tests/` per project convention.
**Rejected**: Adopting `qmd` + an off-the-shelf visualizer (adds external dependency).

### D-012 Spec process = spec-kit only
**Decision**: Record specs with spec-kit (`specify`), `generic` integration, commands under `.specify/commands/`. agent-os is no longer used.
**Note**: The global rule referencing agent-os (id `pSqUInOOG2ClDoEPFe8eN1`) is outdated and to be updated by the user.

### D-013 Version control
**Decision**: Use `git`. Each spec gets its own branch; this work is on `spec/okf-brain-v1` (spec-kit feature id `001-okf-brain-v1`). Initial commit established the repo; `main` is the base branch.
