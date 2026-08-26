---
type: note                        # REQUIRED — see AGENTS.md "Unified type vocabulary"
# REQUIRED — private | shareable (personal domains life/people/orgs/documents default private, others shareable; override explicitly)
visibility: private
title: Concept Title              # recommended
description: One-line summary used in index.md and search snippets.   # recommended
domain: life                      # life | people | orgs | documents | tools | specs | skills | learning
tags: []
resource:                         # optional canonical URI for a tool/asset
source:                           # provenance — where this concept came from
  - self:                         # self: = synthesized within this vault; or a URL; or a legacy origin ref
generated: { by: agent:harness, at: 2026-07-11T00:00:00Z }  # last meaningful change (ISO 8601)
status: active                    # optional — active | dormant | archived
---

# Concept Title

One short paragraph defining the concept. Prefer structured markdown (headings,
lists, tables) over long prose.

## Why it matters
What this is for / why it is in the brain.

## Details
Body content. Cross-link related concepts with bundle-relative links, e.g.
[Another Concept](/PLACEHOLDER-not-a-link).

## Citations
External sources backing claims above.

## Sources

- https://www.youtube.com/watch?v=# provenance — where this concept came from
