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

    name="$(basename "$dir")"
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

for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc"; do
    [ -f "$rc" ] || continue
    if grep -qF "$BIN" "$rc"; then
        sed -i.bak "\\|# cmd_tools utilities|d;\\|$BIN|d" "$rc"
        rm -f "$rc.bak"
        echo "Removed PATH entry from $(basename "$rc")"
    fi
done

echo ""
echo "Done: $removed uninstalled, $failed failed."
echo "Restart your shell or run: source ~/.bashrc"
[ "$failed" -eq 0 ]