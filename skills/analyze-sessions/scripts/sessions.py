"""Shared session loading utilities for analyze-sessions scripts."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSIONS_DIR = Path(__file__).resolve().parent / ".." / ".." / ".." / ".." / ".agent" / "sessions"
SESSIONS_DIR = SESSIONS_DIR.resolve()
# Fallback: use absolute path if relative doesn't resolve
if not SESSIONS_DIR.exists():
    SESSIONS_DIR = Path.home() / ".agent" / "sessions"


def parse_relative_time(when: str) -> datetime:
    """Parse relative time strings like '7d', '2w', '3h', '30m' or ISO dates."""
    if not when:
        return datetime.min.replace(tzinfo=timezone.utc)
    when = when.strip()
    # Relative: 7d, 2w, 3h, 30m
    import re
    m = re.match(r"^(\d+)([dhwm])$", when)
    if m:
        val, unit = int(m.group(1)), m.group(2)
        now = datetime.now(timezone.utc)
        return now - {"d": timedelta(days=val), "w": timedelta(weeks=val), "h": timedelta(hours=val), "m": timedelta(minutes=val)}[unit]
    # ISO date/datetime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            dt = datetime.strptime(when, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {when}")


def find_session_files() -> list[str]:
    """Find all session JSONL files (no subagent JSONLs)."""
    if not SESSIONS_DIR.exists():
        return []
    results = []
    for project_dir in SESSIONS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        for f in sorted(project_dir.glob("*.jsonl"), reverse=True):
            results.append(str(f))
    return results


def load_session(path: str) -> dict:
    """Load a session JSONL file, returning metadata and messages."""
    meta = None
    messages = []
    total_cost = 0.0
    total_tokens = 0
    subagent_files = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") == "session":
                meta = record
            elif record.get("type") == "message":
                msg = record.get("message", {})
                role = msg.get("role", "")
                usage = msg.get("usage")
                content = msg.get("content", [])
                text = ""
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text += part.get("text", "")
                elif isinstance(content, str):
                    text = content
                if text.strip():
                    messages.append({"role": role, "text": text.strip(), "id": msg.get("id", ""), "timestamp": msg.get("timestamp", ""), "usage": usage})
                # Accumulate cost from assistant messages
                if role == "assistant" and usage and usage.get("cost"):
                    total_cost += usage["cost"].get("total", 0)
                    total_tokens += usage.get("totalTokens", 0)
            elif record.get("type") == "custom_message":
                content = record.get("content", "")
                attribution = record.get("attribution", "")
                if isinstance(content, str) and content.strip():
                    messages.append({"role": attribution, "text": content.strip(), "id": record.get("id", ""), "timestamp": record.get("timestamp", ""), "custom": True})
    # Find subagent files
    session_dir = Path(path).parent
    if session_dir.exists():
        for f in sorted(session_dir.glob("*.jsonl")):
            if f.name != Path(path).name:
                subagent_files.append(str(f))
    return {"meta": meta or {}, "messages": messages, "path": path, "subagents": subagent_files, "cost": total_cost, "tokens": total_tokens}


def filter_sessions(files: list[str], since: str = None, until: str = None, cwd: str = None, limit: int = None) -> list[dict]:
    """Load and filter sessions by time range and optional cwd."""
    since_dt = parse_relative_time(since) if since else datetime.min.replace(tzinfo=timezone.utc)
    until_dt = parse_relative_time(until) if until else datetime.max.replace(tzinfo=timezone.utc)
    results = []
    for path in files:
        try:
            sess = load_session(path)
        except Exception:
            continue
        ts = sess["meta"].get("timestamp", "")
        try:
            session_dt = datetime.fromisoformat(ts)
            if session_dt.tzinfo is None:
                session_dt = session_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if session_dt < since_dt or session_dt > until_dt:
            continue
        if cwd and cwd.lower() not in sess["meta"].get("cwd", "").lower():
            continue
        results.append(sess)
    if limit:
        results = results[:limit]
    return results
