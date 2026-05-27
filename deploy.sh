#!/usr/bin/env bash
set -euo pipefail

REQUIRED_PYTHON="3.10"
REPO_URL="git@github.com:pannet1/fti-holdings.git"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="ratchet-holdings"
SERVICE_DIR="$HOME/.config/systemd/user"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTION]

Deploy or repair the Ratchet Holdings trading bot.

Options:
  --install       Fresh install (clone repo, install deps, configure)
  --fix           Detect and repair broken install
  --status        Check health of current install
  --help          Show this message

If no option is given, runs install + fix in sequence.
EOF
    exit 0
}

# ── Health checks ──────────────────────────────────────────────

check_python() {
    local py
    if [[ -f "$REPO_DIR/.venv/bin/python" ]]; then
        py="$REPO_DIR/.venv/bin/python"
    elif command -v python3 &>/dev/null; then
        py="python3"
    else
        fail "python3 not found. Install Python $REQUIRED_PYTHON."
        return 1
    fi
    local ver
    ver=$("$py" --version 2>&1 | grep -oP '\d+\.\d+')
    if [[ "$ver" != "$REQUIRED_PYTHON" ]]; then
        fail "Python $REQUIRED_PYTHON required, venv has $ver. Run: uv python pin $REQUIRED_PYTHON && uv venv"
        return 1
    fi
    pass "Python $ver"
}

check_uv() {
    if ! command -v uv &>/dev/null; then
        fail "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
    pass "uv $(uv --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo 'ok')"
}

check_repo() {
    if [[ ! -d "$REPO_DIR/.git" ]]; then
        fail "Repository not found at $REPO_DIR"
        return 1
    fi
    pass "Repository at $REPO_DIR"
}

check_venv() {
    if [[ ! -f "$REPO_DIR/.venv/bin/python" ]]; then
        fail "Virtual environment missing at $REPO_DIR/.venv"
        return 1
    fi
    pass "Virtual environment"
}

check_deps() {
    if [[ ! -f "$REPO_DIR/.venv/bin/python" ]]; then
        return 1
    fi
    if ! "$REPO_DIR/.venv/bin/python" -c "import yaml, pendulum, pydantic, broker_ai" 2>/dev/null; then
        fail "Dependencies not installed or broken"
        return 1
    fi
    pass "Dependencies installed"
}

check_config() {
    local missing=0
    for f in settings.yml auth.yaml; do
        if [[ ! -f "$REPO_DIR/data/$f" ]]; then
            fail "Config file missing: data/$f"
            missing=1
        else
            pass "Config file: data/$f"
        fi
    done
    # check auth fields are filled (not empty)
    if [[ -f "$REPO_DIR/data/auth.yaml" ]]; then
        if grep -q 'userid: ""' "$REPO_DIR/data/auth.yaml" 2>/dev/null; then
            fail "auth.yaml still has empty fields — edit data/auth.yaml with real credentials"
        else
            pass "auth.yaml populated"
        fi
    fi
    return $missing
}

check_state_files() {
    local missing=0
    for f in run.txt holdings.csv trades.csv; do
        if [[ ! -f "$REPO_DIR/data/$f" ]]; then
            fail "State file missing: data/$f"
            missing=1
        fi
    done
    [[ $missing -eq 0 ]] && pass "State files present"
    return $missing
}

check_strategy_config() {
    local count
    count=$(find "$REPO_DIR/data" -maxdepth 1 -name 'ratchet*.yml' 2>/dev/null | wc -l)
    if [[ $count -eq 0 ]]; then
        fail "No strategy config (*.yml) found in data/"
        return 1
    fi
    pass "Strategy config found ($count file(s))"
}

check_systemd_service() {
    if ! systemctl --user --all list-units --full 2>/dev/null | grep -q "$SERVICE_NAME"; then
        fail "systemd service $SERVICE_NAME not found"
        return 1
    fi
    pass "systemd service $SERVICE_NAME installed"
}

