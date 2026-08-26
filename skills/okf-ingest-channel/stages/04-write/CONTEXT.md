---
type: skill
---

# Stage 04 — Write concept pages

> One job: prose against frozen manifest + FBC path placement.

## Inputs
- `tools/manifest.json`
- Supporting raw transcripts / extractions

## FBC
Placement still checked against full content + `_config/taxonomy.md` (extensible). Manifest is structural contract; path must not contradict body meaning.

## Outputs
- `concepts/**/<slug>.md`
- Creator + tool concepts as needed
- Hub backlinks (depth-conditional)

## Quality
- 250–600 words dense synthesis where appropriate
- `## Sources` with timestamped quotes
- Tag cleanup per `@tax` (mechanical rules only after FBC tags chosen)

## Also
Single-video incremental path may use `skills/okf-ingest` stages 03–04 after write.

## Next
→ `../05-polish/CONTEXT.md`
