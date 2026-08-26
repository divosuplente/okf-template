---
type: skill
---

# Stage 03 — Canonicalize (serial barrier)

> One job: freeze taxonomy/manifest so writers cannot invent divergent pages.

## Inputs
- All `tools/extractions/*.json` for the run

## Outputs
- `tools/manifest.json` — canonical pages, paths, related, quotes
- `tools/taxonomy.json` — theme → slug[] (themes overlay; not domain FBC map)

## Steps
1. Aggregate by normalized slug
2. Merge near-duplicates
3. Page threshold: ≥2 videos OR one substantial deep-dive
4. Assign themes
5. Freeze — no structural decisions after this

## Human gate
Review merge groups / threshold edge cases before write.

## Next
→ `../04-write/CONTEXT.md`
