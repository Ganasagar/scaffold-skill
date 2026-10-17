#!/usr/bin/env bash
# Default: ./install.sh --project /absolute/project/root [--dry-run]
# User-wide: ./install.sh --scope user [--dry-run]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/codex/scaffold-skill/scripts/install_skill.py" "$@"
