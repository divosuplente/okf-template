#!/usr/bin/env bash
# OMP Vault Setup — install global extensions and managed skills from bundled copies
# Run once after cloning this vault on a new machine.
set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOOTSTRAP="$VAULT_ROOT/.omp/bootstrap"
OMP_HOME="${OMP_HOME:-$HOME/.omp/agent}"

echo "=== OMP Vault Setup ==="
echo "Vault: $VAULT_ROOT"
echo "OMP home: $OMP_HOME"
echo ""

# 1. Install global extensions
echo "--- Global extensions ---"
mkdir -p "$OMP_HOME/extensions"
for f in "$BOOTSTRAP/extensions/"*.ts; do
  [ -f "$f" ] || continue
  name=$(basename "$f")
  dest="$OMP_HOME/extensions/$name"
  if [ -f "$dest" ]; then
    echo "  SKIP (exists): $name"
  else
    cp "$f" "$dest"
    echo "  INSTALLED: $name"
  fi
done

# 2. Install managed skills
echo ""
echo "--- Managed skills ---"
if [ -d "$BOOTSTRAP/managed-skills" ]; then
  for skill_dir in "$BOOTSTRAP/managed-skills"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    dest="$OMP_HOME/managed-skills/$skill_name"
    if [ -d "$dest" ]; then
      echo "  SKIP (exists): $skill_name"
    else
      cp -r "$skill_dir" "$dest"
      echo "  INSTALLED: $skill_name"
    fi
  done
fi

# 3. Verify local extensions (should already be in repo via git)
echo ""
echo "--- Local extensions ---"
LOCAL_EXT="$VAULT_ROOT/.omp/extensions"
if [ -d "$LOCAL_EXT" ]; then
  count=$(find "$LOCAL_EXT" -name "*.js" -maxdepth 1 | wc -l | tr -d ' ')
  echo "  $count local extensions in .omp/extensions/"
else
  echo "  WARNING: .omp/extensions/ not found — creating from bootstrap"
  mkdir -p "$LOCAL_EXT"
  for f in "$BOOTSTRAP/extensions/"*.js; do
    [ -f "$f" ] || continue
    cp "$f" "$LOCAL_EXT/"
    echo "  COPIED: $(basename "$f")"
  done
fi

echo ""
echo "=== Setup complete ==="
echo "Restart OMP for extension changes to take effect."
