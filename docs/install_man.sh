#!/usr/bin/env bash
# install_man.sh -- install the pyti_lpc_cmd man page
# Copyright (C) 2026 Kris Kirby, KE4AHR -- Licensed GPLv3.0
#
# Usage:
#   ./install_man.sh          -- install for current user only
#   sudo ./install_man.sh -s  -- install system-wide
#
# User install:   ~/.local/share/man/man1/pyti_lpc_cmd.1
# System install: /usr/local/share/man/man1/pyti_lpc_cmd.1

set -euo pipefail

MANPAGE="$(dirname "$(realpath "$0")")/pyti_lpc_cmd.1"
SYSTEM=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--system) SYSTEM=1 ;;
        -h|--help)
            echo "Usage: $0 [-s|--system]"
            echo "  (no flags)   Install for current user (~/.local/share/man/man1/)"
            echo "  -s, --system Install system-wide (/usr/local/share/man/man1/)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
    shift
done

if [[ ! -f "$MANPAGE" ]]; then
    echo "Error: man page not found at $MANPAGE" >&2
    exit 1
fi

if [[ $SYSTEM -eq 1 ]]; then
    MANDIR="/usr/local/share/man/man1"
    echo "Installing system-wide to $MANDIR (requires write permission)"
else
    MANDIR="${HOME}/.local/share/man/man1"
    echo "Installing for user $(whoami) to $MANDIR"
fi

mkdir -p "$MANDIR"
install -m 0644 "$MANPAGE" "$MANDIR/pyti_lpc_cmd.1"

# Update the man database if mandb or makewhatis is available
if command -v mandb &>/dev/null; then
    if [[ $SYSTEM -eq 1 ]]; then
        mandb -q 2>/dev/null || true
    else
        mandb -q -u 2>/dev/null || true
    fi
elif command -v makewhatis &>/dev/null; then
    makewhatis "$MANDIR" 2>/dev/null || true
fi

echo "Installed: $MANDIR/pyti_lpc_cmd.1"
echo "Test with: man pyti_lpc_cmd"
