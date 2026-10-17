#!/usr/bin/env bash
# Install the Codex version of scaffold-skill into the user skills folder.
#   ./install.sh            copy  → ~/.agents/skills/scaffold-skill
#   ./install.sh --link     symlink instead (edits in this repo go live)
# An existing install is moved aside to scaffold-skill.bak-<timestamp>, never deleted.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/codex/scaffold-skill"
DEST_DIR="${SKILLS_DIR:-$HOME/.agents/skills}"
DEST="$DEST_DIR/scaffold-skill"

[ -f "$SRC/SKILL.md" ] || { echo "missing $SRC/SKILL.md" >&2; exit 1; }
mkdir -p "$DEST_DIR"

if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  BAK="$DEST.bak-$(date +%Y%m%d-%H%M%S)"
  mv "$DEST" "$BAK"
  echo "moved existing install → $BAK"
fi

if [ "${1:-}" = "--link" ]; then
  ln -s "$SRC" "$DEST"
  echo "linked $DEST → $SRC"
else
  cp -R "$SRC" "$DEST"
  echo "copied → $DEST"
fi

python3 "$DEST/scripts/scaffold.py" version >/dev/null && echo "ok: scaffold.py $(python3 "$DEST/scripts/scaffold.py" version)"
echo "restart Codex so it picks up the skill"
