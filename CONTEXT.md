---
type: infrastructure
---

# CONTEXT — OKF task router

> Layer 1. Answer: **Where do I go?**  
> Prerequisite: `IDENTITY.md`. Load only the skill/stage for the current task.

## Session start
1. Read `IDENTITY.md` (if needed).
2. Match the user request to a row below.
3. Open **one** skill/stage — not the whole `skills/` tree.
4. Human review gates between stages when quality is uncertain.

## Primary routing

| Task | Go to | Notes |
|------|--------|--------|
| Orient / how vault works | `IDENTITY.md` → `README.md` → `_config/*` → `AGENTS.md` if deep | Thin layers first |
| Query / what do I know | `skills/okf-query/` or `okf search` + concepts | Cite paths; no fabrication |
| Journal / therapy / private reflection | **`skills/okf-journal/`** | ALWAYS private; life/* via FBC |
| Ingest URL / video / article | `skills/okf-ingest/` + `stages/01`→`04` | FBC; not for private journals |
| Ingest folder / inbox batch | `skills/okf-batch-ingest/` | Alias: deprecated `okf-ingest-folder` |
| YouTube full channel | `skills/okf-ingest-channel/` + `stages/01`→`08` | Heavy pipeline |
| Post-ingest cleanup only | `skills/okf-ingest/stages/03-cleanup/` | Slugs, fm, dedupe |
| Index / lint / relink / doctor / view | `python3 tools/okf.py <cmd>` | After corpus changes |
| Verify ICM integration | `python3 tools/okf.py icm-sync` + `doctor` | |
| ICM routing sync | `python3 tools/okf.py icm-sync` | Optional skill: `okf-icm-sync` |
| AAAK compress skills | `skills/okf-aaak-compression/` | Meta only |
| Taxonomy / tags / domains | `_config/taxonomy.md` | Extensible; FBC mandatory |
| Themes | `themes/index.md` | Overlay nav |
| Specs | `specs/<id>/` | |
| Path access | `rules/path-access-control.md` | |
| Smoke check | `python3 tools/okf.py doctor` | |
| Deep vault ops | `skills/okf-core/` | |

## Ingest vs journal
- **Public/external content** → `okf-ingest` / batch / channel  
- **Personal/therapy/journal** → **`okf-journal` only** (private life/*)

## Archived skills
One-shot migration/audit/debug skills may live under `skills/_archive/` (not default routing).

## Do not
- Load every skill at session start  
- Mark journal/therapy content `shareable`  
- Renumber `concepts/` into pipeline folders  
- Treat `raw/` as editable truth  
