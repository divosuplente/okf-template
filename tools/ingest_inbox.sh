#!/bin/bash
set -euo pipefail

# OKF Inbox Ingest — processes .md files in inbox/
# Uses the OKF ingest.py tool to ingest each file as a concept.
# Deletes source on success, moves failures to inbox/failed/.
# Commits and pushes changes to origin.

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
INBOX="$VAULT/inbox"
FAILED="$INBOX/failed"
TOOL="$VAULT/tools/ingest.py"
LOG="$VAULT/log.md"
FAIL_LOG="$FAILED/reasons.log"

# Ensure output dirs exist
mkdir -p "$FAILED"

# Purge inbox/processed files that have been sitting there more than 7 days.
# mtime-based: mv preserves mtime, so it reflects time spent in the folder.
PROCESSED="$INBOX/processed"
if [ -d "$PROCESSED" ]; then
    PURGED=$(find "$PROCESSED" -maxdepth 1 -type f -mtime +7 -delete -print | wc -l | tr -d ' ')
    [ "$PURGED" -gt 0 ] && echo "Purged $PURGED processed file(s) older than 7 days."
fi

# Count files
FILE_COUNT=$(find "$INBOX" -maxdepth 1 -type f | wc -l)

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "No files in inbox. Nothing to ingest."
    exit 0
fi

echo "Found $FILE_COUNT file(s) in inbox. Starting ingest..."

SUCCESS=0
FAILED_COUNT=0

for f in "$INBOX"/*; do
    [ -f "$f" ] || continue

    FILENAME=$(basename "$f")
    EXT="${FILENAME##*.}"

    # Handle task files: extract YouTube URLs and ingest each
    if [[ "$FILENAME" == task-*.md ]]; then
        echo "  Processing task: $FILENAME"
        TASK_SUCCESS=0
        TASK_FAILED=0
        while IFS= read -r line; do
            URL=$(echo "$line" | grep -oE 'https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+' | head -1)
            if [ -n "$URL" ]; then
                echo "    Ingesting: $URL"
                if python3 "$TOOL" "$URL" --domain learning --visibility private 2>&1; then
                    TASK_SUCCESS=$((TASK_SUCCESS + 1))
                else
                    TASK_FAILED=$((TASK_FAILED + 1))
                fi
            fi
        done < "$f"
        rm "$f"
        SUCCESS=$((SUCCESS + TASK_SUCCESS))
        FAILED_COUNT=$((FAILED_COUNT + TASK_FAILED))
        echo "  ✓ Task complete: $TASK_SUCCESS ingested, $TASK_FAILED failed"
        continue
    fi
    if [ "$EXT" = "md" ]; then
        echo "  Ingesting: $FILENAME"
        if python3 "$TOOL" "$f" --domain tools --visibility shareable 2>&1; then
            rm "$f"
            SUCCESS=$((SUCCESS + 1))
            echo "  ✓ Ingested $FILENAME"
        else
            echo "  ✗ Failed to ingest $FILENAME"
            mv "$f" "$FAILED/"
            echo "$(date +%Y-%m-%dT%H:%M:%S) $FILENAME ingest-failed" >> "$FAIL_LOG"
            FAILED_COUNT=$((FAILED_COUNT + 1))
        fi
    else
        echo "  ⚠️  Skipping $FILENAME (unsupported type: .$EXT)"
        mv "$f" "$FAILED/"
        echo "$(date +%Y-%m-%dT%H:%M:%S) $FILENAME unsupported-type .$EXT" >> "$FAIL_LOG"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

# Rebuild index if any files were ingested
if [ "$SUCCESS" -gt 0 ]; then
    echo "Rebuilding OKF index..."
    cd "$VAULT" && python3 tools/okf.py index 2>&1 || true
    echo "Relinking..."
    python3 tools/okf.py relink 2>&1 || true
fi

# Commit and push
cd "$VAULT"
git add -A
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
git commit -m "inbox ingest: $SUCCESS ingested, $FAILED_COUNT failed — $TIMESTAMP" 2>&1 || true
git push origin main 2>&1 || echo "⚠️ Push failed"

echo "Done. Success: $SUCCESS, Failed: $FAILED_COUNT"
