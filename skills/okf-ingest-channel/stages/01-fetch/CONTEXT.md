---
type: skill
---

# Stage 01 — Fetch transcripts

> One job: immutable raw transcripts on disk. No concept writing.

## Inputs
- YouTube channel handle/URL
- Optional: `--since`, `--limit`, `--delay`

## Outputs
- `raw/youtube/<slug>.md` (type raw-transcript, immutable)
- `raw/youtube/manifest.json`

## Mechanical
```bash
uv run skills/okf-ingest-channel/scripts/fetch_transcripts.py @ChannelHandle --output-dir ./raw/youtube
# flags: --limit N | --since 1y | --delay 3.0
```

## Done when
- [ ] Manifest lists fetched videos
- [ ] Transcript files exist for in-scope videos

## Next
→ `../02-extract/CONTEXT.md`
