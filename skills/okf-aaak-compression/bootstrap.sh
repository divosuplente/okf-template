#!/usr/bin/env bash
# bootstrap-aaak-compression.sh — Install the AAAK compression skill universally
#
# Publishes the agent-skill-compression skill + setup.sh into both:
#   ~/.agents/skills/agent-skill-compression/  (harness/ECC runtime)
#   ~/.omp/agent/managed-skills/agent-skill-compression/  (OMP managed skills)
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

echo "=== Bootstrap AAAK Compression Skill (Universal) ==="
echo "Source: $(cd "$SOURCE_DIR" && pwd)"
echo ""

# Install into ~/.agents/skills/ (harness/ECC runtime)
AGENTS_TARGET="$HOME/.agents/skills/agent-skill-compression"
mkdir -p "$AGENTS_TARGET"
cp "$SOURCE_DIR/SKILL.md" "$AGENTS_TARGET/SKILL.md"
if [ -f "$SOURCE_DIR/setup.sh" ]; then
  cp "$SOURCE_DIR/setup.sh" "$AGENTS_TARGET/setup.sh"
  chmod +x "$AGENTS_TARGET/setup.sh"
fi
echo "✅ Installed to $AGENTS_TARGET"

# Install into ~/.omp/agent/managed-skills/ (OMP managed skills)
OMP_TARGET="$HOME/.omp/agent/managed-skills/agent-skill-compression"
mkdir -p "$OMP_TARGET"
cp "$SOURCE_DIR/SKILL.md" "$OMP_TARGET/SKILL.md"
if [ -f "$SOURCE_DIR/setup.sh" ]; then
  cp "$SOURCE_DIR/setup.sh" "$OMP_TARGET/setup.sh"
  chmod +x "$OMP_TARGET/setup.sh"
fi
echo "✅ Installed to $OMP_TARGET"

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Both runtimes can now discover the agent-skill-compression skill."
echo ""
echo "To enable compression in any project:"
echo "  bash ~/.agents/skills/agent-skill-compression/setup.sh /path/to/project/skills"
echo ""
echo "Then ask the agent: 'apply AAAK compression to skills/'"
