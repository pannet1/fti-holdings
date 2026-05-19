# Deployment Guide

## Prerequisites

- Python 3.10+
- `uv` package manager
- systemd (user instance)
- Finvasia (Shoonya) account with TOTP enabled
- Server access for deployment

## Local Setup

```bash
# Create virtual environment
uv venv --python 3.10
source .venv/bin/activate

# Install dependencies
uv sync

# Configure credentials (outside git)
cp factory/bypass_template.yaml data/bypass.yaml
# Edit data/bypass.yaml with actual credentials

# Configure settings
cp factory/settings_template.yml data/settings.yml
# Edit data/settings.yml with start/stop times

# Initialize state files
touch data/run.txt
```

## Server Deployment

### 1. Pull Code

```bash
cd ~/programs/fti-holdings
git pull
```

### 2. Install Dependencies

```bash
uv sync --frozen
```

### 3. Configure Service

```bash
# Copy service template
cp factory/ratchet-holdings.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Enable linger (survives SSH logout)
loginctl enable-linger $USER
```

### 4. Start Service

```bash
systemctl --user start ratchet-holdings
systemctl --user enable ratchet-holdings
```

### 5. Verify

```bash
# Check service status
systemctl --user status ratchet-holdings

# Check logs
journalctl --user -u ratchet-holdings -f

# Check application logs
tail -f data/log.txt
```

## Service Template

```ini
# factory/ratchet-holdings.service
[Unit]
Description=Ratchet Holdings Trading Strategy
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/programs/fti-holdings
ExecStart=%h/.local/bin/uv run python -m rachet_investing.main
Restart=on-failure
RestartSec=30
StandardOutput=append:%h/programs/fti-holdings/data/log.txt
StandardError=journal

[Install]
WantedBy=default.target
```

## Scripts

### Local Development

```bash
# scripts/local_run.sh
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
uv run python -m rachet_investing.main
```

### Remote Verification

```bash
# scripts/remote_status.sh
#!/bin/bash
systemctl --user status ratchet-holdings
echo "---"
tail -20 ~/programs/fti-holdings/data/log.txt
```

## Troubleshooting

### Service Won't Start

```bash
# Check journal logs
journalctl --user -u ratchet-holdings --no-pager -n 50

# Test manually
uv run python -m rachet_investing.main
```

### Authentication Fails

```bash
# Delete stale token
rm data/<userid>.txt

# Restart service
systemctl --user restart ratchet-holdings
```

### No Orders Placed

```bash
# Check run state
cat data/run.txt

# Reset run state
> data/run.txt

# Restart
systemctl --user restart ratchet-holdings
```

### Position Drift

```bash
# Compare local vs broker
uv run python scripts/remote_sync_check.py
```
