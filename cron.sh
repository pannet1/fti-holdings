#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

if [[ "${1:-}" == "--install" ]]; then
    CRON_LINE="15 9 * * 1-5 $SCRIPT_DIR/cron.sh"
    (crontab -l 2>/dev/null | grep -v "$SCRIPT_DIR/cron.sh"; echo "$CRON_LINE") | crontab -
    echo "Installed: $CRON_LINE"
    exit 0
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/tmux-$(date +\%Y\%m\%d).log"
export PATH="$HOME/.cargo/bin:$PATH"
cd "$SCRIPT_DIR"
echo "=== $(date) ===" >> "$LOG_FILE"
bash "$SCRIPT_DIR/tmux.sh" >> "$LOG_FILE" 2>&1
echo "Exit code: $?" >> "$LOG_FILE"
