#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating venv at $VENV ..."
    python3 -m venv "$VENV"
fi

PIP="$VENV/bin/pip"
BIN="$VENV/bin"

installed=0
failed=0

for dir in "$ROOT"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"

    if [ -f "$dir/pyproject.toml" ]; then
        pkg="$(grep '^name' "$dir/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
        printf "Installing %s (python) ... " "$pkg"
        if $PIP install -e "$dir" --quiet 2>&1; then
            echo "ok"
            installed=$((installed + 1))
        else
            echo "FAILED"
            failed=$((failed + 1))
        fi

    elif [ -f "$dir/Makefile" ]; then
        printf "Installing %s (make) ... " "$name"
        if make -C "$dir" --quiet 2>&1; then
            # Symlink every executable in the project's bin/ into the venv bin.
            # Fallback: if no bin/, symlink the binary named after the directory.
            if [ -d "$dir/bin" ]; then
                for bin in "$dir/bin/"*; do
                    [ -x "$bin" ] && ln -sf "$(realpath "$bin")" "$BIN/"
                done
            elif [ -x "$dir/$name" ]; then
                ln -sf "$(realpath "$dir/$name")" "$BIN/"
            fi
            echo "ok"
            installed=$((installed + 1))
        else
            echo "FAILED"
            failed=$((failed + 1))
        fi
    fi
done

# Add venv bin to PATH in .bashrc if not already there.
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