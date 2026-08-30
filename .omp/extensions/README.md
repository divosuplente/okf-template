---
type: note
visibility: private
source: [self]
domain: tools
---
# project-local OMP extensions (okf vault)

## Fresh-machine setup

Run the bootstrap script after cloning this vault:

```bash
bash .omp/setup.sh
```

This copies bundled global extensions and managed skills from `.omp/bootstrap/` into `~/.omp/agent/`, so they're available on any machine.

## How it works

`project-loader.ts` (global) scans `<cwd>/.omp/extensions/*.js` on session start and loads them. No config wiring needed.

### Extension sources (bundled in `.omp/bootstrap/`)

| File | Scope | Purpose |
|---|---|---|
| `extensions/project-loader.ts` | Global (`~/.omp/agent/extensions/`) | Scans and loads local `.js` extensions |
| `extensions/path-guard.js` | Local (this dir) | Enforces `rules/path-access-control.md` allowed/readonly lists |
| `extensions/concept-guard.js` | Local (this dir) | Gates `write` to `concepts/**`: required frontmatter, domain visibility |
| `extensions/git-sync.js` | Local (this dir) | Session-start `git pull --rebase origin main` |

### Managed skills (bundled in `.omp/bootstrap/managed-skills/`)

| Skill | Purpose |
|---|---|
| `extensions-create` | Author new OMP extensions (event table, API patterns, global vs local) |
| `omp-project-local-extensions` | Setup guide for project-local extensions |

## Key bugs fixed

1. **`event.input` vs `event.arguments`**: OMP tool_call events use `event.arguments` for tool parameters, not `event.input`. `path-guard.js` and `concept-guard.js` now check `event.arguments ?? event.input`.
3. **Absolute writes bypass**: `concept-guard.js` normalizes via `path.relative(ctx.cwd, t)`.
4. **Frontmatter regex**: Changed to tolerate body after closing `---`.
5. **`edit` events**: No `content` field → content checks scoped to `write` only.