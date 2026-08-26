#!/usr/bin/env bash
# setup-aaak-compression.sh — Enable AAAK skill compression in any project
#
# Usage: setup-aaak-compression.sh [path/to/skills/dir]
# Default: ./skills
#
# What it does:
# 1. For each skill subdirectory, copies SKILL.md → SKILL.full.md (verbatim backup)
# 2. Adds an AGENTS.md section documenting the dual-layer system
#
# The agent then compresses SKILL.md using the agent-skill-compression managed skill.
# Run this script FIRST, then ask the agent to "apply AAAK compression to skills/".
#
# Prerequisites:
# - The agent-skill-compression managed skill must be available (it's in ${AGENT_SKILLS_DIR:-$HOME/.agent/skills}/)
# - The agent session must have access to the project's AGENTS.md

set -euo pipefail

SKILLS_DIR="${1:-./skills}"

if [ ! -d "$SKILLS_DIR" ]; then
  echo "Error: $SKILLS_DIR does not exist"
  exit 1
fi

# Derive project root from SKILLS_DIR (parent of the skills/ dir)
SKILLS_DIR_ABS="$(cd "$SKILLS_DIR" && pwd)"
PROJECT_ROOT="$(dirname "$SKILLS_DIR_ABS")"

echo "=== AAAK Skill Compression Setup ==="
echo "Target: $SKILLS_DIR"
echo ""

# Step 1: Copy each SKILL.md to SKILL.full.md
COUNT=0
for skill_dir in "$SKILLS_DIR"/*/; do
  [ -d "$skill_dir" ] || continue
  skill_md="${skill_dir}SKILL.md"
  full_md="${skill_dir}SKILL.full.md"
  
  if [ ! -f "$skill_md" ]; then
    continue
  fi
  
  if [ -f "$full_md" ]; then
    echo "  SKIP $(basename "$skill_dir") — SKILL.full.md already exists"
    continue
  fi
  
  cp "$skill_md" "$full_md"
  echo "  ✅ $(basename "$skill_dir") — SKILL.full.md created ($(wc -c < "$full_md") bytes)"
  COUNT=$((COUNT + 1))
done

echo ""
echo "Verbatim backups created: $COUNT"
echo ""

# Step 2: Add AGENTS.md section (if not already present)
# Step 2: Add AGENTS.md section in PROJECT_ROOT (not CWD)
AGENTS_FILE=""
for candidate in "$PROJECT_ROOT/AGENTS.md" "$PROJECT_ROOT/CLAUDE.md" "$PROJECT_ROOT/.cursorrules"; do
  if [ -f "$candidate" ]; then
    AGENTS_FILE="$candidate"
    break
  fi
done

if [ -z "$AGENTS_FILE" ]; then
  AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"
  echo "No AGENTS.md found in $PROJECT_ROOT. Created new one."
  touch "$AGENTS_FILE"
fi

if grep -q "SKILL.full.md" "$AGENTS_FILE" 2>/dev/null; then
  echo "AGENTS.md already has compression section — skipping."
else
  cat >> "$AGENTS_FILE" << 'SECTION'

## Skill Compression (AAAK)
- Every `skills/` directory has two files: `SKILL.md` (compressed agent view using AAAK syntax) and `SKILL.full.md` (verbatim source of truth).
- The `SKILL.md` file is a **lossy** agent overlay — the `SKILL.full.md` file preserves the lossless original.
- Frontmatter (`name`, `description`) in `SKILL.md` MUST match `SKILL.full.md` exactly for skill routing to work.
- When editing or creating skills, apply AAAK compression: see the `agent-skill-compression` managed skill for format rules.
- The compression uses MemPalace's AAAK dialect syntax: section prefixes, pipe-separated concepts, hyphenated words, article-dropping, and a DICT glossary line.
SECTION
  echo "✅ Added Skill Compression section to $AGENTS_FILE"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Ask the agent: 'apply AAAK compression to $SKILLS_DIR'"
echo "  2. The agent will read each SKILL.full.md and write compressed SKILL.md"
echo "  3. Verify: frontmatter matches, YAML blocks valid, semantic content preserved"
echo ""
echo "Managed skill location: ${AGENT_SKILLS_DIR:-$HOME/.agent/skills}/agent-skill-compression/SKILL.md"
