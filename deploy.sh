#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
[[ -d apps/backend ]] || { echo "Run from repo root"; exit 1; }

install() {
    if ! command -v uv &>/dev/null; then
        echo "Installing uv"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    if [[ ! -f .venv/bin/python ]]; then
        uv venv --python 3.10
    fi
    uv sync
}

case "${1:-}" in
    --fix|-f)
        rm -rf .venv 2>/dev/null || true
        install
        ;;
    *) install ;;
esac
