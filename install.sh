#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating venv at $VENV ..."
    python3 -m venv "$VENV"
fi

PIP="$VENV/bin/pip"

installed=0
failed=0

for dir in "$ROOT"/*/; do
    [ -f "$dir/pyproject.toml" ] || continue

    name="$(grep '^name' "$dir/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
    printf "Installing %s ... " "$name"

    if $PIP install -e "$dir" --quiet 2>&1; then
        echo "ok"
        installed=$((installed + 1))
    else
        echo "FAILED"
        failed=$((failed + 1))
    fi
done

# Add venv bin to PATH in shell rc if not already there.
BIN="$VENV/bin"
PATH_LINE="export PATH=\"$BIN:\$PATH\""

if ! grep -qF "$BIN" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# cmd_tools utilities" >> "$HOME/.bashrc"
    echo "$PATH_LINE" >> "$HOME/.bashrc"
    echo "Added PATH entry to .bashrc"
fi

echo ""
echo "Done: $installed installed, $failed failed."
echo "Restart your shell or run: source ~/.bashrc"
[ "$failed" -eq 0 ]