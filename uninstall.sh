#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if [ ! -d "$VENV" ]; then
    echo "No venv found at $VENV, nothing to uninstall."
    exit 0
fi

PIP="$VENV/bin/pip"
BIN="$VENV/bin"

removed=0
failed=0

for dir in "$ROOT"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"

    if [ -f "$dir/pyproject.toml" ]; then
        pkg="$(grep '^name' "$dir/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
        printf "Uninstalling %s (python) ... " "$pkg"
        if $PIP uninstall "$pkg" -y --quiet 2>&1; then
            echo "ok"
            removed=$((removed + 1))
        else
            echo "FAILED"
            failed=$((failed + 1))
        fi

    elif [ -f "$dir/Makefile" ]; then
        printf "Uninstalling %s (make) ... " "$name"
        # Remove symlinks from venv bin that point into this project.
        for link in "$BIN"/*; do
            [ -L "$link" ] || continue
            target="$(realpath "$link" 2>/dev/null || true)"
            case "$target" in "$dir"*)
                rm -f "$link"
                ;;
            esac
        done
        # Run make clean if available.
        make -C "$dir" clean --quiet 2>/dev/null || true
        echo "ok"
        removed=$((removed + 1))
    fi
done

# Remove PATH entry from .bashrc.
if grep -qF "$BIN" "$HOME/.bashrc" 2>/dev/null; then
    sed -i.bak "\\|# cmd_tools utilities|d;\\|$BIN|d" "$HOME/.bashrc"
    rm -f "$HOME/.bashrc.bak"
    echo "Removed PATH entry from .bashrc"
fi

echo ""
echo "Done: $removed uninstalled, $failed failed."
echo "Restart your shell or run: source ~/.bashrc"
[ "$failed" -eq 0 ]