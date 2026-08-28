---
type: infrastructure
---

# OKF Vault — Setup & Operations Runbook

How to bring this vault up on a new machine and operate it. Agents: read this
before touching tooling; the path-access rule (`rules/path-access-control.md`)
governs what you may touch.

## 1. Prerequisites

- **uv** (Python package manager) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Python 3.11+** (uv manages its own; the venv pins 3.11)
- **git**, **gh** (GitHub auth: `gh auth login`)
- Optional: **tesseract** (`brew install tesseract`) — only for OCR of scanned
  PDFs; not needed for the standard pipeline
- Optional: **Calibre** (`brew install --cask calibre`) — only for MOBI/AZW
  books; not needed for PDF/EPUB

## 2. Clone & install

```bash
git clone https://github.com/<your-org>/2ndBrain.git && cd 2ndBrain
uv venv
```

### If `pypi.org` is reachable

```bash
uv pip install -e "tools/book-to-skill[all]" pymupdf pix2tex timm \
  numpy scipy sympy matplotlib plotly jupyter notebook ipykernel symderive
```


### Optional: DuckDB for ad-hoc SQL queries

```bash
uv pip install duckdb
```

If PyPI is blocked:

```bash
uv pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ duckdb
```

Enables `okf sql` — run arbitrary SQL over the corpus (concepts, tags, links).
In-memory only; no disk footprint. See **§6.1 SQL queries** below.

### If `pypi.org` is blocked (supply-chain firewall)

Use the Tsinghua mirror for all packages:

```bash
uv pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
  -e "tools/book-to-skill[all]" pymupdf pix2tex timm \
  numpy scipy sympy matplotlib plotly jupyter notebook ipykernel symderive
```

### What this installs

**Book pipeline (§5):**

| Package | Used by | Purpose |
|---|---|---|
| `book-to-skill` (editable) | `book-to-skill` CLI | text extraction (pypdf/pdfminer/docling) |
| `docling` | `--mode technical` | layout-aware extraction, tables, **figure crops** |
| `pymupdf` | `tools/formula-snap.py` | render formula crops |
| `pix2tex` + `timm` | `formula-snap.py --latex` | image → LaTeX OCR (~97MB model, first run) |
| `ebooklib`, `beautifulsoup4`, etc. | `book-to-skill` | EPUB/DOCX/HTML extraction |

**Physics/math study stack (§8):**

| Package | Purpose |
|---|---|
| `numpy` | Vector/matrix computation, linear algebra |
| `scipy` | ODE solvers (`solve_ivp`), integration, optimization, special functions |
| `sympy` | Symbolic algebra — exact derivatives, integrals, equation solving |
| `matplotlib` | Static plots — trajectories, fields, functions |
| `plotly` | Interactive browser plots — 3D surfaces, phase portraits |
| `jupyter` + `notebook` + `ipykernel` | Interactive notebooks for lesson code |
| `symderive` | Agent-native symbolic math (pipe-based API wrapping SymPy/PySR/CVXPY) |

## 3. Verify

```bash
.venv/bin/book-to-skill --check                              # per-format extractor report
.venv/bin/python -c "import pymupdf, pix2tex"                # book pipeline OK
.venv/bin/python -c "import numpy, scipy, sympy, matplotlib, plotly, symderive; print('Study stack OK')"
.venv/bin/python tools/okf.py doctor                         # vault integrity
```

## 4. What lives where

| Path | Contents | Committed? |
|---|---|---|
| `books/slices/<book>/` | per-chapter PDF slices + formula snapshots | **yes** — reference material |
| `.venv/` | Python environment | **no** (gitignored) |
| `~/.cache/huggingface/` | docling/pix2tex model weights | **no** |

## 5. The book pipeline (operating procedure)

For each book, in order:

```bash
# 1. Slice into per-chapter PDFs (committed to books/slices/)
.venv/bin/python tools/book-slicer.py <path-to-book>.pdf

# 2. Extract text + figures (technical mode for math/tables; text for prose)
BOOK_SKILL_WORKDIR=/tmp/<book> .venv/bin/book-to-skill <book> --mode technical

# 3. Snap formulas to WebP + LaTeX (per chapter slice)
.venv/bin/python tools/formula-snap.py books/slices/<book>/01-chapter-1.pdf --latex

# 4. Fold into concepts per skills/okf-book-ingest/SKILL.md
```

Then follow `skills/okf-book-ingest/SKILL.md` (INGEST + CHAPTER procedures) to
create parent book concepts and per-chapter concepts, embedding the formula
crops and linking the slices.

## 6. Vault maintenance

```bash
.venv/bin/python tools/okf.py index      # rebuild search index
.venv/bin/python tools/okf.py lint       # health check (never hard-fails)
.venv/bin/python tools/okf.py relink --dry-run   # canonicalize links
```

### 6.1 SQL queries (requires duckdb)

