---
type: skill
name: okf-journal
description: >-
  Private journal, therapy, and session note ingestion into the OKF brain.
  Triggered when user mentions journaling, therapy notes, therapy session,
  journal entry, personal reflection, or sensitive personal content to save.
  Supports --mode journal (general private entries) and --mode therapy
  (clinically-aware therapy/session notes). ALWAYS visibility: private.
  Domain life. Never shareable export.
---

# OKF Journal — Private journal & therapy/session note ingest

## Modes

| Mode | `--mode journal` | `--mode therapy` |
|------|-------------------|-------------------|
| Use for | General journaling, reflections, life events, habit tracking | Therapy sessions, clinical notes, mental health reflections |
| Type | `note`, `habit`, `goal`, `topic` (FBC) | `note` |
| Tags | FBC-derived + `journal` | FBC-derived + `therapy`, `journal` |
| Clinical framework awareness | No | Yes — recognizes CBT, DBT, ACT, EMDR, Schema Therapy concepts |

Both modes are ALWAYS `visibility: private`.

## Trigger patterns
- "journal", "journaling", "journal entry", "log this"
- "therapy", "therapy session", "therapy notes", "session notes"
- "reflection", "personal reflection", "reflect on"
- Personal/sensitive content to save (mental health, recovery, private life events)

## Non-negotiable rules
- **ALWAYS** `visibility: private`
- **ALWAYS** personal-domain placement under `life/` (never `shareable`)
- **FBC:** read full entry body to choose subdomain and tags — see `_config/taxonomy.md` (extensible)
- **NEVER** mark journal/therapy entries `shareable` or include them in exports
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
tags: [journal, <topic-tags-from-FBC>]
timestamp: <session date or today ISO>
status: active
source:
  - self:
---
```

For therapy mode, add `therapy` to tags and include framework tag(s) if applicable
(e.g., `cbt`, `dbt`, `act`, `emdr`, `schema-therapy`).

## Body template — journal mode
```markdown
# <Title>

## Date
<YYYY-MM-DD>

## Summary
<1-2 sentences>

## Notes
<structured notes>

## Insights
<takeaways>

## Action items
- <next steps>

## Related
- [parent hub]
```

## Body template — therapy mode
```markdown
# <Title>

## Session date
<YYYY-MM-DD>

## Framework
<CBT | DBT | ACT | EMDR | Schema Therapy | Integrative | Other>

## Summary
<1-2 sentences>

## Session content
<structured notes — what was discussed, what techniques were used>

## Insights
<takeaways, cognitive distortions identified, patterns noticed>

## Homework / action items
- <between-session assignments, practice goals>

## Related
- [parent hub]
```

## Therapy mode: clinical framework reference

When `--mode therapy` is active, recognize and tag these frameworks:

| Framework | Key concepts to watch for |
|-----------|--------------------------|
| **CBT** (Cognitive Behavioral Therapy) | Cognitive distortions, automatic thoughts, behavioral activation, exposure |
| **DBT** (Dialectical Behavior Therapy) | Wise mind, distress tolerance, emotional regulation, interpersonal effectiveness |
| **ACT** (Acceptance and Commitment Therapy) | Psychological flexibility, values, defusion, acceptance |
| **EMDR** (Eye Movement Desensitization and Reprocessing) | Processing, bilateral stimulation, target memories |
| **Schema Therapy** | Early maladaptive schemas, schema modes, limited reparenting |

Tag with the framework(s) identified. Do NOT diagnose — record what was discussed.

## Cross-link targets
Search first (`okf search`) to find existing related concepts.
- Always depth-conditional backlink to parent hub (`life/personal`, etc.)
- Link to relevant concepts when the journal entry relates to existing knowledge

## Pipeline after write
```bash
python3 tools/okf.py index
python3 tools/okf.py lint
python3 tools/okf.py relink --dry-run
# append log.md with journal summary — never echo private body in shareable contexts
```

## Privacy guarantee
- Filtered out of any shareable export
- When unsure -> `private`
- Do not paste full journal/therapy bodies into public docs, PRs, or shareable concepts
