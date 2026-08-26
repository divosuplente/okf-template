#!/usr/bin/env python3
"""Check YouTube channels for new videos and write ingestion tasks.

Cron-friendly, zero-config after setup. Fast: only enumerates channel videos
via yt-dlp (flat extraction, no downloads). Writes task files to inbox/ for
the nightly ingest pipeline to pick up.

Usage:
    python3 tools/channel_check.py add @Handle [--label Name] [--since 1y]
    python3 tools/channel_check.py list
    python3 tools/channel_check.py check [@Handle]         # no arg = all active
    python3 tools/channel_check.py remove @Handle
    python3 tools/channel_check.py migrate                 # import existing manifests
"""

import argparse
import json
import re
import subprocess
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "channel_check.db"
INBOX_DIR = Path(__file__).parent.parent / "inbox"

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    _init_db(db)
    return db


def _init_db(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            id                INTEGER PRIMARY KEY,
            handle            TEXT UNIQUE NOT NULL,
            url               TEXT UNIQUE NOT NULL,
            label             TEXT,
            since             TEXT,
            active            INTEGER DEFAULT 1,
            created_at        TEXT DEFAULT (datetime('now')),
            last_checked_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS videos (
            id              INTEGER PRIMARY KEY,
            channel_id      INTEGER NOT NULL REFERENCES channels(id),
            youtube_id      TEXT NOT NULL,
            title           TEXT,
            url             TEXT,
            published       TEXT,
            status          TEXT DEFAULT 'pending',
            UNIQUE(channel_id, youtube_id)
        );

        CREATE TABLE IF NOT EXISTS check_runs (
            id              INTEGER PRIMARY KEY,
            channel_id      INTEGER NOT NULL REFERENCES channels(id),
            checked_at      TEXT DEFAULT (datetime('now')),
            new_found       INTEGER DEFAULT 0,
            task_file       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id, youtube_id);
        CREATE INDEX IF NOT EXISTS idx_channels_active ON channels(active, last_checked_at);
    """)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def normalize_channel_url(channel: str) -> str:
    if channel.startswith("http"):
        return channel
    return f"https://www.youtube.com/{channel}/videos"


def parse_since(spec: str | None) -> str | None:
    if not spec:
        return None
    today = datetime.now(timezone.utc).date()
    m = re.match(r"^(\d+)([yd])$", spec.strip())
    if m:
        val, unit = int(m.group(1)), m.group(2)
        delta = timedelta(days=val * 365) if unit == "y" else timedelta(days=val)
        return (today - delta).isoformat()
    m = re.match(r"^\d{4}-?\d{2}-?\d{2}$", spec.strip())
    if m:
        raw = spec.strip().replace("-", "")
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def upload_date_str(entry: dict) -> str:
    """Return YYYY-MM-DD from yt-dlp entry, or empty string."""
    # upload_date is YYYYMMDD; timestamp is epoch float
    val = entry.get("upload_date")
    if val and len(str(val)) == 8:
        d = str(val)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return ""


def _filter_new_by_since(entries: list[dict], since: str) -> list[dict]:
    """Fetch upload dates for new videos in chunks, filter by since."""
    if not entries:
        return []

    BATCH_SIZE = 30
    date_map = {}

    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i:i + BATCH_SIZE]
        urls = [e.get("url", f"https://www.youtube.com/watch?v={e.get('id')}") for e in batch if e.get("id")]
        if not urls:
            continue

        try:
            out = subprocess.run(
                ["yt-dlp", "--print", "%(id)s %(upload_date)s", "--quiet"] + urls,
                capture_output=True, text=True, timeout=120,
            )
            if out.returncode != 0 or not out.stdout.strip():
                continue
        except (subprocess.TimeoutExpired, Exception):
            continue

        for line in out.stdout.strip().splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                vid_id, date_str = parts
                if len(date_str) == 8:
                    date_map[vid_id] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    filtered = []
    for entry in entries:
        vid_id = entry.get("id")
        date = date_map.get(vid_id, "")
        if date and date >= since:
            entry["upload_date"] = date.replace("-", "")
            filtered.append(entry)
    return filtered


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:120]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args):
    db = get_db()
    url = normalize_channel_url(args.channel)
    since = parse_since(args.since)
    label = args.label or args.channel.lstrip("@").replace("-", " ").replace("_", " ").title()
    try:
        db.execute(
            "INSERT INTO channels (handle, url, label, since) VALUES (?, ?, ?, ?)",
            (args.channel, url, label, since),
        )
        db.commit()
        print(f"Added: {args.channel} ({label})")
        if since:
            print(f"  Since: {since}")
    except sqlite3.IntegrityError:
        print(f"Already registered: {args.channel}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    db = get_db()
    rows = db.execute(
        "SELECT c.handle, c.label, c.active, c.last_checked_at, "
        "COUNT(v.id) as video_count "
        "FROM channels c LEFT JOIN videos v ON c.id = v.channel_id "
        "GROUP BY c.id "
        "ORDER BY c.active DESC, c.last_checked_at DESC NULLS LAST"
    ).fetchall()
    if not rows:
        print("No channels registered. Use: channel_check.py add @Handle")
        return
    print(f"{'Handle':<25} {'Label':<25} {'Active':<8} {'Videos':<8} {'Last Checked'}")
    print("-" * 85)
    for r in rows:
        print(f"{r['handle']:<25} {r['label'] or '':<25} {'yes' if r['active'] else 'no':<8} {r['video_count']:<8} {r['last_checked_at'] or 'never'}")


def cmd_remove(args):
    db = get_db()
    cur = db.execute("DELETE FROM channels WHERE handle = ?", (args.channel,))
    db.commit()
    if cur.rowcount == 0:
        print(f"Not found: {args.channel}", file=sys.stderr)
        sys.exit(1)
    print(f"Removed: {args.channel}")


def cmd_check(args):
    db = get_db()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    if args.channel:
        channels = [
            db.execute("SELECT * FROM channels WHERE handle = ?", (args.channel,)).fetchone()
        ]
        if not channels[0]:
            print(f"Channel not found: {args.channel}", file=sys.stderr)
            sys.exit(1)
    else:
        channels = db.execute("SELECT * FROM channels WHERE active = 1").fetchall()

    if not channels:
        print("No active channels to check.")
        return

    total_new = 0
    total_tasks = 0
    for ch in channels:
        new_count, task_file = _check_channel(db, ch, dry_run=args.dry_run)
        total_new += new_count
        if task_file:
            total_tasks += 1

    print(f"\nSummary: {total_new} new videos found across {len(channels)} channel(s), {total_tasks} task file(s) written")

    # Commit and push if task files were written
    if total_tasks > 0 and not args.dry_run:
        _git_commit_push(total_tasks)


def _check_channel(db: sqlite3.Connection, ch: sqlite3.Row, dry_run: bool = False) -> tuple[int, str | None]:
    ch_id = ch["id"]
    handle = ch["handle"]
    url = ch["url"]
    since = ch["since"]
    label = ch["label"] or handle

    print(f"\n{'='*60}")
    print(f"Checking: {label} ({handle})")

    if dry_run:
        existing = db.execute(
            "SELECT COUNT(*) as cnt FROM videos WHERE channel_id = ?", (ch_id,)
        ).fetchone()["cnt"]
        print(f"  [DRY RUN] Known videos: {existing}")
        return 0, None

    # Enumerate videos via yt-dlp --flat-playlist (fast; no per-video metadata)
    try:
        out = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json", "--quiet", url],
            capture_output=True, text=True, timeout=120,
        )
        if out.returncode != 0:
            print(f"  ERROR enumerating: {out.stderr.strip()}", file=sys.stderr)
            return 0, None
        entries = [json.loads(line) for line in out.stdout.strip().splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"  ERROR enumerating: {e}", file=sys.stderr)
        return 0, None

    if not entries:
        print("  No videos found.")
        return 0, None

    # Get known video IDs
    known_ids = {
        r["youtube_id"]
        for r in db.execute("SELECT youtube_id FROM videos WHERE channel_id = ?", (ch_id,)).fetchall()
    }

    # Find new videos (not yet in DB)
    new_entries = [e for e in entries if e.get("id") not in known_ids]

    print(f"  Total visible: {len(entries)}, Known: {len(known_ids)}, New: {len(new_entries)}")

    # If since is set, fetch upload dates for new videos only (targeted, fast)
    if since and new_entries:
        new_entries = _filter_new_by_since(new_entries, since)
        print(f"  After since={since}: {len(new_entries)} new")

    if not new_entries:
        print("  Nothing new.")
        db.execute("UPDATE channels SET last_checked_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), ch_id))
        db.commit()
        return 0, None

    # Record new videos in DB so they won't be re-detected
    for entry in new_entries:
        db.execute(
            "INSERT OR IGNORE INTO videos (channel_id, youtube_id, title, url, published, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ch_id, entry.get("id"), entry.get("title"), entry.get("url"), upload_date_str(entry), "pending"),
        )

    # Write task file to inbox
    task_file = _write_task_file(handle, label, new_entries, dry_run)

    # Update channel last_checked
    db.execute("UPDATE channels SET last_checked_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), ch_id))

    # Record run
    db.execute(
        "INSERT INTO check_runs (channel_id, new_found, task_file) VALUES (?, ?, ?)",
        (ch_id, len(new_entries), task_file),
    )
    db.commit()

    print(f"  Done: {len(new_entries)} new videos → {task_file}")
    return len(new_entries), task_file


def _write_task_file(handle: str, label: str, entries: list[dict], dry_run: bool) -> str | None:
    """Write a task file to inbox/ listing new videos to ingest."""
    if dry_run:
        return None

    channel_slug = re.sub(r"[^a-zA-Z0-9]", "", handle.lstrip("@")).lower()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"task-{channel_slug}-{timestamp}.md"
    filepath = INBOX_DIR / filename

    # Build video list
    video_lines = []
    for entry in entries:
        vid_id = entry.get("id", "")
        title = entry.get("title", "Untitled")
        url = entry.get("url", f"https://www.youtube.com/watch?v={vid_id}")
        published = upload_date_str(entry) or "unknown"
        video_lines.append(f"- [{title}]({url}) ({published})")

    content = f"""---
type: note
visibility: private
tags: [youtube, ingest-task]
generated: {{ by: process:channel-check, at: {datetime.now(timezone.utc).isoformat()} }}
---

# Task: Ingest new videos from {label} ({handle})

{len(entries)} new video(s) detected. Ingest each via the channel ingest pipeline.

## Videos

{chr(10).join(video_lines)}

## Instructions

Process each video through the OKF channel ingest pipeline:
1. Fetch transcript via yt-dlp
2. Extract concepts and entities
3. Write OKF concept pages
4. Cross-link to [{label}](/concepts/creators/general/{channel_slug}.md) creator page
"""

    filepath.write_text(content, encoding="utf-8")
    return str(filepath.relative_to(Path(__file__).parent.parent))


def _git_commit_push(task_count: int):
    """Commit and push task files (matches ingest_inbox.sh pattern)."""
    vault = Path(__file__).parent.parent
    try:
        subprocess.run(["git", "-C", str(vault), "add", str(INBOX_DIR)], capture_output=True, timeout=10)
        msg = f"channel check: {task_count} new ingestion task(s)"
        result = subprocess.run(
            ["git", "-C", str(vault), "commit", "-m", msg],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            print("  Committed task file(s).")
            push = subprocess.run(
                ["git", "-C", str(vault), "push", "origin", "HEAD"],
                capture_output=True, text=True, timeout=30,
            )
            if push.returncode != 0:
                print(f"  Warning: push failed: {push.stderr.strip()[:100]}")
            else:
                print("  Pushed.")
    except Exception as e:
        print(f"  Warning: git ops skipped: {e}")


def cmd_migrate(args):
    """Import existing manifest-*.json files into the DB."""
    db = get_db()
    raw_dir = Path(__file__).parent.parent / "raw" / "youtube"
    manifest_files = list(raw_dir.glob("manifest-*.json")) + [raw_dir / "manifest.json"]
    manifest_files = [m for m in manifest_files if m.is_file()]
    if not manifest_files:
        print("No manifest files found to migrate.")
        return

    for mf in manifest_files:
        with open(mf) as f:
            data = json.load(f)

        ch_url = data.get("channel", "")
        handle_match = re.search(r"@([^/]+)", ch_url)
        if not handle_match:
            print(f"  SKIP {mf.name}: couldn't extract handle from {ch_url}")
            continue
        handle = f"@{handle_match.group(1)}"

        existing = db.execute("SELECT id FROM channels WHERE handle = ?", (handle,)).fetchone()
        if existing:
            print(f"  SKIP {mf.name}: {handle} already in DB")
            continue

        label = mf.stem.replace("manifest-", "").replace("-", " ").title()
        since = data.get("since")

        try:
            cur = db.execute(
                "INSERT INTO channels (handle, url, label, since, last_checked_at) VALUES (?, ?, ?, ?, ?)",
                (handle, ch_url, label, since, data.get("fetched_at")),
            )
            ch_id = cur.lastrowid
        except sqlite3.IntegrityError:
            ch_row = db.execute("SELECT id FROM channels WHERE handle = ?", (handle,)).fetchone()
            ch_id = ch_row["id"]

        imported = 0
        for v in data.get("videos", []):
            vid_id = v.get("youtube_id") or v.get("id")
            if not vid_id:
                continue
            db.execute(
                "INSERT OR IGNORE INTO videos (channel_id, youtube_id, title, url, published, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ch_id, vid_id, v.get("title", ""), v.get("url", ""), v.get("published"), "ingested"),
            )
            imported += 1

        for v in data.get("skipped_videos", []):
            vid_id = v.get("id")
            if not vid_id:
                continue
            db.execute(
                "INSERT OR IGNORE INTO videos (channel_id, youtube_id, title, status) VALUES (?, ?, ?, ?)",
                (ch_id, vid_id, v.get("title", ""), "skipped"),
            )
            imported += 1

        db.commit()
        print(f"  Imported {mf.name}: {handle} — {imported} videos")

    print("Migration complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Check YouTube channels for new videos and write ingestion tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Register a channel to track")
    p_add.add_argument("channel", help="YouTube @handle or URL")
    p_add.add_argument("--label", help="Human-readable name")
    p_add.add_argument("--since", help="Only track videos since this date (1y, 2025-01-01)")

    sub.add_parser("list", help="List tracked channels")

    p_check = sub.add_parser("check", help="Check for new videos")
    p_check.add_argument("channel", nargs="?", help="Specific @handle (default: all active)")
    p_check.add_argument("--dry-run", action="store_true", help="Show counts without writing tasks")

    p_remove = sub.add_parser("remove", help="Remove a channel")
    p_remove.add_argument("channel", help="YouTube @handle")

    sub.add_parser("migrate", help="Import existing manifest-*.json into the database")

    args = ap.parse_args()
    dispatch = {"add": cmd_add, "list": cmd_list, "check": cmd_check, "remove": cmd_remove, "migrate": cmd_migrate}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
