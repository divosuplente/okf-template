---
type: infrastructure
---

# Taxonomy reference (extensible)

> **Not a closed classifier.** Agents MUST read the **full body** of each source (transcript, article, note) to choose `domain` / `subdomain` / `subsubdomain` and semantic tags (FBC).  
> This file is a **shared starting map** so skills stop re-pasting tables. New leaves are expected.

Skills reference this as `@tax` / `_config/taxonomy.md`.

## Full-body classification (mandatory)

1. Read the entire source body (not title/filename/keywords alone).
2. Decide placement from what the content is **actually about**.
3. Prefer an existing path from the map below when it fits.
4. If nothing fits durably → **extend the map** (see Extension protocol). Do not force-fit into a wrong leaf.
5. Semantic tags come from full-body meaning after cleanup rules — not from a keyword→tag table.

## Visibility defaults

| Default | Domains |
|---------|---------|
| `private` | `life`, `people`, `orgs`, `documents`, `work` |
| `shareable` | `tools`, `skills`, `specs`, `learning`, `creators` |

Author may override. Unsure → `private`. Lint warns on personal-domain + `shareable`.

## Soft routing heuristics (aids only)

- `life` = personal only: journal/therapy-adjacent personal — **not** general health/learning.
- `learning` = articles/courses/talks including health science, languages, music, dev learning.
- `tools` = products, CLIs, agent frameworks, devices.
- Agent frameworks → `tools/agents/…` (not `tools/dev` orchestration dump).
- Physical devices → `tools/dev/devices` (or current devices path).
- Public creators/channels → `creators/`; private contacts → `people/`.
- Internal enterprise → `work/` (private default).

## Known domains (top-level)

`life` · `people` · `orgs` · `documents` · `tools` · `specs` · `skills` · `learning` · `creators` · `work`

## Known subdomains (current map — extensible)

| Domain | Subdomains |
|--------|------------|
| `life` | `personal` |
| `learning` | `dev`, `languages`, `music`, `skills`, `health`, `general` |
| `tools` | `agents`, `dev`, `general` |
| `skills` | `content`, `general` |
| `work` | `general` |
| `people` | `medical`, `tech`, `general` |
| `creators` | `general` |
| `orgs` | `general` |
| `documents` | `general` |
| `specs` | `general` |

## Known subsubdomains (current map — extensible)

| Path | Subsubs |
|------|---------|
| `learning/dev` | `javascript`, `react`, `css`, `typescript`, `vue`, `svelte`, `html`, `git`, `dotnet`, `api`, `performance`, `ai`, `architecture` |
| `learning/health` | *(populated per-vault)* |
| `learning/languages` | *(populated per-vault)* |
| `learning/music` | *(populated per-vault)* |
| `learning/skills` | *(populated per-vault)* |
| `tools/agents` | `orchestration`, `coding-agents`, `sandboxes`, `memory`, `mcp`, `general` |
| `tools/dev` | `general`, `devices` |
| `tools/general` | `devices`, `general`, `orchestration` |

## Tag cleanup (mechanical / after FBC)

Apply **after** full-body tag choice:

- lowercase, hyphenated, **singular** preferred
- ≥1 meaningful tag
- **Remove:** `clippings`, bare `youtube` (unless creator-context needs it), domain-redundant tags (tag == domain name), garbage/hex/numeric tags
- **Keep** broad parent `dev` and add specific sub-tags when applicable
- Near-duplicate merges (examples, not exhaustive):  
  `self-hosted`/`self-hosting` → pick one form vault-wide · `agent`/`agents` → `agent` ·  
  `ai-skills`→`ai` · `webdev`→`web-development` · `selfhosting`→`self-hosted` ·  
  `blood-sugar`→`glucose` · `omega3`→`omega-3` · `long-covid`→`covid`

Do **not** assign semantic tags from keywords alone.

## Types (unified vocabulary)

`key-element` · `goal` · `habit` · `project` · `topic` · `person` · `organization` · `document` · `tool` · `spec` · `skill` · `learning` · `source` · `playbook` · `reference` · `note` (fallback)

## Hubs (placement after FBC)

- Domain hub: `concepts/<dom>/<dom>.md`
- Subdomain hub: `concepts/<dom>/<sub>.md`
- Subsub hub: `concepts/<dom>/<sub>/<ssub>.md`
- New concepts depth-conditionally backlink to parent hub (`okf-core` HUB rules).

## Extension protocol

When FBC needs a path or tag not on this map:

1. Choose a clear kebab-case leaf name.
2. Create hub file(s) if missing (`type: reference`).
3. Update **this file** with the new leaf (keep “extensible” framing).
4. Mention structural additions in `log.md` when durable (not one-off typos).
5. Do not invent parallel trees for the same idea — merge into one leaf.

## Related

- Conventions: `_config/conventions.md`
- Glossary: `_config/glossary.md`
- Deep contract: `AGENTS.md`
- Session router: `CONTEXT.md`
