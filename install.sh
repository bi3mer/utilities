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

    name="$(basename "$dir")"
    printf "Installing %s ... " "$name"

    if $PIP install -e "$dir" --quiet 2>&1; then
        echo "ok"
        ((installed++))
    else
        echo "FAILED"
        ((failed++))
    fi
done

# Add venv bin to PATH in shell rc if not already there.
BIN="$VENV/bin"
PATH_LINE="export PATH=\"$BIN:\$PATH\""

for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc"; do
    [ -f "$rc" ] || continue
    if ! grep -qF "$BIN" "$rc"; then
        echo "" >> "$rc"
        echo "# cmd_tools utilities" >> "$rc"
        echo "$PATH_LINE" >> "$rc"
        echo "Added PATH entry to $(basename "$rc")"
    fi
done

echo ""
echo "Done: $installed installed, $failed failed."
echo "Restart your shell or run: source ~/.bashrc"
[ "$failed" -eq 0 ]