#!/usr/bin/env python3
"""WikiSkill: co-evolve agent skills with a persistent knowledge base.

Implements the framework from arXiv:2608.27454 (Tang et al., 2026).
Three-layer architecture: raw traces -> wiki patterns -> executable skills.
Four-phase loop: inference -> wiki maintenance -> skill proposal -> gating/rollback.

Usage:
    python3 tools/wikiskill.py init --workspace ./ws --target skills/my-skill
    python3 tools/wikiskill.py run  --workspace ./ws --train-tasks train.json \\
        --val-tasks val.json --llm-command 'cat' --max-iters 8
    python3 tools/wikiskill.py status --workspace ./ws
    python3 tools/wikiskill.py report --workspace ./ws

For programmatic use from the eval kernel:
    import wikiskill
    wikiskill.run_evolution(ws, train, val, agent_fn=agent, completion_fn=completion)
"""
from __future__ import annotations

import argparse
import difflib
import importlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Prompts (adapted from paper Appendix E)
# ---------------------------------------------------------------------------

INFERENCE_PROMPT_TEMPLATE = """\
You are an AI agent with the following skill instructions:

--- SKILL ---
{skill_content}
--- END SKILL ---

Complete the following task. Show your reasoning, then give your final answer.

Task: {task_description}

Return your final answer on a line starting with "ANSWER: ".
"""

WIKI_MAINTAINER_PROMPT = """\
You are the Wiki Maintainer in the WikiSkill framework.

Your job: analyze agent execution traces and update the persistent knowledge base.

You receive:
1. The current wiki (patterns + index + logs)
2. Sampled execution traces (up to 5 failing, 3 passing, each capped at 15K chars)

Your tasks:
- Perform root-cause analysis on failures: identify patterns in what went wrong.
- Extract successful strategies from passing traces.
- Create new pattern files or update existing ones.
- Append to the evolution log.

Respond in JSON:
{
  "patterns": [
    {"action": "create", "name": "<slug>", "content": "<markdown>"},
    {"action": "update", "name": "<slug>", "content": "<updated markdown>"}
  ],
  "log_entry": "<one-line summary of this iteration's findings>"
}

Current wiki:
{wiki_content}

Sampled traces:
{traces_content}
"""

SKILL_PROPOSER_PROMPT = """\
You are the Skill Proposer in the WikiSkill framework.

You operate in ReAct style. You have access to:
- Wiki index and pattern files
- Skill-impact tracker (proposal diffs + validation outcomes)
- Training outcome summary
- Raw trace files

Analyze the wiki patterns and trace outcomes, then propose a skill update.

Respond in JSON:
{
  "action": "create" | "patch" | "no_action",
  "skill_name": "<name>",
  "patches": [
    {"op": "append", "target": "<exact substring to find>", "content": "<text to add>"},
    {"op": "replace", "target": "<exact substring to find>", "content": "<replacement>"}
  ],
  "full_content": "<if action=create, the full SKILL.md content>",
  "purpose": "<motivating wiki patterns>",
  "summary": "<one-line description of the proposal>"
}

Wiki index:
{wiki_index}

Skill impact:
{skill_impact}

Training outcomes:
{training_summary}

Current skill:
{skill_content}
"""


# ---------------------------------------------------------------------------
# Workspace management
# ---------------------------------------------------------------------------

def init_workspace(ws_root: str, target_skill: str | None = None) -> Path:
    """Create the WikiSkill workspace directory structure."""
    ws = Path(ws_root)
    (ws / "raw" / "traces").mkdir(parents=True, exist_ok=True)
    (ws / "wiki" / "patterns").mkdir(parents=True, exist_ok=True)
    (ws / "skills").mkdir(parents=True, exist_ok=True)

    for f in ("wiki/index.md", "wiki/logs.md", "wiki/skill-impact.md"):
        p = ws / f
        if not p.exists():
            p.write_text("", encoding="utf-8")

    # Seed skill
    target_name = Path(target_skill).name if target_skill else "default-skill"
    skill_dir = ws / "skills" / target_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        if target_skill and Path(target_skill).exists():
            src = Path(target_skill)
            if src.is_dir():
                src_skill = src / "SKILL.md"
                if src_skill.exists():
                    skill_md.write_text(src_skill.read_text(encoding="utf-8"))
                else:
                    skill_md.write_text(_stub_skill(target_name), encoding="utf-8")
            else:
                skill_md.write_text(src.read_text(encoding="utf-8"))
        else:
            skill_md.write_text(_stub_skill(target_name), encoding="utf-8")

    purpose_md = skill_dir / "PURPOSE.md"
    if not purpose_md.exists():
        purpose_md.write_text("# Purpose\n\n_Motivating wiki patterns._\n", encoding="utf-8")

    # Initial state
    state_path = ws / "state.json"
    if not state_path.exists():
        save_state(str(ws), {"iteration": 0, "r_best": 0.0, "history": []})

    return ws


