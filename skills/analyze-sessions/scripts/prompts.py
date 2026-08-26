#!/usr/bin/env python3
"""Dump user prompts from agent sessions for pattern mining."""
import argparse
import json
import sys
from collections import defaultdict

from sessions import find_session_files, filter_sessions


def main():
    parser = argparse.ArgumentParser(description="Dump user prompts for pattern mining")
    parser.add_argument("--since", help="Only sessions since (e.g. 7d)")
    parser.add_argument("--until", help="Only sessions until")
    parser.add_argument("--cwd", help="Filter by cwd")
    parser.add_argument("--max-chars", type=int, default=2000, help="Max chars per prompt (drop longer)")
    parser.add_argument("--format", choices=["markdown", "jsonl"], default="markdown", help="Output format")
    parser.add_argument("--grep", help="Only sessions where prompts contain this substring")
    args = parser.parse_args()

    files = find_session_files()
    sessions = filter_sessions(files, since=args.since, until=args.until, cwd=args.cwd)
    if args.format == "jsonl":
        for sess in sessions:
            for msg in sess["messages"]:
                if msg["role"] != "user":
                    continue
                if len(msg["text"]) > args.max_chars:
                    continue
                if args.grep and args.grep.lower() not in msg["text"].lower():
                    continue
                print(json.dumps({
                    "session_id": sess["meta"].get("id", ""),
                    "timestamp": sess["meta"].get("timestamp", ""),
                    "cwd": sess["meta"].get("cwd", ""),
                    "prompt": msg["text"],
                }))
    else:
        by_project = defaultdict(list)
        for sess in sessions:
            cwd = sess["meta"].get("cwd", "unknown")
            title = sess["meta"].get("title", "Untitled")
            ts = sess["meta"].get("timestamp", "")
            for msg in sess["messages"]:
                if msg["role"] != "user":
                    continue
                if len(msg["text"]) > args.max_chars:
                    continue
                if args.grep and args.grep.lower() not in msg["text"].lower():
                    continue
                by_project[cwd].append({
                    "title": title,
                    "ts": ts,
                    "prompt": msg["text"],
                    "id": sess["meta"].get("id", ""),
                })

        if not by_project:
            print("No prompts found.", file=sys.stderr)
            return

        print("# User Prompts by Project")
        print("")
        for proj in sorted(by_project.keys()):
            prompts = by_project[proj]
            print(f"## `{proj}` ({len(prompts)} prompts)")
            print("")
            for p in sorted(prompts, key=lambda x: x["ts"], reverse=True):
                print(f"- **{p['ts'][:10]}** ({p['title'][:60]})")
                preview = p["prompt"].strip().replace("\n", " ")[:150]
                if len(p["prompt"]) > 150:
                    preview += "..."
                print(f"  `{preview}`")
                print("")


if __name__ == "__main__":
    main()