```bash
.venv/bin/python tools/okf.py sql "SELECT domain, COUNT(*) FROM concepts GROUP BY domain"
.venv/bin/python tools/okf.py sql "SELECT tag, COUNT(*) as n FROM tags GROUP BY tag ORDER BY n DESC LIMIT 10"
.venv/bin/python tools/okf.py sql "SELECT c.id, c.title FROM concepts c WHERE c.id NOT IN (SELECT target_id FROM links)"
echo "SELECT * FROM concepts WHERE visibility='shareable' AND domain='tools'" | .venv/bin/python tools/okf.py sql
```

Queries run in-memory over a snapshot of the corpus. Three tables available:

| Table | Columns |
|-------|---------|
| `concepts` | `id`, `path`, `domain`, `type`, `visibility`, `title`, `status`, `body` |
| `tags` | `concept_id`, `tag` |
| `links` | `source_id`, `target_id` |

Output is TSV — pipe to `column -s$'\t' -t` for columns, or to `jq`/`awk` as needed.

## 7. Agent operating notes

- **Path access**: `rules/path-access-control.md` is the sole allow/deny list.
  `books/` is allowed; anything outside the vault root requires explicit user
  permission.
- **Skills**: invocable skills live in `skills/` (e.g. `okf-book-ingest`,
  `okf-study`, `okf-review`). Refer to them by folder name.
- **Session start (ICM)**: `IDENTITY.md` → `CONTEXT.md` → the specific
  skill/stage needed. Do not dump the whole vault.
- **The venv is not committed** — always run tooling via `.venv/bin/...` or
  `uv run ...`, never bare `python3` (system Python lacks the deps).
- **Slices are committed; originals are not.** Never copy originals into the repo. If a slice is missing, regenerate it from the original with `book-slicer.py` (the original's path is recorded in the slice manifest).

## 8. Physics/Math Study Stack

For the physics and math self-study roadmaps. Installed in §2 alongside the book pipeline.

| Package | Purpose | Roadmap levels |
|---|---|---|
| `numpy` | Vector/matrix computation, linear algebra | All levels |
| `scipy` | ODE solvers (`solve_ivp`), integration, optimization, special functions | Physics 1–8, Math 4–15 |
| `sympy` | Symbolic algebra — exact derivatives, integrals, equation solving, checks | Physics 5–7, Math 2–19 |
| `matplotlib` | Static plots — trajectories, fields, functions | All levels |
| `plotly` | Interactive browser plots — 3D surfaces, phase portraits | Physics 6, Math 11–14 |
| `jupyter` + `notebook` + `ipykernel` | Interactive notebooks for lesson code | All levels |
| `symderive` | Agent-native symbolic math — pipe-based API wrapping SymPy/PySR/CVXPY, designed for composable agent workflows | All levels |


## 9. Agent hooks (OMP extensions)

OMP supports **project-local extensions** — small `.js` files that hook into
agent lifecycle events (`session_start`, `tool_call`, `session_stop`). They run
on every session and can block tool calls, run pre-flight checks, or execute
background work.

### Two-layer architecture

| Layer | Path | Scope |
|---|---|---|
| **Global loader** | `~/.omp/agent/extensions/project-loader.ts` | Discovers & loads local extensions |
| **Local extensions** | `.omp/extensions/*.js` | Project-specific hooks (shipped with repo) |

### Setup

1. **Install the global loader** (one-time, NOT shipped by OMP):
   Place `project-loader.ts` in `~/.omp/agent/extensions/`. It reads `.omp/extensions/*.js`
   from the current project on every `session_start` and invokes them.

```ts
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import * as fs from "fs";
import * as path from "path";

export default function (pi: ExtensionAPI): void {
  pi.on("session_start", async (_event, ctx) => {
    const localDir = path.join(ctx.cwd, ".omp", "extensions");
    if (!fs.existsSync(localDir)) return;

    const files = fs.readdirSync(localDir).filter(f => f.endsWith(".js"));
    if (files.length === 0) return;

    for (const file of files) {
      try {
        const mod = await import(path.join(localDir, file));
        if (typeof mod.default === "function") mod.default(pi);
        if (typeof mod.onSessionStart === "function") await mod.onSessionStart(_event, ctx);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.warn(`Project extension ${file} failed to load: ${msg}`);
      }
    }
  });
}
```

2. **Write local extensions** in `.omp/extensions/`. Drop a `.js` file there;
   it auto-loads on the next session. No config needed.

### Extension contract

Each extension is a CommonJS/ESM module with a default export:

```js
export default function (pi) {
  pi.on("tool_call", async (event, ctx) => {
    // event: { toolName, input }
    // ctx: { cwd }
    // Return { block: true, reason: "..." } to veto the tool call
  });

  pi.on("session_start", async (_event, ctx) => {
    // Runs once at session boot; ctx.cwd = repo root
  });
}
```

### Common patterns

- **Pre-flight guards**: validate frontmatter or schema before `write`/`edit`
- **Path guards**: enforce allow/deny lists parsed from `rules/*.md`
- **Auto-sync**: run `git pull --rebase` on first tool call

This is OMP-specific. Other harnesses (Claude Code, Cursor, Codex) have
different extension mechanisms — check their documentation for equivalents.
