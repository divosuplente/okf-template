import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

let synced = false;

function isOkfVault(cwd) {
  return fs.existsSync(path.join(cwd, "rules", "path-access-control.md"));
}

function doSync(cwd, onDone) {
  const stamp = new Date().toISOString().replace("T", " ").slice(0, 19);
  let result = "";
  let stashUsed = false;
  try {
    const status = execSync("git status --porcelain", { cwd, stdio: "pipe" }).toString().trim();
    if (status) {
      stashUsed = true;
      execSync("git stash -u -m 'git-sync'", { cwd, stdio: "pipe" });
    }
    execSync("git pull --rebase origin main", { cwd, stdio: "pipe" });
    if (stashUsed) {
      try { execSync("git stash pop --quiet", { cwd, stdio: "pipe" }); } catch (_) { result = `⚠ Synced but stash pop conflicted: resolve manually`; }
    }
    if (!stashUsed || !result) result = `✓ Synced at ${stamp}${stashUsed ? " (changes preserved)" : ""}`;
  } catch (e) {
    try { execSync("git rebase --abort", { cwd, stdio: "pipe" }); } catch (_) {}
    if (stashUsed) {
      try { execSync("git stash pop --quiet", { cwd, stdio: "pipe" }); } catch (_) {
        result = `✗ Sync failed: ${e.message.split('\n')[0]}; stash remains: \`git stash list\``;
      }
    }
    if (!result) result = `✗ Sync failed: ${e.message.split('\n')[0]}`;
  }
  fs.writeFileSync(path.join(cwd, ".omp", "git-sync-status.txt"), `[git-sync] ${result}\n`);
  if (onDone) {
    setTimeout(() => onDone(`[git-sync] ${result}`), 5000);
  } else {
    console.log(`[git-sync] ${result}`);
  }
}

// Fallback: works when loaded directly via config.yml
export default function (pi) {
  pi.on("tool_call", async (_event, ctx) => {
    if (synced) return;
    if (!isOkfVault(ctx.cwd)) return;
    synced = true;
    doSync(ctx.cwd, (msg) => console.log(msg));
  });
}

// Preferred: invoked by project-loader.ts immediately on session_start
export async function onSessionStart(_event, ctx) {
  if (synced) return;
  if (typeof ctx !== "object" || ctx === null || !("cwd" in ctx)) return;
  if (!isOkfVault(ctx.cwd)) return;
  synced = true;
  doSync(ctx.cwd, (msg) => console.log(msg));
}
