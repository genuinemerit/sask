#!/usr/bin/env bash
# Manage the dev sask systemd --user service (DD-0021, SPEC-033).
#
# Mirrors production's stdout -> systemd -> journald path in dev, so
# `journalctl` (and later the CLI's `logs query`) behave the same way in
# both environments. No application code is touched by this script.
#
#   bash tools/dev/sask-dev-service.sh install
#   bash tools/dev/sask-dev-service.sh enable
#   bash tools/dev/sask-dev-service.sh start
#   bash tools/dev/sask-dev-service.sh status
#   bash tools/dev/sask-dev-service.sh tail          # follow (Ctrl-C to stop)
#   bash tools/dev/sask-dev-service.sh logs [N]       # last N lines, default 50
#   bash tools/dev/sask-dev-service.sh stop
#   bash tools/dev/sask-dev-service.sh restart

set -euo pipefail

cd "$(dirname "$0")/../.."
REPO_ROOT="$(pwd)"

UNIT_NAME="sask-dev.service"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_PATH="${UNIT_DIR}/${UNIT_NAME}"
TEMPLATE_PATH="${REPO_ROOT}/tools/dev/sask-dev.service.template"

pass() { printf '[PASS]  %s\n' "$1"; }
info() { printf '[INFO]  %s\n' "$1"; }
fail() {
    printf '[FAIL]  %s\n' "$1" >&2
    exit 1
}

cmd_install() {
    [[ -f "$TEMPLATE_PATH" ]] || fail "template not found: $TEMPLATE_PATH"

    VENV_PATH="$(poetry env info --path 2>/dev/null || true)"
    if [[ -z "$VENV_PATH" ]]; then
        fail "poetry env info --path returned nothing — run 'poetry install' first"
    fi

    mkdir -p "$UNIT_DIR"
    sed -e "s|__REPO_ROOT__|${REPO_ROOT}|g" \
        -e "s|__VENV_PATH__|${VENV_PATH}|g" \
        "$TEMPLATE_PATH" > "$UNIT_PATH"
    pass "wrote $UNIT_PATH (repo=${REPO_ROOT}, venv=${VENV_PATH})"

    systemctl --user daemon-reload
    pass "systemctl --user daemon-reload"

    # Investigate, don't silently change, linger state: systemd's documented
    # behavior (see systemd-logind(8), "Lingering") is that a user's --user
    # instance and its units stop when that user's last session ends, unless
    # lingering is enabled for the account (loginctl enable-linger <user>),
    # which keeps the user instance running independent of active sessions
    # and starts it at boot. This is standard systemd behavior, not something
    # specific to this host to be discovered empirically.
    if loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q "Linger=yes"; then
        info "lingering is already enabled for $USER — the service can run without an active session"
    else
        info "lingering is NOT enabled for $USER — sask-dev.service will stop when your last session ends"
        info "to keep it running across logout (optional), run yourself: loginctl enable-linger $USER"
    fi
}

cmd_enable()  { systemctl --user enable "$UNIT_NAME";  pass "enabled $UNIT_NAME"; }
cmd_start()   { systemctl --user start "$UNIT_NAME";   pass "started $UNIT_NAME"; }
cmd_stop()    { systemctl --user stop "$UNIT_NAME";    pass "stopped $UNIT_NAME"; }
cmd_restart() { systemctl --user restart "$UNIT_NAME"; pass "restarted $UNIT_NAME"; }
cmd_status()  { systemctl --user status "$UNIT_NAME"; }
cmd_tail()    { journalctl --user -u "sask-dev" -f; }
cmd_logs() {
    local n="${1:-50}"
    journalctl --user -u "sask-dev" --no-pager -n "$n"
}

case "${1:-}" in
    install)  cmd_install ;;
    enable)   cmd_enable ;;
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    restart)  cmd_restart ;;
    status)   cmd_status ;;
    tail)     cmd_tail ;;
    logs)     cmd_logs "${2:-}" ;;
    *)
        printf '[FAIL] Usage: %s {install|enable|start|stop|restart|status|tail|logs [N]}\n' "$0" >&2
        exit 1
        ;;
esac
