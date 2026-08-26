---
type: skill
---

# Stage 03 — Cleanup

> One job: fix ingest debt so concepts are correctly named, placed, and non-duplicate.  
> **Mandatory** after `ingest.py` or any automated stub.

## Inputs
- Concept paths from stage 02 (or recent ingest)
- Known caveats (`AGENTS.md` / skill IC block)

## Mechanical helper (optional)
```bash
python3 tools/ingest_postprocess.py --dry-run --paths <concept.md> …
```
Strips noise tags / flags garbage slugs only — **never** classifies domain or semantic tags.

## Checklist
1. **Slug** — Rename garbage path-derived slugs (`users-ima-okf-inbox-…`) to title-derived kebab slugs.
2. **Subdomain** — Move from flat `concepts/<dom>/` into correct `sub` / `ssub` (ingest CLI has no subdomain flag).
3. **Frontmatter** — Fix mangled titles (emoji, raw URLs, triple quotes); set real `description`; tag audit.
4. **Duplicates** — If concept already exists, merge into higher-quality file; delete true dupes.
5. **Links** — Update hub + internal links after moves/renames.
6. **Inbox guard** — Move inbox item to `inbox/processed/` only if ≥1 concept created; else `inbox/failed/` + reason.
7. **Purge stale processed** — Delete any file in `inbox/processed/` that has been sitting there for more than 7 days (mtime-based — `mv` preserves mtime, so it reflects time in the folder). Only the `processed` subfolder is touched:
   ```bash
   find "$VAULT/inbox/processed" -maxdepth 1 -type f -mtime +7 -delete
   ```

## Outputs
- Final concept paths (post-rename/move)
- Short cleanup report (renames, moves, deletes, merges)

## Done when
- [ ] No garbage slugs in this batch
- [ ] Paths match taxonomy
- [ ] No accidental duplicate files for this batch
- [ ] Visibility still correct after moves (domain defaults)

## Human gate
Confirm merges/deletes when two rich concepts collide.

## Next
→ `../04-relink-index/CONTEXT.md`
