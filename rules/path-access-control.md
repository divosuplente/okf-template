---
type: infrastructure
---

# Path Access Control Rule

**Purpose**
Define which paths agents may access by default, and which require explicit user permission.

**Allowed Paths (read/write)**
- `skills/` – usable agent skills (includes stage contracts under `skills/*/stages/`)
- `inbox/` – temporary ingest staging
- `concepts/` – OKF concept files (the vault's core content)
- `tools/` – CLI tooling (`okf.py`, `ingest.py`, migration scripts)
- `provenance/` – provenance maps and generated artifacts
- `_config/` – ICM short reference slices (conventions, glossary)
- `themes/` – cross-domain synthesis overlays
- `specs/` – feature specs
- `books/` – per-chapter book slices + formula snapshots (committed reference material; originals stay outside the repo)
- `rules/` – agent path/policy rules (this file)
- `.omp/` – project-local OMP extensions for hooks and guards
- `IDENTITY.md`, `CONTEXT.md`, `AGENTS.md`, `decisions.md` – orientation + contract + decisions
- `log.md` – vault change log
- `index.md` – vault catalog (prefer `okf.py index` to regenerate; hand-edits will be overwritten)

**Read-Only Paths**
- `raw/` – verbatim source snapshots (archive; never edit)

**Blocked Paths**
- Any path that resolves outside the repo root requires explicit user permission before access
- Any path not listed above requires explicit user permission before access.

**Enforcement**
- Agents **MUST** check this rule before accessing paths not listed under **Allowed** or **Read-Only**.
- If a path is blocked, the agent must either abort the operation or request explicit user permission.
- User-granted permission for a specific task carries across the session — no need to re-confirm for each file within the approved scope.
