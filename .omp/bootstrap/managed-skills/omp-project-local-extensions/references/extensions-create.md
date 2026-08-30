# Create Hook: Turn an Idea Into a Working OMP Extension

**What the user wants the extension to do**: $ARGUMENTS

If filled in, treat it as the spec. Only ask to pin down gaps (exact paths/commands/patterns, whether it must *block*). If blank, ask what it should guarantee or do.

## What an extension is

An OMP **extension** is a TypeScript module that fires on lifecycle events. It runs whether the model "remembers" or not — a rule asks, an extension guarantees.

## Two extension scopes

| Scope | Path | Loaded by | Format | When to use |
|---|---|---|---|---|
| **Global** | `~/.omp/agent/extensions/<name>.ts` | OMP core auto-discovery | `.ts` only — factory export | Rules that apply across all projects (security, tool guards, prompt injection) |
| **Project-local** | `<repo>/.omp/extensions/<name>.js` | `project-loader.ts` global extension | `.js` — dual export `default(pi)` + `onSessionStart(event, ctx)` | Vault-specific guards that travel with git (path access, concept guards, sync hooks) |

### Global extensions

Drop a `.ts` file into `~/.omp/agent/extensions/` — OMP auto-discovers it on startup. No config wiring.

```ts
// ~/.omp/agent/extensions/my-extension.ts
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";

export default function (pi: ExtensionAPI): void {
  pi.on("tool_call", async (event, ctx) => {
    // intercept
  });
}
```

### Project-local extensions

Live in `.omp/extensions/` inside the repo. Require the global `project-loader.ts` extension (ships with OMP) to discover them. Dual export pattern:

```js
// .omp/extensions/my-guard.js
export default function (pi) {
  // Fallback: works when loaded directly via config.yml
  pi.on("tool_call", async (_event, ctx) => { /* ... */ });
}

// Preferred: invoked by project-loader.ts immediately on session_start
export async function onSessionStart(_event, ctx) {
  // ctx.cwd is the repo root; perform startup work here
}
```

Why `.js`? Dynamic `import()` of `.ts` at runtime returns `{}` in Node.js (no native TS loader). The loader only accepts `.js`.

## Pick the event

| The user wants to... | Event | Can block? | Return shape |
|---|---|---|---|
| **Stop a tool from executing** or revise its args | **`tool_call`** | **Yes** | `{ block: true, reason }` or `{ input: {...} }` |
| **Patch tool output** (redact, truncate) | **`tool_result`** | No | `{ content, details, isError }` |
| **Filter LLM context** before API call | **`context`** | No | `{ messages: [...] }` |
| **Inject into system prompt** every turn | **`before_agent_start`** | No | `{ systemPrompt: "..." }` |
| **Run on session start** | **`session_start`** | No | — |
| **Run on turn boundary** | **`turn_start`** / **`turn_end`** | No | — |
| **Gate the session stop** ("don't finish until tests pass") | **`session_stop`** | **Yes** | `{ decision: "block", reason }` or `{ continue: true, additionalContext }` |
| **Run when agent streaming ends** | **`agent_end`** | No | — |
| **Cancel session switch/branch/compact** | **`session_before_switch`**, `session_before_branch`, `session_before_compact` | **Yes** | `{ cancel: true }` |
| **Intercept user bash/python** | **`user_bash`** / **`user_python`** | No | `{ result }` |

## Write the extension

1. **Guard early** — check `event.toolName` and return `undefined` for non-matching events.
2. **Return the shaped result** — or `undefined` to pass through.
3. **Fail open** — `tool_call` errors are **fail-closed** (block the tool). Wrap in `try/catch` if a crash should not block.
4. **Guard UI** — `ctx.hasUI` is false in headless/subagent mode.

### 1. Blocking a tool call

```ts
pi.on("tool_call", async (event, ctx) => {
  if (event.toolName !== "bash") return;
  const input = event.input;
  if (typeof input !== "object" || input === null || !("command" in input)) return;
  const cmd = input.command;
  if (typeof cmd !== "string" || !cmd.includes("rm -rf")) return;

  if (ctx.hasUI) {
    const ok = await ctx.ui.confirm("Dangerous command", `Allow: ${cmd}`);
    if (ok) return;
  }

  return { block: true, reason: "rm -rf blocked by policy" };
});
```

