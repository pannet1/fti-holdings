#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.cargo/bin:$PATH"
find . -type d -name "__pycache__" -print0 | xargs -0 rm -rf
sess="ratchet"

if tmux has-session -t "$sess" 2>/dev/null; then
	if [ -t 0 ]; then
		echo "Attaching to session $sess."
		tmux attach-session -t "$sess"
	else
		echo "Session $sess already exists."
	fi
else
	echo "Setting up environment"
	if ! hash uv 2>/dev/null; then
		echo "Installing uv"
		curl -LsSf https://astral.sh/uv/install.sh | sh
		hash -r
	fi
	echo "Pulling latest code"
	git pull --ff-only
	if [[ ! -f .venv/bin/python ]]; then
		uv venv --python 3.10
	fi
	echo "Removing stale per-package lockfiles to force fresh resolve..."
	rm -f apps/backend/uv.lock packages/*/uv.lock
	echo "Syncing dependencies..."
	uv sync --directory apps/backend
	if [ -t 0 ]; then
		echo "Creating and attaching to session $sess."
		tmux new-session -s "$sess" -x 120 -y 48 "uv run --directory apps/backend python -m app.main && tmux kill-session -t $sess"
	else
		echo "Creating session $sess."
		tmux new-session -d -s "$sess" -x 120 -y 48
		tmux send-keys -t "$sess" "uv run --directory apps/backend python -m app.main && tmux kill-session -t $sess" C-m
	fi
fi
