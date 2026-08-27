---
type: skill
---

# Stage 02 — Concept

> One job: compile raw source into canonical concept(s) with correct placement and body.

## Inputs
- Stage 01 raw path(s)
- `skills/okf-core` domain/subdomain maps (FBC — full-body classification)
- `skills/okf-ingest/SKILL.md` for YT/web special cases (creator, linked tools)

## Outputs (write)
- Primary: `concepts/<domain>/<sub>/<…>/<slug>.md`
- Optional: creator `concepts/creators/…`, linked tool concepts, hub link updates
- Frontmatter **required**: `type`, `visibility` (explicit)
- Recommended: `title`, `description`, `domain`, `tags`, `source`, `timestamp`, `status`

## Classification rules (non-negotiable)

Shared reference (extensible, not a cage): `_config/taxonomy.md`.
- Read **full** body/transcript — not title/keywords alone
- `life` = personal/neurodivergent/travel/mindfulness only; cooking/health learning → `learning/…`
- Agent frameworks → `tools/agents/…`; devices → `tools/dev/devices` (or current devices path)
- `#private` or personal content → `visibility: private`
- Skip structural headings as titles: Transcript, Features, Installation, Readme, Overview, Introduction
- Remove `clippings` / domain-redundant tags; lowercase hyphenated singular tags

## Body quality
- Summary from actual content, not blurb-only
- Concrete examples from source
- ≥1 cross-link to existing concepts when possible
- Depth-conditional backlink to parent hub (`okf-core` HUB rules)
- YT: link creator; list extracted real tools (not social profiles)

## Done when
- [ ] Concept path matches FBC
- [ ] FM valid; tags cleaned
- [ ] Hub entry added/updated when required by skill
- [ ] List of all concept paths created this run (for stage 04 log)

## Human gate
Review title, domain path, and visibility before cleanup if classification is ambiguous.

## Next
→ `../03-cleanup/CONTEXT.md`