def _stub_skill(name: str) -> str:
    return f"""---
type: skill
title: {name}
---

# {name}

_Procedural instructions for the inference agent._
"""


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state(ws_root: str) -> dict:
    p = Path(ws_root) / "state.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"iteration": 0, "r_best": 0.0, "history": []}


def save_state(ws_root: str, state: dict) -> None:
    p = Path(ws_root) / "state.json"
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Trace sampling
# ---------------------------------------------------------------------------

def sample_traces(
    traces: list[dict],
    max_failing: int = 5,
    max_passing: int = 3,
    char_cap: int = 15000,
) -> list[dict]:
    """Stratified sampling: up to max_failing failing + max_passing passing,
    sorted by trace length descending (prefer info-rich traces).
    Each trace truncated at char_cap with ...[truncated] suffix."""
    failing = sorted(
        [t for t in traces if not t.get("passed", False)],
        key=lambda t: len(t.get("trace", "")),
        reverse=True,
    )[:max_failing]
    passing = sorted(
        [t for t in traces if t.get("passed", False)],
        key=lambda t: len(t.get("trace", "")),
        reverse=True,
    )[:max_passing]

    result = []
    for t in failing + passing:
        entry = dict(t)
        trace = entry.get("trace", "")
        if len(trace) > char_cap:
            entry["trace"] = trace[:char_cap] + "...[truncated]"
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def default_scorer(task: dict, answer: str) -> float:
    """Default scorer: 1.0 if task['expected'] (lowercased) is substring of answer;
    0.0 if no match; 0.5 if no 'expected' key."""
    expected = task.get("expected")
    if expected is None:
        return 0.5
    return 1.0 if str(expected).lower() in answer.lower() else 0.0


def load_scorer(scorer_spec: str | None):
    """Load scorer from 'module:func' spec, or return default_scorer."""
    if not scorer_spec:
        return default_scorer
    module_name, func_name = scorer_spec.rsplit(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


# ---------------------------------------------------------------------------
# Patching
# ---------------------------------------------------------------------------

def apply_patch(content: str, op: str, target: str, replacement: str) -> str:
    """Apply a single patch op to content.

    ops: 'append' (add replacement after target), 'replace' (swap target with replacement),
          'insert_after' (alias for append).
    Raises ValueError if target not found.
    """
    if op in ("append", "insert_after"):
        idx = content.find(target)
        if idx == -1:
            raise ValueError(f"apply_patch: target substring not found: {target[:60]!r}")
        end = idx + len(target)
        return content[:end] + replacement + content[end:]
    elif op == "replace":
        idx = content.find(target)
        if idx == -1:
            raise ValueError(f"apply_patch: target substring not found: {target[:60]!r}")
        end = idx + len(target)
        return content[:idx] + replacement + content[end:]
    else:
        raise ValueError(f"apply_patch: unknown op '{op}'")


def generate_diff(old: str, new: str, label: str = "SKILL.md") -> str:
    """Generate unified diff for audit trail."""
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
    )
    return "".join(diff)


# ---------------------------------------------------------------------------
# Wiki operations
# ---------------------------------------------------------------------------

def _read_wiki_content(ws_root: str) -> str:
    """Read current wiki state as a single string for prompt context."""
    ws = Path(ws_root)
    parts = []
    index = ws / "wiki" / "index.md"
    if index.exists():
        parts.append(f"## Wiki Index\n{index.read_text(encoding='utf-8')}")
    for p in sorted((ws / "wiki" / "patterns").glob("*.md")):
        parts.append(f"### {p.stem}\n{p.read_text(encoding='utf-8')}")
    return "\n\n".join(parts) if parts else "(empty wiki)"


