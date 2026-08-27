#!/usr/bin/env python3
"""Cost rollups for OMP sessions."""
import argparse
from datetime import datetime, timezone

from sessions import find_session_files, filter_sessions


def main():
    parser = argparse.ArgumentParser(description="Cost rollups for OMP sessions")
    parser.add_argument("--since", help="Only sessions since (e.g. 7d)")
    parser.add_argument("--until", help="Only sessions until")
    parser.add_argument("--cwd", help="Filter by session cwd")
    parser.add_argument("--by", choices=["total", "day", "project", "model", "session"], default="day", help="Grouping")
    parser.add_argument("--limit", type=int, help="Max groups")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    files = find_session_files()
    sessions = filter_sessions(files, since=args.since, until=args.until, cwd=args.cwd)

    if not sessions:
        print("No sessions found.", file=open('/dev/stderr', 'w'))
        return

    if args.by == "total":
        total_cost = sum(s["cost"] for s in sessions)
        total_tokens = sum(s["tokens"] for s in sessions)
        if args.json:
            print(f'{{"cost": {total_cost:.4f}, "tokens": {total_tokens}}}')
        else:
            print(f"Total cost: ${total_cost:.4f}")
            print(f"Total tokens: {total_tokens:,}")
        return

    if args.by == "day":
        by_day = {}
        for s in sessions:
            ts = s["meta"].get("timestamp", "")
            day = ts[:10] if ts else "unknown"
            if day not in by_day:
                by_day[day] = {"cost": 0, "tokens": 0, "sessions": 0}
            by_day[day]["cost"] += s["cost"]
            by_day[day]["tokens"] += s["tokens"]
            by_day[day]["sessions"] += 1
        rows = sorted(by_day.items(), key=lambda x: x[0], reverse=True)
        if args.limit:
            rows = rows[:args.limit]
        if args.json:
            print("[")
            for day, v in rows:
                print(f'  {{"day": {day!r}, "cost": {v["cost"]:.4f}, "tokens": {v["tokens"]}, "sessions": {v["sessions"]}}}')
            print("]")
        else:
            print(f"{'Day':<12} {'Sessions':<10} {'Cost':<12} {'Tokens'}")
            print("-" * 50)
            for day, v in rows:
                print(f"{day:<12} {v['sessions']:<10} ${v['cost']:<11.4f} {v['tokens']:,}")
        return

    if args.by == "project":
        by_proj = {}
        for s in sessions:
            cwd = s["meta"].get("cwd", "unknown")
            if cwd not in by_proj:
                by_proj[cwd] = {"cost": 0, "tokens": 0, "sessions": 0}
            by_proj[cwd]["cost"] += s["cost"]
            by_proj[cwd]["tokens"] += s["tokens"]
            by_proj[cwd]["sessions"] += 1
        rows = sorted(by_proj.items(), key=lambda x: -x[1]["cost"])
        if args.limit:
            rows = rows[:args.limit]
        if args.json:
            print("[")
            for cwd, v in rows:
                print(f'  {{"project": {cwd!r}, "cost": {v["cost"]:.4f}, "tokens": {v["tokens"]}, "sessions": {v["sessions"]}}}')
            print("]")
        else:
            print(f"{'Project':<40} {'Sessions':<10} {'Cost':<12} {'Tokens'}")
            print("-" * 70)
            for cwd, v in rows:
                print(f"{cwd[:38]:<40} {v['sessions']:<10} ${v['cost']:<11.4f} {v['tokens']:,}")
        return

    if args.by == "session":
        rows = sorted(sessions, key=lambda s: -s["cost"])
        if args.limit:
            rows = rows[:args.limit]
        if args.json:
            print("[")
            for s in rows:
                meta = s["meta"]
                print(f'  {{"id": {meta.get("id", "")!r}, "title": {meta.get("title", "")!r}, "timestamp": {meta.get("timestamp", "")!r}, "cost": {s["cost"]:.4f}, "tokens": {s["tokens"]}}}')
            print("]")
        else:
            print(f"{'Session':<40} {'Cost':<12} {'Tokens':<12} {'ID'}")
            print("-" * 80)
            for s in rows:
                meta = s["meta"]
                title = (meta.get("title", "") or "Untitled")[:38]
                sid = meta.get("id", "")[:12]
                print(f"{title:<40} ${s['cost']:<11.4f} {s['tokens']:<12,} {sid}")


if __name__ == "__main__":
    main()
