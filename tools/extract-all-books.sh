#!/usr/bin/bash
# Extract all four physics books with separate workdirs to avoid temp dir collision
set -e
PYTHON=".venv/bin/python3"
EXTRACT="tools/book-to-skill/scripts/extract.py"
SLICE_BASE="books/slices"
OUT_BASE="plans/book-skills"

run_extract() {
    slug="$1"
    workdir="$(mktemp -d)"
    echo "=== Extracting $slug → workdir $workdir ==="
    BOOK_SKILL_WORKDIR="$workdir" "$PYTHON" "$EXTRACT" "$SLICE_BASE/$slug" --mode text --install-missing no
    mkdir -p "$OUT_BASE/$slug"
    cp "$workdir/full_text.txt" "$workdir/metadata.json" "$OUT_BASE/$slug/"
    echo "  full_text.txt: $(wc -c < "$OUT_BASE/$slug/full_text.txt") bytes"
    echo "  metadata.json: $(wc -c < "$OUT_BASE/$slug/metadata.json") bytes"
    rm -rf "$workdir"
}

run_extract "rafelski-modern-special-relativity"
run_extract "daiber-special-algebra-relativity"
run_extract "wolfson-relativity-quantum"
run_extract "weinberg-foundations-modern-physics"

echo "All done."
