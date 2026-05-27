#!/usr/bin/env bash
set -euo pipefail

REQUIRED_PYTHON="3.10"
SERVICE_NAME="ratchet-holdings"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTION]

Deploy or repair the Ratchet Holdings trading bot.
Run from the repo root after cloning.

Options:
  --install       Install deps, scaffold config, set up service
  --fix           Detect and repair broken install
  --status        Check health of current install
  --help          Show this message
EOF
    exit 0
}

# ── helpers ──────────────────────────────────────────

ensure_uv() {
    if ! command -v uv &>/dev/null; then
        info "Installing uv"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
}

ensure_venv() {
    if [[ ! -f .venv/bin/python ]]; then
        info "Creating virtual environment (Python $REQUIRED_PYTHON)"
        uv venv --python "$REQUIRED_PYTHON"
    fi
}

sync_deps() {
    info "Installing dependencies (uv sync)"
    local attempt=1
    while true; do
        if uv sync --frozen 2>/dev/null; then
            break
        fi
        if [[ $attempt -ge 3 ]]; then
            info "Frozen sync failed, trying full sync"
            uv sync || { fail "uv sync failed"; return 1; }
            break
        fi
        info "Retrying (attempt $attempt)"; attempt=$((attempt + 1)); sleep 2
    done
    pass "Dependencies installed"
}

scaffold_config() {
    local factory="apps/backend/factory"
    [[ -d "$factory" ]] || { fail "Factory dir $factory not found"; return 1; }
    mkdir -p data
    for f in settings.yml auth.yaml; do
        if [[ ! -f "data/$f" ]]; then
            [[ -f "$factory/$f" ]] || { fail "Template $factory/$f missing"; continue; }
            cp "$factory/$f" "data/$f"
            info "Created data/$f — edit with real values"
        fi
    done
    if ! ls data/ratchet*.yml &>/dev/null 2>&1; then
        info "No strategy config in data/ — copy one from factory/ or create manually"
    fi
    chmod 600 data/auth.yaml 2>/dev/null || true
}

init_state() {
    for f in run.txt; do
        [[ -f "data/$f" ]] || { touch "data/$f"; info "Created data/$f"; }
    done
}

install_service() {
    local unit="$HOME/.config/systemd/user/$SERVICE_NAME.service"
    mkdir -p "$(dirname "$unit")"
    cat > "$unit" << EOF
[Unit]
Description=Ratchet Holdings Trading Strategy
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/python -m app.main
Restart=on-failure
RestartSec=30
StandardOutput=append:$(pwd)/data/log.txt
StandardError=journal

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME" 2>/dev/null || true
    loginctl enable-linger "$USER" 2>/dev/null || true
    pass "systemd service installed & enabled"
}

# ── checks ────────────────────────────────────────────

check_python() {
    local py=".venv/bin/python"
    [[ -f "$py" ]] || { fail "No venv python at $py"; return 1; }
    local ver
    ver=$("$py" --version 2>&1 | grep -oP '\d+\.\d+')
    if [[ "$ver" != "$REQUIRED_PYTHON" ]]; then
        fail "Python $REQUIRED_PYTHON required, venv has $ver"
        return 1
    fi
    pass "Python $ver"
}

check_uv() {
    command -v uv &>/dev/null || { fail "uv not found"; return 1; }
    pass "uv ok"
}

check_deps() {
    .venv/bin/python -c "import yaml, pendulum, pydantic, broker_ai" 2>/dev/null \
        && pass "Dependencies installed" \
        || { fail "Dependencies broken"; return 1; }
}

check_config() {
    local rc=0
    for f in data/settings.yml data/auth.yaml; do
        [[ -f "$f" ]] && pass "$f" || { fail "$f missing"; rc=1; }
    done
    if [[ -f data/auth.yaml ]] && grep -q 'userid: ""' data/auth.yaml 2>/dev/null; then
        fail "auth.yaml has empty fields — edit with real credentials"
        rc=1
    fi
    return $rc
}

check_state() {
    local rc=0
    for f in data/run.txt; do
        [[ -f "$f" ]] || { fail "$f missing"; rc=1; }
    done
    [[ $rc -eq 0 ]] && pass "State files present"
    return $rc
}

check_service_installed() {
    systemctl --user --all list-units --full 2>/dev/null | grep -q "$SERVICE_NAME" \
        && pass "Service installed" \
        || { fail "Service not installed"; return 1; }
}

check_service_running() {
    local s
    s=$(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
    if [[ "$s" == "active" ]]; then
        pass "Service is running"
    elif [[ "$s" == "activating" ]]; then
        info "Service is starting up (may need credentials)"
    else
        fail "Service is $s"; return 1
    fi
}

# ── commands ──────────────────────────────────────────

cmd_install() {
    echo "═══ Install ═══"
    ensure_uv
    ensure_venv
    sync_deps
    scaffold_config
    init_state
    install_service
    echo ""
    info "Done. Next:"
    info "  1. Edit data/auth.yaml with Finvasia credentials"
    info "  2. Ensure a strategy .yml exists in data/"
    info "  3. Run: systemctl --user start $SERVICE_NAME"
}

cmd_fix() {
    echo "═══ Fix ═══"
    local rc=0
    ensure_uv
    ensure_venv
    check_python || rc=1
    check_deps || { sync_deps || rc=1; }
    scaffold_config
    init_state
    check_config || rc=1
    check_state || rc=1
    if ! check_service_installed; then
        install_service
        check_service_installed || rc=1
    fi
    check_service_running || {
        info "Starting service"
        systemctl --user restart "$SERVICE_NAME" 2>/dev/null || true
        for i in 1 2 3; do
            sleep 1
            check_service_running && { rc=0; break; } || true
        done
    }
    local tok
    tok=$(ls data/*.txt 2>/dev/null | grep -v run.txt | head -1 || true)
    [[ -n "$tok" ]] && info "Stale token $(basename "$tok") — will regenerate on auth"
    echo ""
    [[ $rc -eq 0 ]] && pass "All good" || fail "Issues found"
}

cmd_status() {
    echo "═══ Status ═══"
    check_python || true
    check_uv || true
    check_deps || true
    check_config || true
    check_state || true
    check_service_installed || true
    check_service_running || true
    echo ""
    info "Log tail:"
    tail -5 data/log.txt 2>/dev/null || echo "(no log)"
    echo ""
    info "Live logs: journalctl --user -u $SERVICE_NAME -f"
}

# ── main ──────────────────────────────────────────────

cd "$(dirname "$0")"
[[ -d apps/backend ]] || { fail "Run from repo root"; exit 1; }

case "${1:-}" in
    --install|-i) cmd_install ;;
    --fix|-f)     cmd_fix ;;
    --status|-s)  cmd_status ;;
    --help|-h)    usage ;;
    *)            usage ;;
esac
