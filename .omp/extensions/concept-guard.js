import * as path from "path";
import * as fs from "fs";

export default function (pi) {
  const PERSONAL_DOMAINS = ["life", "people", "orgs", "documents", "work"];

  pi.on("tool_call", async (event, ctx) => {
    if (!["write", "edit"].includes(event.toolName)) return;
    const targets = getTargets(event.toolName, event.input);
    for (const target of targets) {
      if (!target.startsWith("concepts/")) continue;
      const content = event.input.content || "";
      const frontmatter = extractFrontmatter(content);
      if (!frontmatter) {
        return { block: true, reason: `Missing frontmatter in ${target}. Every concept requires type and visibility.` };
      }

      if (!frontmatter.type) {
        return { block: true, reason: `Missing required field 'type' in ${target}.` };
      }
      if (!frontmatter.visibility) {
        return { block: true, reason: `Missing required field 'visibility' in ${target}.` };
      }

      const domain = target.split("/")[1];
      if (PERSONAL_DOMAINS.includes(domain) && frontmatter.visibility === "shareable") {
        return { block: true, reason: `Personal domain '${domain}' cannot be 'shareable' in ${target}. Override requires explicit confirmation.` };
      }

      if (frontmatter.type !== "note" && !frontmatter.source) {
        return { block: true, reason: `Missing 'source' provenance in ${target} (required for non-note types).` };
      }
    }
  });
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

function extractFrontmatter(content) {
  const match = content.match(/^\s*---\s*\n([\s\S]*?)\n\s*---\s*$/);
  if (!match) return null;
  const fmText = match[1];
  const result = {};
  for (const line of fmText.split("\n")) {
    const kv = line.match(/^(\w+):\s*(.+)$/);
    if (kv) result[kv[1]] = kv[2].trim();
  }
  return result;
}
