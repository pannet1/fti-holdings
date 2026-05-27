#!/bin/bash
if tmux has-session -t ratchet 2>/dev/null; then
    echo "Running"
else
    echo "Stopped"
fi
