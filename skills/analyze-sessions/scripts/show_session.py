#!/usr/bin/env python3
"""Render an OMP session as readable markdown."""
import argparse
import sys
from datetime import datetime, timezone

from sessions import find_session_files, filter_sessions, load_session


def render_session(sess: dict, include_subagents: bool = False, max_text: int = 4000) -> str:
    """Render a session to markdown."""
    meta = sess["meta"]
    lines = []
    lines.append(f"# {meta.get('title', 'Untitled Session')}")
    lines.append("")
    lines.append(f"- **ID:** {meta.get('id', 'N/A')}")
    lines.append(f"- **Time:** {meta.get('timestamp', 'N/A')}")
    lines.append(f"- **CWD:** {meta.get('cwd', 'N/A')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in sess["messages"]:
        role = msg["role"]
        text = msg["text"]
        if role in ("system", ""):
            continue
        if msg.get("custom") and "<system-reminder>" in text:
            continue
        prefix = {"user": "**You**", "assistant": "**Assistant**"}.get(role, f"**{role}**")
        if len(text) > max_text:
            text = text[:max_text] + "\n...[truncated]"
        lines.append(f"{prefix}:")
        lines.append(f"```")
        lines.append(text)
        lines.append(f"```")
        lines.append("")

    if include_subagents and sess["subagents"]:
        lines.append("---")
        lines.append("## Subagents")
        lines.append("")
        for spath in sess["subagents"]:
            try:
                sub = load_session(spath)
                sub_meta = sub["meta"]
                lines.append(f"### {sub_meta.get('title', Path(spath).stem)}")
                lines.append("")
                for msg in sub["messages"][:20]:
                    role = msg["role"]
                    if role in ("system", ""):
                        continue
                    prefix = {"user": "**User**", "assistant": "**Assistant**"}.get(role, f"**{role}**")
                    text = msg["text"][:500]
                    if len(msg["text"]) > 500:
                        text += "..."
                    lines.append(f"{prefix}: {text}")
                lines.append("")
            except Exception:
                pass

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Show an OMP session as markdown")
    parser.add_argument("--latest", action="store_true", help="Show most recent session")
    parser.add_argument("--session", help="Session id prefix (8 chars)")
    parser.add_argument("--since", help="Only sessions since")
    parser.add_argument("--cwd", help="Filter by cwd")
    parser.add_argument("--include-subagents", action="store_true", help="Include subagent transcripts")
    parser.add_argument("--max-text", type=int, default=4000, help="Max chars per message")
    args = parser.parse_args()

    files = find_session_files()
    sessions = filter_sessions(files, since=args.since, cwd=args.cwd)

    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(1)

    if args.session:
        # Find matching session
        target = None
        for s in sessions:
            if s["meta"].get("id", "").startswith(args.session):
                target = s
                break
        if not target:
            print(f"No session found with id prefix: {args.session}", file=sys.stderr)
            sys.exit(1)
    else:
        target = sessions[0]

    print(render_session(target, include_subagents=args.include_subagents, max_text=args.max_text))


if __name__ == "__main__":
    main()