def update_wiki(ws_root: str, patterns: list[dict], log_entry: str) -> None:
    """Apply wiki maintainer output: create/update pattern files, append to logs."""
    ws = Path(ws_root)
    patterns_dir = ws / "wiki" / "patterns"
    index = ws / "wiki" / "index.md"
    logs = ws / "wiki" / "logs.md"

    for pat in patterns:
        action = pat.get("action", "")
        name = pat.get("name", "unnamed")
        content = pat.get("content", "")
        pfile = patterns_dir / f"{name}.md"
        if action == "create":
            pfile.write_text(content, encoding="utf-8")
        elif action == "update" and pfile.exists():
            pfile.write_text(content, encoding="utf-8")
        # Update index
        idx_text = index.read_text(encoding="utf-8") if index.exists() else ""
        entry = f"- **{name}** — {content.splitlines()[0] if content else 'pattern'}\n"
        if name not in idx_text:
            index.write_text(idx_text + entry, encoding="utf-8")

    # Append log entry
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logs.write_text(
        (logs.read_text(encoding="utf-8") if logs.exists() else "") + f"- [{ts}] {log_entry}\n",
        encoding="utf-8",
    )


def append_skill_impact(
    ws_root: str, iteration: int, proposal: dict, r_val: float, accepted: bool
) -> None:
    """Append to wiki/skill-impact.md for audit trail."""
    ws = Path(ws_root)
    si = ws / "wiki" / "skill-impact.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"## Iteration {iteration} [{ts}]\n"
        f"- Action: {proposal.get('action', 'unknown')}\n"
        f"- Skill: {proposal.get('skill_name', 'unknown')}\n"
        f"- Summary: {proposal.get('summary', 'N/A')}\n"
        f"- Validation score: {r_val:.4f}\n"
        f"- Accepted: {accepted}\n\n"
    )
    si.write_text(
        (si.read_text(encoding="utf-8") if si.exists() else "") + entry,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# LLM backend
# ---------------------------------------------------------------------------

def call_llm_subprocess(prompt: str, command: str) -> str:
    """Call LLM via subprocess: prompt on stdin, response on stdout."""
    result = subprocess.run(
        command, shell=True, input=prompt, capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLM command failed: {result.stderr}")
    return result.stdout


def call_llm_subprocess_json(prompt: str, command: str) -> dict:
    """Call LLM via subprocess, parse JSON from stdout."""
    raw = call_llm_subprocess(prompt, command)
    # Try to extract JSON from the response
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Iteration driver
# ---------------------------------------------------------------------------

def _load_tasks(path: str) -> list[dict]:
    """Load task list from JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _get_active_skill(ws_root: str) -> tuple[str, str]:
    """Return (skill_name, skill_content) for the active skill."""
    ws = Path(ws_root)
    skills_dir = ws / "skills"
    for d in sorted(skills_dir.iterdir()):
        skill_md = d / "SKILL.md"
        if skill_md.exists():
            return d.name, skill_md.read_text(encoding="utf-8")
    return "default", ""


def _snapshot_skills(ws_root: str) -> dict[str, str]:
    """Snapshot all skill files for rollback. Returns {relative_path: content}."""
    ws = Path(ws_root)
    snapshot = {}
    skills_dir = ws / "skills"
    if skills_dir.exists():
        for f in skills_dir.rglob("*.md"):
            rel = f.relative_to(ws)
            snapshot[str(rel)] = f.read_text(encoding="utf-8")
    return snapshot


def _restore_skills(ws_root: str, snapshot: dict[str, str]) -> None:
    """Restore skills from snapshot."""
    ws = Path(ws_root)
    skills_dir = ws / "skills"
    # Clear current skills
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in snapshot.items():
        f = ws / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")


def run_iteration(
    ws_root: str,
    train_tasks: list[dict],
    val_tasks: list[dict],
    iteration: int,
    scorer_fn,
    agent_fn=None,
    completion_fn=None,
    llm_command: str | None = None,
) -> dict:
    """Run one iteration of the WikiSkill loop.

    agent_fn: Callable[[str], str] — for inference and skill proposal (ReAct)
    completion_fn: Callable[[str], str] — for wiki maintenance (oneshot)
    llm_command: shell command template; if agent_fn/completion_fn not provided,
                 use this to call LLM via subprocess
    """
    ws = Path(ws_root)
    state = load_state(ws_root)

    # Resolve LLM callables
    def _agent(prompt: str) -> str:
        if agent_fn:
            return agent_fn(prompt)
        if llm_command:
            return call_llm_subprocess(prompt, llm_command)
        raise RuntimeError("No LLM backend: pass agent_fn or --llm-command")

    def _completion(prompt: str) -> str:
        if completion_fn:
            return completion_fn(prompt)
        if llm_command:
            return call_llm_subprocess(prompt, llm_command)
        raise RuntimeError("No LLM backend: pass completion_fn or --llm-command")

    def _completion_json(prompt: str) -> dict:
        if completion_fn:
            return _parse_json(completion_fn(prompt))
        if llm_command:
            return call_llm_subprocess_json(prompt, llm_command)
        raise RuntimeError("No LLM backend: pass completion_fn or --llm-command")

    # --- Phase 1: Inference Rollout ---
    skill_name, skill_content = _get_active_skill(ws_root)
    trace_dir = ws / "raw" / "traces" / f"iteration-{iteration}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    traces = []
    for task in train_tasks:
        task_id = task.get("id", str(task.get("task_id", "")))
        prompt = INFERENCE_PROMPT_TEMPLATE.format(
            skill_content=skill_content,
            task_description=task.get("description", task.get("task", "")),
        )
        try:
            response = _agent(prompt)
        except Exception as e:
            response = f"[ERROR] {e}"
        trace = {"task_id": task_id, "response": response, "trace": response}

        # Determine pass/fail from response
        answer = response
        if "ANSWER:" in response:
            answer = response.split("ANSWER:")[-1].strip()
        score = scorer_fn(task, answer)
        trace["passed"] = score >= 0.5
        trace["score"] = score

        (trace_dir / f"{task_id}.json").write_text(
            json.dumps(trace, indent=2), encoding="utf-8"
        )
        traces.append(trace)

    # --- Phase 2: Wiki Maintenance ---
    sampled = sample_traces(traces)
    traces_text = "\n\n".join(
        f"### Task {t['task_id']} ({'PASS' if t['passed'] else 'FAIL'})\n{t['trace']}"
        for t in sampled
    )
    wiki_content = _read_wiki_content(ws_root)

    wiki_prompt = (WIKI_MAINTAINER_PROMPT
        .replace("{wiki_content}", wiki_content)
        .replace("{traces_content}", traces_text))
    try:
        wiki_output = _completion_json(wiki_prompt)
        update_wiki(
            ws_root,
            wiki_output.get("patterns", []),
            wiki_output.get("log_entry", f"Iteration {iteration}: wiki updated"),
        )
    except Exception as e:
        print(f"  [wiki] error: {e}", file=sys.stderr)

    # --- Phase 3: Skill Proposal ---
    wiki_index = (ws / "wiki" / "index.md").read_text(encoding="utf-8")
    skill_impact = (ws / "wiki" / "skill-impact.md").read_text(encoding="utf-8")
    n_pass = sum(1 for t in traces if t["passed"])
    n_total = len(traces)
    training_summary = f"Training: {n_pass}/{n_total} passed ({n_pass/max(n_total,1)*100:.0f}%)"
    proposer_prompt = (SKILL_PROPOSER_PROMPT
        .replace("{wiki_index}", wiki_index or "(empty)")
        .replace("{skill_impact}", skill_impact or "(no prior proposals)")
        .replace("{training_summary}", training_summary)
        .replace("{skill_content}", skill_content or "(empty skill)"))

    try:
        proposal = _parse_json(_agent(proposer_prompt))
    except Exception:
        proposal = {"action": "no_action", "summary": "proposal parsing failed"}
    snapshot = _snapshot_skills(ws_root)

    # Apply proposal
    action = proposal.get("action", "no_action")
    if action == "create":
        new_name = proposal.get("skill_name", "proposed-skill")
        new_dir = ws / "skills" / new_name
        new_dir.mkdir(parents=True, exist_ok=True)
        (new_dir / "SKILL.md").write_text(
            proposal.get("full_content", ""), encoding="utf-8"
        )
        (new_dir / "PURPOSE.md").write_text(
            f"# Purpose\n\n{proposal.get('purpose', '')}\n", encoding="utf-8"
        )
    elif action == "patch":
        skill_name, skill_content = _get_active_skill(ws_root)
        skill_file = ws / "skills" / skill_name / "SKILL.md"
        old_content = skill_file.read_text(encoding="utf-8")
        new_content = old_content
        for patch in proposal.get("patches", []):
            try:
                new_content = apply_patch(
                    new_content,
                    patch.get("op", "append"),
                    patch.get("target", ""),
                    patch.get("content", ""),
                )
            except ValueError as e:
                print(f"  [patch] skipped: {e}", file=sys.stderr)
        skill_file.write_text(new_content, encoding="utf-8")

    # Validation inference
    val_traces = []
    _, val_skill = _get_active_skill(ws_root)
    for task in val_tasks:
        task_id = task.get("id", str(task.get("task_id", "")))
        prompt = INFERENCE_PROMPT_TEMPLATE.format(
            skill_content=val_skill,
            task_description=task.get("description", task.get("task", "")),
        )
        try:
            response = _agent(prompt)
        except Exception as e:
            response = f"[ERROR] {e}"
        answer = response
        if "ANSWER:" in response:
            answer = response.split("ANSWER:")[-1].strip()
        score = scorer_fn(task, answer)
        val_traces.append({"task_id": task_id, "score": score, "passed": score >= 0.5})

    r_val = sum(t["score"] for t in val_traces) / max(len(val_traces), 1)
    r_best = state.get("r_best", 0.0)
    accepted = r_val > r_best

    if not accepted:
        # Rollback skills (wiki persists)
        _restore_skills(ws_root, snapshot)

    # Record skill impact
    append_skill_impact(ws_root, iteration, proposal, r_val, accepted)

    # Update state
    state["iteration"] = iteration
    state["r_best"] = max(r_val, r_best) if accepted else r_best
    if accepted:
        state["r_best"] = r_val
    state["history"].append({
        "k": iteration,
        "r_val": r_val,
        "r_best": state["r_best"],
        "accepted": accepted,
        "proposal_summary": proposal.get("summary", action),
    })
    save_state(ws_root, state)

    return {
        "iteration": iteration,
        "r_val": r_val,
        "r_best": state["r_best"],
        "accepted": accepted,
        "n_train": n_total,
        "n_train_pass": n_pass,
    }


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[1:end])
    return json.loads(text)


# ---------------------------------------------------------------------------
# Evolution loop
# ---------------------------------------------------------------------------

def run_evolution(
    ws_root: str,
    train_tasks: list[dict],
    val_tasks: list[dict],
    max_iters: int = 8,
    scorer_fn=None,
    agent_fn=None,
    completion_fn=None,
    llm_command: str | None = None,
) -> dict:
    """Run the full WikiSkill evolution loop.

    1. Baseline validation (iteration 0)
    2. Iterate up to max_iters
    3. Early termination if r_best >= 1.0
    """
    if scorer_fn is None:
        scorer_fn = default_scorer

    state = load_state(ws_root)
    # Baseline validation (iteration 0): seed r_best so first proposal gates against it
    if state.get("iteration", 0) == 0:
        print("=== Baseline validation (iteration 0) ===", file=sys.stderr)
        r_baseline = _run_validation(
            ws_root, val_tasks, scorer_fn,
            agent_fn=agent_fn, llm_command=llm_command,
        )
        state["r_best"] = r_baseline
        state["history"].append({
            "k": 0, "r_val": r_baseline, "r_best": r_baseline,
            "accepted": False,
            "proposal_summary": "baseline (no skill change)",
        })
        save_state(ws_root, state)
        print(f"  r_baseline={r_baseline:.4f}", file=sys.stderr)
    start_iter = state.get("iteration", 0) + 1
    for k in range(start_iter, start_iter + max_iters):
        print(f"=== Iteration {k} ===", file=sys.stderr)
        result = run_iteration(
            ws_root, train_tasks, val_tasks, k,
            scorer_fn=scorer_fn,
            agent_fn=agent_fn,
            completion_fn=completion_fn,
            llm_command=llm_command,
        )
        print(
            f"  r_val={result['r_val']:.4f} r_best={result['r_best']:.4f} "
            f"accepted={result['accepted']}",
            file=sys.stderr,
        )
        if result["r_best"] >= 1.0:
            print("  Early termination: r_best >= 1.0", file=sys.stderr)
            break

    return load_state(ws_root)


def _run_validation(
    ws_root: str, val_tasks: list[dict], scorer_fn,
    agent_fn=None, llm_command: str | None = None,
) -> float:
    """Run validation inference with current skills, return mean score."""
    def _agent(prompt: str) -> str:
        if agent_fn:
            return agent_fn(prompt)
        if llm_command:
            return call_llm_subprocess(prompt, llm_command)
        raise RuntimeError("No LLM backend")

    _, skill_content = _get_active_skill(ws_root)
    scores = []
    for task in val_tasks:
        prompt = INFERENCE_PROMPT_TEMPLATE.format(
            skill_content=skill_content,
            task_description=task.get("description", task.get("task", "")),
        )
        try:
            response = _agent(prompt)
        except Exception as e:
            response = f"[ERROR] {e}"
        answer = response
        if "ANSWER:" in response:
            answer = response.split("ANSWER:")[-1].strip()
        scores.append(scorer_fn(task, answer))
    return sum(scores) / max(len(scores), 1)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def generate_report(ws_root: str) -> str:
    """Generate a human-readable report of the evolution run."""
    ws = Path(ws_root)
    state = load_state(ws_root)
    lines = ["# WikiSkill Report", ""]

    # Score trajectory
    lines.append("## Score Trajectory")
    lines.append("")
    lines.append("| Iteration | r_val | r_best | Accepted | Summary |")
    lines.append("|-----------|-------|--------|----------|---------|")
    for h in state.get("history", []):
        lines.append(
            f"| {h['k']} | {h['r_val']:.4f} | {h.get('r_best', 0.0):.4f} | "
            f"{'✓' if h['accepted'] else '✗'} | {h.get('proposal_summary', '')} |"
        )
    lines.append("")

    # Accepted/rejected counts
    accepted = sum(1 for h in state["history"] if h["accepted"])
    rejected = len(state["history"]) - accepted
    lines.append(f"- Total iterations: {len(state['history'])}")
    lines.append(f"- Accepted: {accepted}")
    lines.append(f"- Rejected: {rejected}")
    lines.append(f"- Best score: {state.get('r_best', 0.0):.4f}")
    lines.append("")

    # Pattern catalog
    patterns_dir = ws / "wiki" / "patterns"
    patterns = sorted(patterns_dir.glob("*.md")) if patterns_dir.exists() else []
    lines.append(f"## Pattern Catalog ({len(patterns)} patterns)")
    for p in patterns:
        first_line = p.read_text(encoding="utf-8").split("\n")[0].strip("# ")
        lines.append(f"- **{p.stem}** — {first_line}")
    lines.append("")

    # Final skill diff
    skill_impact = ws / "wiki" / "skill-impact.md"
    if skill_impact.exists() and skill_impact.read_text(encoding="utf-8").strip():
        lines.append("## Skill Impact Log")
        lines.append("```")
        lines.append(skill_impact.read_text(encoding="utf-8"))
        lines.append("```")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="WikiSkill: co-evolve agent skills with a persistent knowledge base."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Initialize workspace")
    p_init.add_argument("--workspace", required=True, help="Workspace directory path")
    p_init.add_argument("--target", default=None, help="Path to seed skill (dir or SKILL.md)")

    # run
    p_run = sub.add_parser("run", help="Run evolution loop")
    p_run.add_argument("--workspace", required=True, help="Workspace directory path")
    p_run.add_argument("--train-tasks", required=True, help="JSON file with training tasks")
    p_run.add_argument("--val-tasks", required=True, help="JSON file with validation tasks")
    p_run.add_argument("--max-iters", type=int, default=8, help="Max iterations (default: 8)")
    p_run.add_argument("--scorer", default=None, help="Scorer as module:func (default: exact-match)")
    p_run.add_argument(
        "--llm-command", default=None,
        help="Shell command for LLM calls (prompt on stdin, response on stdout)",
    )

    # status
    p_status = sub.add_parser("status", help="Show current state")
    p_status.add_argument("--workspace", required=True, help="Workspace directory path")

    # report
    p_report = sub.add_parser("report", help="Print evolution report")
    p_report.add_argument("--workspace", required=True, help="Workspace directory path")

    args = parser.parse_args(argv)

    if args.command == "init":
        ws = init_workspace(args.workspace, args.target)
        print(f"Initialized workspace: {ws}")
        return 0

    elif args.command == "run":
        train_tasks = _load_tasks(args.train_tasks)
        val_tasks = _load_tasks(args.val_tasks)
        scorer_fn = load_scorer(args.scorer)
        state = run_evolution(
            args.workspace, train_tasks, val_tasks,
            max_iters=args.max_iters,
            scorer_fn=scorer_fn,
            llm_command=args.llm_command,
        )
        print(f"\nFinal state: iteration={state['iteration']}, r_best={state['r_best']:.4f}")
        return 0

    elif args.command == "status":
        state = load_state(args.workspace)
        print(json.dumps(state, indent=2))
        return 0

    elif args.command == "report":
        print(generate_report(args.workspace))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
