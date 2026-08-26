---
type: skill
---

# Stage 02 — Extract

> One job: per-video structured JSON (concepts/entities/quotes). No wiki pages yet.

## Inputs
- `raw/youtube/*.md` from stage 01
- `_config/taxonomy.md` as **extensible reference** only

## FBC (mandatory)
Read **full** transcript body for each video. Propose domain/sub/ssub and tags from meaning; extend `@tax` if needed. Keyword tables are aids only.

## Outputs
- `tools/extractions/<slug>.json` (thesis, concepts[], entities[], quotes with timestamps)

## Rules
- Stable general slugs; verbatim quotes only
- Skip sponsor noise
- Batch 10–15 videos

## Next
→ `../03-canonicalize/CONTEXT.md` (only after ALL extractions for this run)
