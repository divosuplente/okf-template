---
type: infrastructure
---

# OKF Brain — Index

Progressive-disclosure catalog for this Open Knowledge Format corpus. This vault is the sole source of truth. Agents start with `IDENTITY.md` → `CONTEXT.md`, then use this index to see what exists before opening individual concepts.

## Domains
- [Life](concepts/life/) — key elements, goals, habits, projects, topics (personal).
- [People](concepts/people/) — individuals.
- [Organizations](concepts/orgs/) — companies, clinics, vendors.
- [Documents](concepts/documents/) — identity/records stubs.
- [Tools](concepts/tools/) — AI/dev tools and ecosystem utilities.
- [Specs](concepts/specs/) — specifications and standards.
- [Skills](concepts/skills/) — reusable expertise / skill packages.
- [Learning](concepts/learning/) — articles, courses, talks.
- [Creators](concepts/creators/) — YouTube channels, content creators, authors.
- [Work](concepts/work/) — enterprise / internal notes (default private).

## Concepts
**0 concepts** (run `okf index` after adding concepts).

## Navigation
- `log.md` — chronological history of ingests, queries filed back, and lint passes.
- `provenance/map.md` — which source(s) each concept came from (generated).
- `tools/` — `okf.py` (`index`/`search`/`lint`/`relink`/`view`), `ingest.py`, `viewer.html`.
- `themes/` — knowledge domain synthesis files (create as needed).

## Agent orientation (ICM)
- [`IDENTITY.md`](IDENTITY.md) — Layer 0 workspace map
- [`CONTEXT.md`](CONTEXT.md) — Layer 1 task router
- [`_config/`](_config/) — conventions, glossary, taxonomy (extensible reference)

## Skills
- [`okf-core`](skills/okf-core/) — base vault operations skill (index, lint, relink, view)
- [`okf-ingest`](skills/okf-ingest/) — single-URL/video ingest workflow
- [`okf-batch-ingest`](skills/okf-batch-ingest/) — batch folder ingest
- [`okf-ingest-channel`](skills/okf-ingest-channel/) — batch YouTube channel transcript fetcher + ingest
- [`okf-query`](skills/okf-query/) — search & cite from the vault
- [`okf-journal`](skills/okf-journal/) — private journal/therapy/session note ingest (merged skill)
- [`okf-review`](skills/okf-review/) — spaced repetition review scheduling
- [`okf-icm-sync`](skills/okf-icm-sync/) — keep IDENTITY/CONTEXT aligned with disk
- [`okf-study`](skills/okf-study/) — study loop with retrieval practice
- [`okf-book-ingest`](skills/okf-book-ingest/) — textbook chapter ingestion
- [`okf-teach`](skills/okf-teach/) — teaching workspace engine
- [`okf-problem-journal`](skills/okf-problem-journal/) — problem tracking for study
- [`okf-tasks`](skills/okf-tasks/) — cross-session task tracking
- [`okf-aaak-compression`](skills/okf-aaak-compression/) — skill compression
- [`analyze-sessions`](skills/analyze-sessions/) — session log analysis
- [`teach`](skills/teach/) — lesson engine
- [`visualize`](skills/visualize/) — diagram generation
- [`snippets`](skills/snippets/) — snippet management
- [`frontend-debug`](skills/frontend-debug/) — frontend debugging
