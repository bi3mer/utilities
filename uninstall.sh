#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if [ ! -d "$VENV" ]; then
    echo "No venv found at $VENV, nothing to uninstall."
    exit 0
fi

PIP="$VENV/bin/pip"

removed=0
failed=0

for dir in "$ROOT"/*/; do
    [ -f "$dir/pyproject.toml" ] || continue

    name="$(grep '^name' "$dir/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    printf "Uninstalling %s ... " "$name"

    if $PIP uninstall "$name" -y --quiet 2>&1; then
        echo "ok"
        ((removed++))
    else
        echo "FAILED"
        ((failed++))
    fi
done

# Remove PATH entry and comment from shell rc files.
BIN="$VENV/bin"

if grep -qF "$BIN" "$HOME/.bashrc" 2>/dev/null; then
    sed -i.bak "\\|# cmd_tools utilities|d;\\|$BIN|d" "$HOME/.bashrc"
    rm -f "$HOME/.bashrc.bak"
    echo "Removed PATH entry from .bashrc"
fi

echo ""
echo "Done: $removed uninstalled, $failed failed."
echo "Restart your shell or run: source ~/.bashrc"
[ "$failed" -eq 0 ]