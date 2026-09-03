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
| Kind | Path pattern |
|------|-------------|
| Primary concept | `concepts/<domain>/<sub>/<…>/<slug>.md` (concise overview, ~50-80 lines) |
| Deep reference (optional) | `concepts/<domain>/<sub>/references/<slug>.md` (or `.../<ssub>/references/<slug>.md`) |
| Creator | `concepts/creators/…` when applicable |
| Linked tools | Per-tool concepts per FBC |

- Frontmatter **required**: `type`, `visibility` (explicit)
- Recommended: `title`, `description`, `domain`, `tags`, `source`, `generated`, `status`

## Concept + Reference split
For substantive content (videos >15 min, courses, lectures, technical talks), split output into two files:
1. **Concept file** (overview): concise summary + structured outline + cross-links + link to reference
2. **Reference file** (deep extract): full knowledge extraction with expanded primary sources

The reference file is NOT a transcript. It extracts teachings and expands each concept with:
- Original author, year, paper/book title
- Historical context and original formulation
- Key extensions and related work
- `read` Wikipedia articles directly for source expansion (works even when `web_search` is blocked)
- Search existing vault concepts (`okf search`) for cross-link targets

Bidirectional links: concept → reference (`> **Full knowledge extract...:** [link]`) and reference → concept (`> **Parent concept:** [link]`).

Skip reference file for short videos (<15 min) or entertainment content with no extractable knowledge.

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
- [ ] Concept is concise overview (not full extract) when a reference file is also created
- [ ] Reference file created for substantive content (if applicable), with expanded sources and bidirectional link
- [ ] Hub entry added/updated when required by skill
- [ ] List of all concept + reference paths created this run (for stage 04 log)

## Human gate
Review title, domain path, and visibility before cleanup if classification is ambiguous.

## Next
→ `../03-cleanup/CONTEXT.md`
