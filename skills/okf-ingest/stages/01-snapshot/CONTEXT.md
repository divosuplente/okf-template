---
type: skill
---

# Stage 01 — Snapshot

> One job: capture source material verbatim on disk. No concept quality work here.
> **Prerequisite:** Stage 00 (preflight) must complete before this stage.

## Inputs
- Preflight answers from `../00-preflight/CONTEXT.md` (domain, visibility, type, conflict decision, tag plan, cross-link targets)
- User URL, local file path, inbox item, or yt-dlp target
- Optional user `#hashtags` (carry forward; do not apply yet)

## Outputs (write)
| Kind | Path pattern |
|------|----------------|
| Web article | `raw/web/<slug>.md` |
| YouTube | `raw/youtube/<video_id>.md` |
| Inbox copy | `raw/inbox/<slug>.md` (or existing convention) |
| Other doc | `raw/<bucket>/<slug>.md` |

Each raw file SHOULD include: original URL/path, fetch date, method, and full verbatim body (description + transcript for YT).

## Mechanical (prefer scripts / CLI)
```bash
# URL/doc mechanical path when appropriate:
python3 tools/ingest.py <url|file>   # may also stub a concept — still run 02–03
# YouTube metadata + subs:
yt-dlp --dump-json --write-auto-sub --skip-download --sub-langs en --sub-format vtt -o "/tmp/okf_yt_<id>" "URL"
```

## Done when
- [ ] Raw snapshot exists and is complete enough to re-derive a concept offline
- [ ] `raw/` not modified for old archives; only new snapshots added
- [ ] Handoff note: source kind (web|yt|inbox), paths written, suggested domain guess (non-binding)

## Human gate
Optional skim of raw path if fetch looks truncated or paywalled.

## Next
→ `../02-concept/CONTEXT.md`
