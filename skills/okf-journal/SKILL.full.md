---
name: okf-journal
description: >-
  Journal entry and therapy/session note ingestion into the OKF brain. Triggered
  when user mentions journaling, therapy notes, therapy session, journal entry,
  personal reflection, or sensitive personal content to save. ALWAYS visibility:
  private. Domain life (usually life/personal).
  Never shareable export.
type: infrastructure
---

# OKF Journal — Private personal & therapy ingest

## Trigger patterns
- "journal", "therapy", "session notes", "journaling", "reflection", "log this session"
- Personal/sensitive content to save (mental health, recovery, private life events)

## Non-negotiable rules
- **ALWAYS** `visibility: private`
- **ALWAYS** personal-domain placement under `life/` (never `shareable`)
- **FBC:** read full entry body to choose subdomain and tags — see `_config/taxonomy.md` (extensible)
- **NEVER** mark journal entries `shareable` or include them in exports
- Prefer `skills/okf-journal` over generic ingest for this content (ingest defaults are often shareable)

## Type mapping
| Content | `type` |
|---------|--------|
| Therapy / session notes | `note` |
| Habit tracking | `habit` |
| Goals / intentions | `goal` |
| Topic reflections | `topic` |
| Life event docs | `note` |

## Path
`concepts/life/<subdomain>/journal-<YYYY-MM-DD>-<topic-slug>.md`

Examples:
- `concepts/life/personal/journal-2026-08-06-weekly-reflection.md`
- `concepts/life/personal/journal-2026-08-06-therapy-session.md`

## Frontmatter template
```yaml
---
type: note
visibility: private
title: <descriptive title>
description: <one-line summary>
domain: life
tags: [journal, therapy, <topic-tags-from-FBC>]
timestamp: <session date or today ISO>
status: active
source:
  - self:
---
```

## Body template
```markdown
# <Title>

## Session date
<YYYY-MM-DD>

## Summary
<1–2 sentences>

## Notes
<structured notes>

## Insights
<takeaways>

## Action items
- <next steps>

## Related
- [parent hub]
- [therapy / recovery concepts when relevant]
```

## Cross-link targets (resolve current paths)
Search first (`okf search`); paths may live under `life/personal/` after subdomain migration:
- therapy, recovery, journaling-therapy, urge-surfing, and related personal health topics as applicable
- Always depth-conditional backlink to parent hub (`life/personal`, …)

## Pipeline after write
```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
# append log.md with journal summary — never echo private body in shareable contexts
```

## Privacy guarantee
- Filtered out of any shareable export
- When unsure → `private`
- Do not paste full journal bodies into public docs, PRs, or shareable concepts
