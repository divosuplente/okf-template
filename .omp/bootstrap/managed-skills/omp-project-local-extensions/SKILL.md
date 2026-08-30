---
name: omp-project-local-extensions
description: Create project-local OMP extensions that travel with git via a global project-loader bootstrap extension.
---

# OMP Project-Local Extensions

Creates a global bootstrap extension that dynamically loads project-local extensions from `cwd/.omp/extensions/`, enabling extensions to travel with git.

## When to Use

- User wants project-local OMP extensions that travel with git
- User asks for extensions that auto-activate per repository
- User mentions `.omp/extensions/` or local project extensions

## Setup (FIRST — copy bundled files into place)

This skill bundles the global loader and companion skill as `references/`. Before doing anything else, ensure they exist on disk:

```bash
# 1. Copy global project-loader (if not already present)
mkdir -p ~/.omp/agent/extensions
if [ ! -f ~/.omp/agent/extensions/project-loader.ts ]; then
  cp <skill-dir>/references/project-loader.ts ~/.omp/agent/extensions/
  echo "Installed project-loader.ts"
fi

# 2. Copy extensions-create skill (if not already present)
if [ ! -d ~/.omp/agent/managed-skills/extensions-create ]; then
  mkdir -p ~/.omp/agent/managed-skills/extensions-create
  cp <skill-dir>/references/extensions-create.md ~/.omp/agent/managed-skills/extensions-create/SKILL.md
  echo "Installed extensions-create skill"
fi
```

`<skill-dir>` resolves to this skill's directory (`~/.omp/agent/managed-skills/omp-project-local-extensions/`).

If either file already exists, skip — don't overwrite local customizations.

## Architecture

```
~/.omp/agent/extensions/          <- Global (auto-discovered by OMP)
└── project-loader.ts             <- Scans cwd/.omp/extensions/

<repo>/.omp/extensions/           <- Local (travels with git)
├── git-sync.js
├── path-guard.js
└── concept-guard.js
```

## Global Loader

Read `references/project-loader.ts` for the canonical source. Copy to `~/.omp/agent/extensions/project-loader.ts` (see Setup above).

Key behavior:
- Scans `<cwd>/.omp/extensions/` for `.js` files only (`.ts` dynamic imports return `{}`)
- For each file: calls `mod.default(pi)` then `mod.onSessionStart(event, ctx)` immediately
- `onSessionStart` bypass lets local extensions act on the same `session_start` that loaded them

## Local Extension Contract

Each local extension exports two functions:
- `default(pi)` — registers tool_call handlers (fallback for direct config.yml loading)
- `onSessionStart(event, ctx)` — invoked immediately by loader to bypass session_start timing

```javascript
export default function (pi) {
  pi.on("tool_call", async (_event, ctx) => { /* ... */ });
}

export async function onSessionStart(_event, ctx) {
  // Vault detection guard — inactive in other repos
  if (!isOkfVault(ctx.cwd)) return;
  // ... startup logic
}
```

## Path Guard Absolute Path Support

`path-guard.js` checks absolute/tilde paths BEFORE the outside-repo block. Must strip trailing slashes from expanded paths to avoid double-slash mismatch:

```javascript
const expanded = aPath.replace(/^~/, process.env.HOME || "").replace(/\/+$/, "");
if (resolved === expanded || resolved.startsWith(expanded + "/")) {
  absAllowed = true;
  break;
}
```

## Companion Skill: extensions-create

Read `references/extensions-create.md` for the full extension authoring guide. Covers:
- Global vs project-local extension scopes
- Event selection table (tool_call, session_stop, tool_result, etc.)
- Code patterns for blocking, revising args, redacting output
- Wiring and verification steps

## Verification

1. Restart OMP for fresh session
2. Look for `[project-loader] Imported <file>, exports: <keys>`
3. If exports show `(empty)`, runtime can't execute `.ts` — rename to `.js`
4. Check `[git-sync]`, `[path-guard]`, `[concept-guard]` logs for activity

## Key Bugs & Fixes

| Bug | Fix |
|---|---|
| `git-sync.js` `synced = true` ran before `try/catch` | Moved inside `try`, after `execSync` |
| `session_start` event missed by lazy-loaded extensions | `project-loader.ts` invokes `mod.onSessionStart` immediately |
| `~/.omp/agent/extensions/` blocked by outside-repo check | Added `absAllowed` flag with tilde expansion before `..` check |
| `~/.omp/` trailing slash → `expanded + "/"` = double-slash | Strip trailing slashes: `.replace(/\/+$/, "")` before concatenation |
| `path.isAbsolute()` returns `false` for `~` paths | Added `aPath.startsWith("~")` check alongside `path.isAbsolute()` |
| Dynamic `.ts` imports returning `{}` | Add diagnostics logging; rename to `.js` if confirmed |
