import * as path from "path";
import * as fs from "fs";

export default function (pi) {
  const RULES_FILE = "rules/path-access-control.md";

  pi.on("tool_call", async (event, ctx) => {
    if (!fs.existsSync(path.join(ctx.cwd, RULES_FILE))) return;
    if (!["write", "edit"].includes(event.toolName)) return;

    const rulesPath = path.join(ctx.cwd, RULES_FILE);
    let content;
    try {
      content = fs.readFileSync(rulesPath, "utf-8");
    } catch {
      return;
    }

    const { allowed, readonly } = parseRules(content);
    const targets = getTargets(event.toolName, event.arguments ?? event.input);
    for (const raw of targets) {
      const resolved = path.isAbsolute(raw)
        ? raw
        : raw.match(/^\w+:\/\//)
          ? raw
          : path.resolve(ctx.cwd, raw);

      let absAllowed = false;
      for (const aPath of allowed) {
        if (path.isAbsolute(aPath) || aPath.startsWith("~")) {
          const expanded = aPath.replace(/^~/, process.env.HOME || "").replace(/\/+$/, "");
          if (resolved === expanded || resolved.startsWith(expanded + "/")) {
            absAllowed = true;
            break;
          }
        }
      }
      if (absAllowed) continue;

      const rel = raw.match(/^\w+:\/\//)
        ? raw
        : path.relative(ctx.cwd, resolved).replace(/\\/g, "/");
      if (rel.startsWith("..")) {
        return { block: true, reason: `Attempt to access path outside repo root: ${raw}` };
      }

      for (const rPath of readonly) {
        if (matches(rel, rPath)) {
          return { block: true, reason: `${rel} is Read-Only (path-access-control.md).` };
        }
      }

      let relAllowed = false;
      for (const aPath of allowed) {
        if (matches(rel, aPath)) {
          relAllowed = true;
          break;
        }
      }

      if (!relAllowed) {
        return { block: true, reason: `${rel} is not in Allowed Paths list.` };
      }
    }
  });
}

function parseRules(content) {
  const allowed = [];
  const readonly = [];
  let section = null;

  for (const line of content.split("\n")) {
    if (line.includes("**Allowed Paths")) section = "allowed";
    else if (line.includes("**Read-Only Paths")) section = "readonly";
    else if (
      line.startsWith("**") ||
      line.startsWith("#") ||
      (line.trim() && !line.startsWith("- "))
    )
      section = null;

    if (section && line.startsWith("- ")) {
      const foundRules = line.match(/`([^`]+)`/g);
      if (foundRules) {
        for (const m of foundRules) {
          const p = m.slice(1, -1);
          if (section === "allowed") allowed.push(p);
          else if (section === "readonly") readonly.push(p);
        }
      }
    }
  }
  return { allowed, readonly };
}

function getTargets(toolName, input) {
  if (toolName === "write") {
    if (typeof input !== "object" || input === null || !("path" in input)) return [];
    const p = input.path;
    return typeof p === "string" ? [p] : [];
  }
  if (toolName === "edit") {
    if (typeof input !== "object" || input === null || !("input" in input)) return [];
    const raw = input.input;
    const targets = [];
    for (const line of String(raw).split("\n")) {
      const match = line.match(/^\[([^\]]+)#[^\]]+\]$/);
      if (match) targets.push(match[1]);
    }
    return targets;
  }
  return [];
}

function matches(target, rule) {
  if (rule.endsWith("/")) return target.startsWith(rule);
  return target === rule;
}
