#!/bin/bash
tmux kill-session -t ratchet 2>/dev/null && echo "Session stopped" || echo "No session running"
