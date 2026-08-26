---
type: skill
---

# Stage 06 — Validate

> One job: deterministic checks. Prefer scripts.

```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
python3 tools/okf.py relink   # only if needed
python3 tools/validation/audit.py
python3 tools/validation/citation_check.py
python3 tools/validation/sweep.py
python3 tools/ingest_postprocess.py --dry-run --paths <new concepts…>
```

## Next
→ `../07-gap-sweep/CONTEXT.md`
