---
type: skill
---

# Stage 04 — Relink · index · log

> One job: make the corpus mechanically consistent and record the run. Prefer scripts.

## Inputs
- Final concept paths from stage 03
- Cleanup report (for log prose)

## Commands (in order)
```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
# only if dry-run shows rewrites:
python3 tools/okf.py relink
```

### Auto-cross-link (run after index)
After `okf index`, for each concept created/updated in this run:
```bash
python3 tools/okf.py link --auto --concept <concept-id> --max 3 --min-score 5 --quiet
```
- Scopes BM25/tag matching to the single new concept (~0.5s per concept)
- Adds top 3 bidirectional links under `## Related Concepts` with clean prose
- Filters noisy hubs; skips already-linked pairs
- Run once per new concept, not globally
### Optional deeper checks (channel-scale runs)
```bash
python3 tools/validation/audit.py
python3 tools/validation/sweep.py
# citation_check when ## Sources + transcripts matter
```

## Outputs
- Regenerated `tools/index.json`, `provenance/map.json` (+ `map.md` if generated)
- `index.md` count refresh if totals changed
- Append **one** `log.md` entry:

```markdown
## [YYYY-MM-DD] ingest | <one-line summary>
- Concepts: `path1`, `path2`, …
- Raw: `raw/…`
- Notes: <cleanup / skips>
- Lint/index: <brief result>
```

## Done when
- [ ] index rebuilt
- [ ] lint reviewed (0 new errors ideal; warnings understood)
- [ ] relink applied only when needed
- [ ] log entry lists **all** concepts created/updated this run

## Human gate
Read lint warnings that touch privacy or unexpected domains.

## Next
Stop. Session complete for this ingest — or route back to `CONTEXT.md` for another task.
