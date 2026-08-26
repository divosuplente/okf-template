#!/usr/bin/env bash
# bootstrap-aaak-compression.sh — Install the AAAK compression skill universally
#
# Publishes the agent-skill-compression skill + setup.sh into:
#   ${AGENT_SKILLS_DIR:-$HOME/.agent/skills}/agent-skill-compression/
#
# Run from any project that has skills/okf-aaak-compression/ (or pass the source dir).
#
# Usage: bootstrap-aaak-compression.sh [source-skills-dir]
# Default: ./skills/okf-aaak-compression

set -euo pipefail

SOURCE_DIR="${1:-./skills/okf-aaak-compression}"

if [ ! -f "$SOURCE_DIR/SKILL.md" ]; then
  echo "Error: $SOURCE_DIR/SKILL.md not found"
  echo "Run this from a project that contains the okf-aaak-compression skill."
  exit 1
fi

# Target directory (override with AGENT_SKILLS_DIR env var)
TARGET_BASE="${AGENT_SKILLS_DIR:-$HOME/.agent/skills}"
TARGET="$TARGET_BASE/agent-skill-compression"

echo "=== Bootstrap AAAK Compression Skill (Universal) ==="
echo "Source: $(cd "$SOURCE_DIR" && pwd)"
echo "Target: $TARGET"
echo ""

mkdir -p "$TARGET"
cp "$SOURCE_DIR/SKILL.md" "$TARGET/SKILL.md"
if [ -f "$SOURCE_DIR/setup.sh" ]; then
  cp "$SOURCE_DIR/setup.sh" "$TARGET/setup.sh"
  chmod +x "$TARGET/setup.sh"
fi
echo "Installed to $TARGET"

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Your agent can now discover the agent-skill-compression skill."
echo ""
echo "To enable compression in any project:"
echo "  bash $TARGET/setup.sh /path/to/project/skills"
echo ""
echo "Then ask the agent: 'apply AAAK compression to skills/'"
