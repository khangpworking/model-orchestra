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
INSTALL_HOOK=0

for arg in "$@"; do
  case "$arg" in
    --hook) INSTALL_HOOK=1 ;;
  esac
done

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

# pre-push hook (opt-in)
if [ $INSTALL_HOOK -eq 1 ]; then
  if [ -d "$TARGET/.git" ]; then
    HOOK_TARGET="$TARGET/.git/hooks/pre-push"
    if [ -e "$HOOK_TARGET" ] && [ ! -L "$HOOK_TARGET" ]; then
      echo "  ⏭  pre-push hook already exists at $HOOK_TARGET — skipping (rename or remove to install)"
    else
      ln -sf "$ROOT/scripts/hooks/pre-push" "$HOOK_TARGET"
      chmod +x "$ROOT/scripts/hooks/pre-push"
      echo "  ✓ pre-push hook symlinked"
    fi
  else
    echo "  ⏭  No .git/ found — skipping hook install (target is not a git repo)"
  fi
fi

echo ""
echo "Done."
echo ""
echo "Next steps:"
echo "  1. Read $TARGET/docs-md/README.md"
echo "  2. Copy docs-md/_feature/ to docs-md/<your-feature>/ for your first feature"
echo "  3. (Optional) Install vbsec for the deep pre-push security scan:"
echo "     git clone https://github.com/tanviet12/vbsec ~/vbsec && ~/vbsec/scripts/install.sh"
if [ $INSTALL_HOOK -eq 0 ]; then
  echo "  4. (Optional) Install the pre-push hook (AI-footprint + secret scan):"
  echo "     $ROOT/scripts/install.sh $TARGET --hook"
fi
echo ""
echo "  Claude Code skills available:"
echo "     /orchestra-plan   — scaffold a new feature design"
echo "     /orchestra-audit  — run the pre-push gate"
echo "     Install them: ln -s $ROOT/skills/claude/* ~/.claude/skills/"
