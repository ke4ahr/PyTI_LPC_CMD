#!/usr/bin/env bash
# build_pdf.sh — compile pyti_lpc_cmd_paper.tex to PDF using LuaLaTeX
# Copyright (C) 2026 Kris Kirby, KE4AHR — Licensed GPLv3.0
#
# Usage:  ./build_pdf.sh [--clean]
#   --clean   remove auxiliary files after a successful build

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TEX_SRC="pyti_lpc_cmd_paper.tex"
JOB_NAME="pyti_lpc_cmd_paper"

AUX_EXTS=(aux bbl bcf blg log out run.xml toc lof lot fls fdb_latexmk synctex.gz)

usage() {
    echo "Usage: $0 [--clean]"
    echo "  Compile ${TEX_SRC} → ${JOB_NAME}.pdf using LuaLaTeX + Biber."
    echo "  --clean   remove auxiliary files after a successful build"
    exit 1
}

CLEAN=0
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN=1 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $arg"; usage ;;
    esac
done

if ! command -v lualatex &>/dev/null; then
    echo "Error: lualatex not found. Install TeX Live or MiKTeX." >&2
    exit 1
fi
if ! command -v biber &>/dev/null; then
    echo "Error: biber not found. Install TeX Live (biber package) or MiKTeX." >&2
    exit 1
fi

echo "==> Pass 1: lualatex ${TEX_SRC}"
lualatex --interaction=nonstopmode --jobname="${JOB_NAME}" "${TEX_SRC}"

echo "==> Biber: process bibliography"
biber "${JOB_NAME}"

echo "==> Pass 2: lualatex ${TEX_SRC}  (resolve citations)"
lualatex --interaction=nonstopmode --jobname="${JOB_NAME}" "${TEX_SRC}"

echo "==> Pass 3: lualatex ${TEX_SRC}  (resolve cross-references)"
lualatex --interaction=nonstopmode --jobname="${JOB_NAME}" "${TEX_SRC}"

echo "==> Output: ${SCRIPT_DIR}/${JOB_NAME}.pdf"

if [[ "$CLEAN" -eq 1 ]]; then
    echo "==> Cleaning auxiliary files..."
    for ext in "${AUX_EXTS[@]}"; do
        rm -f "${JOB_NAME}.${ext}"
    done
fi

echo "==> Done."
