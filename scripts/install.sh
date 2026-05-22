#!/usr/bin/env bash
# install.sh — drops model-orchestra templates into a target project.
#
# Usage:
#   ./install.sh                  # install into current directory
#   ./install.sh /path/to/project
#
# What it does:
#   - Copies templates/docs-md/ → <target>/docs-md/ (skips if exists)
#   - Copies templates/.ai/ → <target>/.ai/ (skips if exists)
#   - Appends templates/gitignore.append → <target>/.gitignore
#   - Prints next-step suggestions

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$(pwd)}"

if [ ! -d "$TARGET" ]; then
  echo "Target dir does not exist: $TARGET" >&2
  exit 1
fi

echo "→ Installing model-orchestra into $TARGET"
echo ""

# docs-md
if [ -d "$TARGET/docs-md" ]; then
  echo "  ⏭  docs-md/ already exists — skipping"
else
  cp -r "$ROOT/templates/docs-md" "$TARGET/docs-md"
  echo "  ✓ docs-md/ scaffolded"
fi

# .ai
if [ -d "$TARGET/.ai" ]; then
  echo "  ⏭  .ai/ already exists — skipping"
else
  cp -r "$ROOT/templates/.ai" "$TARGET/.ai"
  echo "  ✓ .ai/ scaffolded"
fi

# .gitignore
if [ -f "$TARGET/.gitignore" ]; then
  if ! grep -qF "model-orchestra" "$TARGET/.gitignore"; then
    {
      echo ""
      cat "$ROOT/templates/gitignore.append"
    } >> "$TARGET/.gitignore"
    echo "  ✓ .gitignore appended"
  else
    echo "  ⏭  .gitignore already has model-orchestra entries"
  fi
else
  cp "$ROOT/templates/gitignore.append" "$TARGET/.gitignore"
  echo "  ✓ .gitignore created"
fi

echo ""
echo "Done."
echo ""
echo "Next steps:"
echo "  1. Read $TARGET/docs-md/README.md"
echo "  2. Copy docs-md/_feature/ to docs-md/<your-feature>/ for your first feature"
echo "  3. (Optional) Install vbsec for the pre-push security gate:"
echo "     git clone https://github.com/tanviet12/vbsec ~/vbsec && ~/vbsec/scripts/install.sh"
echo "  4. (Phase 2) Pre-push hook coming — for now run /vbs-scan-security manually"
