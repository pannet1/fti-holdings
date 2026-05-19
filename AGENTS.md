# AGENTS.md — Ratchet Holdings

## Project

- **Repo**: fti-holdings (deprecated name, new project: ratchet-holdings concept)
- **Broker**: Finvasia (Shoonya)
- **Bridge**: broker-ai (replaces omspy-brokers / stock-brokers)
- **Strategy**: Ratchet investing — two-book (Holdings + Swing) with Fibonacci sizing

## Troubleshooting Checklist

### Login / Authentication
1. Check `data/<userid>.txt` — is token from today? If stale, delete and retry
2. Verify `bypass.yaml` or config YAML has correct userid/password/TOTP secret
3. Check `data/log.txt` for authentication errors
4. Run `journalctl --user -u ratchet-holdings -f` for service-level errors

### Service Management
- Start: `systemctl --user start ratchet-holdings`
- Stop: `systemctl --user stop ratchet-holdings`
- Restart: `systemctl --user restart ratchet-holdings`
- Status: `systemctl --user status ratchet-holdings`
- Enable linger: `loginctl enable-linger $USER`

### Common Issues
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No orders placed | Strategy not in `data/run.txt` | Remove stale entry or reset run.txt |
| LTP = 0 | WebSocket not subscribed | Check symbol token in factory/symbols.yml |
| Login fails daily | Token file expired | Delete token file, service auto-reauthenticates |
| Drifted positions | Local CSV out of sync with broker | Compare `data/holdings.csv` with broker holdings |
| Strategy crashes | Bad YAML config | Validate `data/*.yml` syntax |

### Logs
- User-visible errors: `data/log.txt`
- System errors: `journalctl --user -u ratchet-holdings`
- Broker API chatter: Set `log_level: INFO` in `settings.yml`

## Code Standards

- **Time library**: `pendulum` only — never `datetime`, `time`, `calendar`
- **Logging**: Use `logging.getLogger(__name__)` via `logging_func` — never `print()`
- **No comments** unless asked
- **No emojis** in text files
- **No secrets** in git-tracked files — use `.env`, YAML outside repo, or secrets manager

## Testing

- Unit tests: `uv run pytest tests/` (local)
- Integration tests: run on server only
- Functional tests: Playwright with `--browser chromium` headless

## Deployment

1. Commit locally: `git add -A && git commit && git push`
2. Pull on server: `git pull`
3. Restart service: `systemctl --user restart ratchet-holdings`
4. Verify: check `data/log.txt` and `journalctl`

## Scripts

All executable scripts live in `scripts/`:
- `scripts/local_*` — local development commands
- `scripts/remote_*` — server deployment/verification commands
- No sensitive info in scripts
