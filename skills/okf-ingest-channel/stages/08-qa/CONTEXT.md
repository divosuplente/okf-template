---
type: skill
---

# Stage 08 — QA

> One job: answerability + trap questions + recall sample.

## Checks
- 5–10 real questions answered only from concepts (cite paths)
- 3–5 traps → correctly "not covered"
- Sample videos: durable ideas have pages (target >90%)

## Close
- Update `index.md` counts if needed
- Enroll channel for tracking: `sqlite3 tools/channel_check.db "INSERT OR IGNORE INTO channels (handle, url, label) VALUES ('@Handle', 'https://www.youtube.com/@Handle/videos', 'Label')"`
- Append `log.md` entry for the channel run
- Stop or route via root `CONTEXT.md`
