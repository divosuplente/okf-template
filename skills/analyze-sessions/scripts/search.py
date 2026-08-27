#!/usr/bin/env python3
"""Search across OMP session transcripts."""
import argparse
import re
import sys

from sessions import find_session_files, filter_sessions, load_session


def main():
    parser = argparse.ArgumentParser(description="Search OMP session transcripts")
    parser.add_argument("query", help="Search query (substring or regex)")
    parser.add_argument("--regex", action="store_true", help="Treat query as regex")
    parser.add_argument("--in", dest="role", choices=["user", "assistant", "all"], default="all", help="Filter by message role")
    parser.add_argument("--context", type=int, default=1, help="Lines of context per match")
    parser.add_argument("--since", help="Only sessions since (e.g. 7d, 2026-01-01)")
    parser.add_argument("--until", help="Only sessions until")
    parser.add_argument("--cwd", action="append", help="Filter by session cwd (repeatable)")
    parser.add_argument("--limit", type=int, help="Max results")
    args = parser.parse_args()

    files = find_session_files()
    sessions = filter_sessions(files, since=args.since, until=args.until, cwd=args.cwd[0] if args.cwd else None)

    pattern = re.compile(args.query, re.IGNORECASE) if args.regex else None
    query_lower = args.query.lower()

    count = 0
    for sess in sessions:
        meta = sess["meta"]
        session_id = meta.get("id", "")
        session_ts = meta.get("timestamp", "")
        session_title = meta.get("title", "Untitled")
        session_cwd = meta.get("cwd", "")

        matched_messages = []
        for i, msg in enumerate(sess["messages"]):
            role = msg["role"]
            if args.role != "all" and role != args.role:
                continue
            text = msg["text"]
            if pattern:
                if pattern.search(text):
                    matched_messages.append((i, msg))
            elif query_lower in text.lower():
                matched_messages.append((i, msg))

        if not matched_messages:
            continue

        print(f"\n{'='*72}")
        print(f"Session: {session_title}")
        print(f"ID: {session_id}")
        print(f"Time: {session_ts}")
        print(f"CWD: {session_cwd}")
        print(f"{'='*72}")

        for idx, msg in matched_messages[:args.limit]:
            print(f"\n  [{msg['role']}] (message {idx})")
            # Show context
            start = max(0, idx - args.context)
            end = min(len(sess["messages"]), idx + args.context + 1)
            for ci in range(start, end):
                cm = sess["messages"][ci]
                marker = ">> " if ci == idx else "   "
                text_preview = cm["text"][:200]
                if len(cm["text"]) > 200:
                    text_preview += "..."
                print(f"  {marker}[{cm['role']}] {text_preview}")
            count += 1

        print(f"\n  drill: python3 {sys.argv[0].replace('search.py', 'show_session.py')} --session {session_id[:8]}")

    if count == 0:
        print("No matches found.", file=sys.stderr)


if __name__ == "__main__":
    main()