### 2. Revising tool args (non-blocking)

```ts
pi.on("tool_call", async (event) => {
  if (event.toolName !== "read") return;
  const input = event.input;
  if (typeof input !== "object" || input === null || !("path" in input)) return;
  const pathVal = input.path;
  if (typeof pathVal === "string" && pathVal.includes(".env")) {
    return { input: { ...event.input, raw: true } };
  }
});
```

### 3. Redacting tool output (middleware-style)

`tool_result` is middleware: each handler sees **prior modifications**, not the original. Last override wins.

```ts
pi.on("tool_result", async (event) => {
  if (event.isError || event.toolName !== "read") return;
  let changed = false;
  const out = event.content.map(chunk => {
    if (chunk.type !== "text") return chunk;
    const next = chunk.text.replace(/(API_KEY|SECRET)=\S+/g, "$1=[REDACTED]");
    if (next !== chunk.text) changed = true;
    return { ...chunk, text: next };
  });
  if (changed) return { content: out };
});
```

### 4. Injecting into the system prompt every turn

```ts
pi.on("before_agent_start", async (event) => {
  const extra = "\n\nAlways use TypeScript strict mode.";
  return { systemPrompt: `${event?.systemPrompt ?? ""}${extra}` };
});
```

### 5. Gate session stop ("don't finish until green")

```ts
pi.on("session_stop", async (event, ctx) => {
  const { execSync } = await import("child_process");
  try {
    execSync("npm run check", { stdio: "pipe", cwd: ctx.cwd });
    return; // green — allow stop
  } catch {
    return { decision: "block", reason: "Validation failed; fix issues before stopping." };
  }
});
```

### 6. Session-start setup

```ts
pi.on("session_start", async (event, ctx) => {
  if (event.reason !== "startup") return;
  ctx.ui.notify("Extension loaded", "info");
});
```

### 7. Background timers (safe)

Use `ctx.setInterval` / `ctx.setTimeout` — raw `setInterval` can crash the session on unhandled errors.

```ts
pi.on("session_start", async (_event, ctx) => {
  const timer = ctx.setInterval(() => {
    ctx.ui.notify("health check", "info");
  }, 60_000);
  pi.on("session_shutdown", () => ctx.clearTimer(timer));
});
```

## Wiring

**Global**: Drop the file. Restart OMP. Done.

**Project-local**: Ensure `project-loader.ts` exists in `~/.omp/agent/extensions/` (ships with OMP). Place `.js` files in `.omp/extensions/`:

```bash
mkdir -p .omp/extensions
# Write extension to .omp/extensions/my-guard.js
git add .omp/extensions/
```

One-shot load without installing:
```bash
omp --extension ./path/to/extension
```

## Verify

1. **Install**: place in the correct directory for the scope.
2. **Restart** OMP.
3. **Trigger** the condition — for a blocking extension, ask the agent to do the blocked action and check it refuses with your reason.
4. **Negative path** — do something that should pass through; verify it works normally.

## Quality checks

- ✅ Correct scope: global (cross-project) vs local (vault-specific, travels with git).
- ✅ Correct event for the behavior.
- ✅ Blocking uses `tool_call` or `session_stop` or `session_before_*`.
- ✅ Early guards on `toolName` / event shape.
- ✅ Type-safe input access — no `as any`; use `typeof` guards (see examples).
- ✅ Fail-open: `try/catch` around `tool_call` if crash should not block.
- ✅ UI calls guarded by `ctx.hasUI`.
- ✅ Background work uses `ctx.setInterval` / `ctx.setTimeout`, not raw globals.
- ✅ Both blocking and pass-through paths verified.

## Security note

An extension runs arbitrary code automatically, with your credentials, on every matching event. Review extensions like you review CI config.

## Notes

- Extensions are the deterministic floor — reserve them for non-negotiables (secrets, destructive commands, tool guards, "don't finish until green").
- Keep extensions fast; they block the agent loop while running.
- `tool_call`: first `{ block: true }` short-circuits; last `{ input }` revision wins.
- `tool_result`: middleware-style; each handler sees prior modifications; last override wins.
- `context`: chained; each handler receives prior handler's output.
- `session_stop`: capped at 8 consecutive continuations; never fires for subagent sessions.
- Runtime actions (`pi.sendMessage`, etc.) are unavailable during factory load — register handlers first, perform actions from events.
