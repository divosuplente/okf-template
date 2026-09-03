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
|----------|----------|
| Web article | `raw/web/<slug>.md` |
| YouTube | `raw/youtube/<video_id>.vtt` (verbatim VTT only — no .md transcript) |
| Inbox copy | `raw/inbox/<slug>.md` (or existing convention) |
| Other doc | `raw/<bucket>/<slug>.md` |

Each raw file SHOULD include: original URL/path, fetch date, method, and full verbatim body (VTT for YT — do not write a plain-text transcript to raw/).

## YouTube VTT preprocessing (mandatory)
Raw VTT auto-captions contain `<c>` timing tags, overlapping cues, and duplicate lines. A 5-hour video can produce 74K+ lines of noisy markup. **Always preprocess VTT before reading:**
1. Strip VTT headers, timing lines, cue identifiers
2. Remove HTML tags (`<c>`, `</c>`, etc.) and unescape HTML entities
3. Deduplicate overlapping/identical cues
4. Output clean prose to `/tmp/okf_yt_<id>_plain.txt`
5. For long videos (>30 min), split into ~800-word chunks for systematic reading. Read ALL chunks — never sample.

The preprocessed file is a working intermediate — it does NOT go in `raw/`. Only the verbatim `.vtt` is the raw snapshot. The knowledge extract goes in `concepts/.../references/` (Stage 02).

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
