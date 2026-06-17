#!/usr/bin/env bash
# Migrate gptaku plugins: setup/star.sh -> setup/setup.sh (unified first-run setup
# that also installs the update-notifier hook), update all Step 0 references, and
# remove the per-plugin SessionStart hooks (we use a single settings.json hook now).
#
# Working-tree only — does NOT commit or push. Re-runnable.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/shared/update-hook"
PLUGINS_DIR="$REPO_ROOT/plugins"
TEMPLATE="$SRC/setup.sh.template"
CJS="$SRC/gptaku-update-check.cjs"

for dir in "$PLUGINS_DIR"/*/; do
  name="$(basename "$dir")"
  [ -f "$dir/.claude-plugin/plugin.json" ] || continue
  star="$dir/setup/star.sh"
  [ -f "$star" ] || { echo "  - $name: no star.sh, skip"; continue; }

  PLUGIN="$(grep -m1 '^PLUGIN=' "$star" | cut -d'"' -f2)"
  OWN_REPO="$(grep -m1 '^OWN_REPO=' "$star" | cut -d'"' -f2)"
  [ -n "$PLUGIN" ] && [ -n "$OWN_REPO" ] || { echo "  ! $name: could not parse vars, skip"; continue; }

  # 1) write setup/setup.sh from template
  sed -e "s|__PLUGIN__|$PLUGIN|g" -e "s|__OWN_REPO__|$OWN_REPO|g" "$TEMPLATE" > "$dir/setup/setup.sh"
  chmod +x "$dir/setup/setup.sh"

  # 2) bundle the check script next to setup.sh
  cp -f "$CJS" "$dir/setup/gptaku-update-check.cjs"

  # 3) drop old star.sh
  trash "$star" 2>/dev/null || true

  # 4) remove the per-plugin SessionStart hooks dir (B-design uses one settings.json hook)
  [ -d "$dir/hooks" ] && { trash "$dir/hooks" 2>/dev/null || true; }

  echo "  ✓ $name (PLUGIN=$PLUGIN OWN_REPO=$OWN_REPO)"
done

# 5) update every Step 0 reference: setup/star.sh -> setup/setup.sh
echo "Updating Step 0 references in .md files..."
grep -rl "setup/star.sh" "$PLUGINS_DIR" --include="*.md" 2>/dev/null | while read -r f; do
  sed -i '' 's#setup/star.sh#setup/setup.sh#g' "$f"
done

echo "Done."
