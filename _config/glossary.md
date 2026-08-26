---
type: infrastructure
---

# Glossary (OKF)

## Unified `type` values
`key-element` · `goal` · `habit` · `project` · `topic` · `person` · `organization` · `document` · `tool` · `spec` · `skill` · `learning` · `source` · `playbook` · `reference` · `note` (fallback)

Finer grouping = `domain` + `tags`, not new types.

## Domains (top-level under `concepts/`)
| Domain | Typical content |
|--------|-----------------|
| `life` | Personal: journal, therapy, health, personal topics (not general learning) |
| `learning` | Articles, courses, talks, health science, languages, music, dev learning |
| `tools` | Products, CLIs, agent frameworks, devices |
| `skills` | Reusable expertise packages (knowledge concepts) |
| `creators` | Public creators / channels (usually shareable) |
| `people` | Private contacts (not public creators) |
| `orgs` | Organizations |
| `documents` | Identity/records stubs |
| `specs` | Specs and standards |
| `work` | Enterprise / internal notes (default private) |

## ICM terms (as used here)
| Term | Meaning in OKF |
|------|----------------|
| Layer 0 | `IDENTITY.md` — where am I |
| Layer 1 | `CONTEXT.md` — where do I go |
| Layer 2 | Stage/skill `CONTEXT.md` or `SKILL.md` — what do I do |
| Layer 3 | `_config/`, rules, deep `AGENTS.md` slices |
| Layer 4 | Working inputs/outputs: `raw/`, `inbox/`, concept files, `log.md` |
| Stage contract | Fixed inputs, structured outputs, optional human gate |
| Compile | Turn raw/inbox into canonical concepts |

## Provenance `source` forms
- Historical: `<origin>:…`
- URL or `youtube:watch?v=…`
- `self:` for vault-synthesized

## Taxonomy
See `_config/taxonomy.md` — extensible FBC reference map (not a closed enum).