check_service_running() {
    local status
    status=$(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
    if [[ "$status" != "active" ]]; then
        fail "Service $SERVICE_NAME is $status"
        return 1
    fi
    pass "Service $SERVICE_NAME is running"
}

check_stale_token() {
    local token_file
    token_file=$(ls "$REPO_DIR/data/"*.txt 2>/dev/null | head -1 || true)
    if [[ -n "$token_file" && "$token_file" != "$REPO_DIR/data/run.txt" ]]; then
        info "Stale token file found: $(basename "$token_file") (will be regenerated on next auth)"
    fi
}

# ── Actions ────────────────────────────────────────────────────

action_clone() {
    if [[ -d "$REPO_DIR/.git" ]]; then
        info "Repository already exists at $REPO_DIR — pulling latest"
        git -C "$REPO_DIR" pull
    else
        info "Cloning repository into $REPO_DIR"
        mkdir -p "$(dirname "$REPO_DIR")"
        git clone "$REPO_URL" "$REPO_DIR"
    fi
}

action_install_python() {
    if ! command -v python3 &>/dev/null; then
        fail "python3 not found. Install Python $REQUIRED_PYTHON first."
        exit 1
    fi
    local ver
    ver=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    if [[ "$ver" != "$REQUIRED_PYTHON" ]]; then
        info "Python $ver found, pinning $REQUIRED_PYTHON via uv"
        uv python pin "$REQUIRED_PYTHON" 2>/dev/null || true
    fi
}

action_install_uv() {
    if ! command -v uv &>/dev/null; then
        info "Installing uv"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # shellcheck disable=SC1091
        source "$HOME/.cargo/env" 2>/dev/null || true
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
}

action_sync_deps() {
    info "Installing dependencies (uv sync)"
    cd "$REPO_DIR"
    # retry git deps (broker-ai, toolkit) up to 3 times
    local attempt=1
    while true; do
        if uv sync --frozen 2>/dev/null; then
            break
        fi
        if [[ $attempt -ge 3 ]]; then
            info "Frozen sync failed, trying full sync (may update lockfile)"
            uv sync || {
                fail "uv sync failed after $attempt attempts"
                return 1
            }
            break
        fi
        info "Retrying uv sync (attempt $attempt)"
        attempt=$((attempt + 1))
        sleep 2
    done
    pass "Dependencies synced"
}

action_scaffold_config() {
    local copied=0
    local factory
    factory=$(ls -d "$REPO_DIR/apps/backend/factory" "$REPO_DIR/factory" 2>/dev/null | head -1)
    if [[ -z "$factory" ]]; then
        fail "Factory directory not found"
        return 1
    fi
    mkdir -p "$REPO_DIR/data"
    for f in settings.yml auth.yaml; do
        if [[ ! -f "$REPO_DIR/data/$f" ]]; then
            if [[ -f "$factory/$f" ]]; then
                cp "$factory/$f" "$REPO_DIR/data/$f"
                info "Created data/$f from factory template — edit with real values"
                copied=1
            else
                fail "Template not found: $factory/$f"
            fi
        fi
    done
    # copy strategy config if none exists
    if ! ls "$REPO_DIR/data/"ratchet*.yml &>/dev/null; then
        if [[ -f "$factory/ratchet_itbees.yml" ]]; then
            cp "$factory/ratchet_itbees.yml" "$REPO_DIR/data/"
            info "Created strategy config from factory template"
        fi
    fi
    return $copied
}

action_init_state() {
    for f in run.txt; do
        if [[ ! -f "$REPO_DIR/data/$f" ]]; then
            touch "$REPO_DIR/data/$f"
            info "Created data/$f"
        fi
    done
}

action_install_service() {
    mkdir -p "$SERVICE_DIR"
    local service_file="$SERVICE_DIR/$SERVICE_NAME.service"
    cat > "$service_file" << 'SERVICEEOF'
[Unit]
Description=Ratchet Holdings Trading Strategy
After=network.target

[Service]
Type=simple
WorkingDirectory=${REPO_DIR}
ExecStart=${REPO_DIR}/.venv/bin/python -m app.main
Restart=on-failure
RestartSec=30
StandardOutput=append:${REPO_DIR}/data/log.txt
StandardError=journal

[Install]
WantedBy=default.target
SERVICEEOF
    info "systemd service written to $service_file"
    systemctl --user daemon-reload
    pass "systemd service installed"
}

action_enable_service() {
    systemctl --user enable "$SERVICE_NAME" 2>/dev/null || true
    loginctl enable-linger "$USER" 2>/dev/null || true
    pass "Service enabled (linger on)"
}

action_start_service() {
    systemctl --user restart "$SERVICE_NAME" 2>/dev/null || systemctl --user start "$SERVICE_NAME"
    pass "Service started"
}

action_fix_permissions() {
    chmod 600 "$REPO_DIR/data/auth.yaml" 2>/dev/null || true
}

# ── Modes ───────────────────────────────────────────────────────

do_install() {
    echo ""
    echo "═══ Ratchet Holdings — Install ═══"
    echo ""

    action_install_uv
    action_clone
    cd "$REPO_DIR"
    action_install_python
    action_sync_deps
    action_scaffold_config
    action_init_state
    action_fix_permissions
    action_install_service
    action_enable_service

    echo ""
    info "Install complete. Next steps:"
    info "  1. Edit $REPO_DIR/data/auth.yaml with your Finvasia credentials"
    if [[ ! -f "$REPO_DIR/data/ratchet_itbees.yml" ]]; then
        info "  2. Create a strategy config in $REPO_DIR/data/ (see factory/ for template)"
    fi
    info "  3. Run: $(basename "$0") --fix  (to verify everything)"
    echo ""
}

do_fix() {
    echo ""
    echo "═══ Ratchet Holdings — Fix Mode ═══"
    echo ""

    local exit_code=0

    check_uv || exit_code=1
    check_python || exit_code=1
    check_repo || { action_clone; }

    cd "$REPO_DIR"

    check_venv || {
        info "Recreating virtual environment"
        uv venv --python "$REQUIRED_PYTHON"
    }
    check_deps || {
        action_sync_deps || exit_code=1
    }

    action_scaffold_config || exit_code=1
    action_init_state
    action_fix_permissions
    check_config || exit_code=1
    check_strategy_config || exit_code=1
    check_state_files || exit_code=1

    # systemd
    if ! systemctl --user --all list-units --full 2>/dev/null | grep -q "$SERVICE_NAME"; then
        info "Reinstalling systemd service"
        action_install_service
        action_enable_service
    else
        check_systemd_service || exit_code=1
    fi

    check_stale_token
    check_service_running || {
        info "Attempting to start service"
        action_start_service || exit_code=1
    }

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        pass "All checks passed. Deploy is healthy."
    else
        fail "Some checks failed. Review the messages above."
    fi
    echo ""
    return $exit_code
}

do_status() {
    echo ""
    echo "═══ Ratchet Holdings — Status ═══"
    echo ""

    check_python || true
    check_uv || true
    check_repo || true

    cd "$REPO_DIR" 2>/dev/null || true

    check_venv || true
    check_deps || true
    check_config || true
    check_strategy_config || true
    check_state_files || true
    check_systemd_service || true
    check_service_running || true
    check_stale_token || true

    echo ""
    info "Recent log tail:"
    tail -5 "$REPO_DIR/data/log.txt" 2>/dev/null || echo "(no log file)"
    echo ""

    info "To view live logs: journalctl --user -u $SERVICE_NAME -f"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────

MODE="${1:-}"

case "$MODE" in
    --install|-i)
        do_install
        ;;
    --fix|-f)
        do_fix
        ;;
    --status|-s)
        do_status
        ;;
    --help|-h)
        usage
        ;;
    "")
        do_install
        do_fix
        ;;
    *)
        echo "Unknown option: $MODE"
        usage
        ;;
esac
