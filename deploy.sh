#!/usr/bin/env bash
#
# deploy.sh — push the local AquaLog working tree to the server and restart it.
#
# Runs on the DEV machine (Git Bash on Windows, or any POSIX shell) and talks to
# the server over SSH. Transfers with rsync when available, otherwise falls back
# to a tar-over-ssh pipe (Git Bash ships ssh/scp/tar but not rsync).
#
#   ./deploy.sh                 # test, back up remote DB, push, restart, health-check
#   ./deploy.sh --skip-tests    # skip the local pytest gate
#   ./deploy.sh --deps          # force pip install -r requirements.txt on the server
#   ./deploy.sh --restart-only  # no transfer, just restart the tmux session
#   ./deploy.sh --dry-run       # show what would be sent, change nothing
#
# Config via environment (defaults shown):
#   REMOTE_HOST=arm@10.0.40.100
#   REMOTE_DIR=/home/arm/projects/aquaLog
#   TMUX_SESSION=aqualog
#   APP_PORT=8501
#
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-arm@10.0.40.100}"
REMOTE_DIR="${REMOTE_DIR:-/home/arm/projects/aquaLog}"
TMUX_SESSION="${TMUX_SESSION:-aqualog}"
APP_PORT="${APP_PORT:-8501}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"
SSH_OPTS="${SSH_OPTS:--o ConnectTimeout=10}"

# Never overwrite these on the server. aqualog.db is the LIVE database and is
# (unfortunately) tracked in git, so it must be excluded explicitly — otherwise a
# deploy would stomp production data with whatever dev DB is in the working tree.
EXCLUDES=(
  "aqualog.db"
  "aqualog.db-journal"
  "aqualog.db-wal"
  "aqualog.db-shm"
  ".git"
  ".venv"
  "venv"
  "__pycache__"
  "*.pyc"
  ".pytest_cache"
  "backups"
  "logs"
  ".streamlit/secrets.toml"
  ".deploy-reqs.sha"
)

SKIP_TESTS=0
FORCE_DEPS=0
RESTART_ONLY=0
DRY_RUN=0
PRUNE=0
LOAD_MASTER=0

# Print the header comment block (line 3 up to the first non-comment line).
usage() {
  awk 'NR>2 && /^#/ { sub(/^# ?/, ""); print; next } NR>2 { exit }' "$0"
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-tests)        SKIP_TESTS=1 ;;
    --deps)              FORCE_DEPS=1 ;;
    --restart-only)      RESTART_ONLY=1 ;;
    --dry-run)           DRY_RUN=1 ;;
    --prune)             PRUNE=1 ;;
    --load-master-data)  LOAD_MASTER=1 ;;
    -h|--help)           usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
  shift
done

cd "$(dirname "$0")"

BOLD=$'\033[1m'; RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; OFF=$'\033[0m'
step() { printf '%s==>%s %s\n' "$BOLD" "$OFF" "$*"; }
ok()   { printf '  %sok%s   %s\n' "$GRN" "$OFF" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YLW" "$OFF" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$OFF" "$*" >&2; exit 1; }

# ─── 1. Local test gate ──────────────────────────────────────────────────────
if [ "$SKIP_TESTS" -eq 0 ] && [ "$RESTART_ONLY" -eq 0 ]; then
  step "Running local test suite"
  if command -v python >/dev/null 2>&1; then PY_LOCAL=python; else PY_LOCAL=python3; fi
  "$PY_LOCAL" -m pytest tests -q || die "tests failed — fix them or re-run with --skip-tests"
  ok "tests passed"
else
  warn "skipping local tests"
fi

# ─── 2. Connectivity ─────────────────────────────────────────────────────────
step "Checking SSH to $REMOTE_HOST"
# shellcheck disable=SC2086
ssh $SSH_OPTS -n "$REMOTE_HOST" "test -d '$REMOTE_DIR'" \
  || die "cannot reach $REMOTE_HOST or $REMOTE_DIR does not exist"
ok "$REMOTE_HOST:$REMOTE_DIR reachable"

# ─── 3. Back up the live database BEFORE touching anything ───────────────────
if [ "$DRY_RUN" -eq 0 ]; then
  step "Backing up remote database"
  # shellcheck disable=SC2086
  ssh $SSH_OPTS "$REMOTE_HOST" bash -s -- "$REMOTE_DIR" "$KEEP_BACKUPS" <<'REMOTE_BACKUP'
set -euo pipefail
DIR="$1"; KEEP="$2"
cd "$DIR"
mkdir -p backups logs
if [ -f aqualog.db ]; then
  STAMP="$(date +%Y%m%d-%H%M%S)"
  # sqlite3's .backup is safe against a live writer; cp is the fallback.
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 aqualog.db ".backup 'backups/aqualog-$STAMP.db'"
  else
    cp -p aqualog.db "backups/aqualog-$STAMP.db"
  fi
  echo "  backed up to backups/aqualog-$STAMP.db ($(du -h "backups/aqualog-$STAMP.db" | cut -f1))"
  # Keep only the newest $KEEP backups.
  ls -1t backups/aqualog-*.db 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f
else
  echo "  no aqualog.db on the server yet — nothing to back up"
fi
REMOTE_BACKUP
  ok "database backed up"
fi

# ─── 4. Transfer ─────────────────────────────────────────────────────────────
if [ "$RESTART_ONLY" -eq 1 ]; then
  warn "--restart-only: skipping transfer"
elif command -v rsync >/dev/null 2>&1; then
  step "Syncing with rsync"
  RSYNC_ARGS=(-az --human-readable --itemize-changes)
  for e in "${EXCLUDES[@]}"; do RSYNC_ARGS+=(--exclude "$e"); done
  [ "$PRUNE" -eq 1 ]   && RSYNC_ARGS+=(--delete)          # excluded files stay protected
  [ "$DRY_RUN" -eq 1 ] && RSYNC_ARGS+=(--dry-run)
  # shellcheck disable=SC2086
  rsync "${RSYNC_ARGS[@]}" -e "ssh $SSH_OPTS" ./ "$REMOTE_HOST:$REMOTE_DIR/"
  ok "files synced"
else
  step "Syncing with tar over ssh (rsync not installed)"
  [ "$PRUNE" -eq 1 ] && warn "--prune needs rsync; stale remote files will be left in place"
  TAR_ARGS=()
  for e in "${EXCLUDES[@]}"; do TAR_ARGS+=(--exclude="$e"); done
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  would send:"
    tar "${TAR_ARGS[@]}" -cvf /dev/null . 2>/dev/null | sed 's|^\./|    |'
  else
    # Staged through /tmp so a dropped connection can't leave a half-extracted tree.
    tar "${TAR_ARGS[@]}" -czf - . \
      | ssh $SSH_OPTS "$REMOTE_HOST" "cat > /tmp/aqualog-deploy.tgz \
          && tar xzf /tmp/aqualog-deploy.tgz -C '$REMOTE_DIR' \
          && rm -f /tmp/aqualog-deploy.tgz"
    ok "files synced"
  fi
fi

if [ "$DRY_RUN" -eq 1 ]; then
  step "Dry run complete — nothing was changed on the server"
  exit 0
fi

# ─── 5. Dependencies + restart + health check ────────────────────────────────
step "Installing deps and restarting"
# shellcheck disable=SC2086
ssh $SSH_OPTS "$REMOTE_HOST" bash -s -- \
    "$REMOTE_DIR" "$TMUX_SESSION" "$APP_PORT" "$FORCE_DEPS" "$LOAD_MASTER" <<'REMOTE_DEPLOY'
set -euo pipefail
DIR="$1"; SESSION="$2"; PORT="$3"; FORCE_DEPS="$4"; LOAD_MASTER="$5"
cd "$DIR"

# Prefer the project venv if one exists; fall back to system python3.
if [ -x ".venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="$DIR/venv/bin/python"
else
  PY="$(command -v python3)"
  echo "  no venv found — using system $PY"
fi
echo "  python: $PY ($("$PY" --version 2>&1))"

# Only reinstall when requirements.txt actually changed (or --deps was passed).
REQ_SHA="$(sha256sum requirements.txt | cut -d' ' -f1)"
if [ "$FORCE_DEPS" = "1" ] || [ ! -f .deploy-reqs.sha ] || [ "$(cat .deploy-reqs.sha)" != "$REQ_SHA" ]; then
  echo "  requirements changed — installing"
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet -r requirements.txt
  echo "$REQ_SHA" > .deploy-reqs.sha
else
  echo "  requirements unchanged — skipping pip install"
fi

# Opt-in only: injectFish/injectPlants DROP and rebuild the master catalogues.
if [ "$LOAD_MASTER" = "1" ]; then
  echo "  reloading master fish/plant data"
  "$PY" injectFish.py
  "$PY" injectPlants.py
fi

command -v tmux >/dev/null 2>&1 || { echo "tmux is not installed on the server" >&2; exit 1; }

# Stop the old app. Kill the dedicated session, then sweep any stray process
# still bound to this port (matched on the port so other apps are untouched).
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "  killing tmux session '$SESSION'"
  tmux kill-session -t "$SESSION"
fi
pkill -f "server.port=$PORT" 2>/dev/null || true
sleep 1

mkdir -p logs
LOG="$DIR/logs/streamlit.log"
[ -f "$LOG" ] && mv "$LOG" "$LOG.1"

echo "  starting streamlit in tmux session '$SESSION' on port $PORT"
tmux new-session -d -s "$SESSION" -c "$DIR" \
  "exec '$PY' -m streamlit run main.py \
     --server.port=$PORT \
     --server.address=0.0.0.0 \
     --server.headless=true \
     >> '$LOG' 2>&1"

# ── Health check ───────────────────────────────────────────────────────────
# main.py calls init_tables() at startup, so any schema migration runs here.
HEALTHY=0
for i in $(seq 1 30); do
  if command -v curl >/dev/null 2>&1; then
    if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/_stcore/health" >/dev/null 2>&1 \
    || curl -fsS --max-time 2 "http://127.0.0.1:$PORT/healthz"        >/dev/null 2>&1; then
      HEALTHY=1; break
    fi
  else
    if "$PY" - "$PORT" <<'PYCHK' >/dev/null 2>&1
import socket, sys
s = socket.create_connection(("127.0.0.1", int(sys.argv[1])), 2); s.close()
PYCHK
    then HEALTHY=1; break; fi
  fi
  sleep 1
done

if [ "$HEALTHY" = "1" ]; then
  echo "  app is up and answering on port $PORT"
else
  echo "" >&2
  echo "  HEALTH CHECK FAILED after 30s — last 40 log lines:" >&2
  tail -n 40 "$LOG" >&2 || true
  echo "" >&2
  echo "  the previous database is untouched; newest backup:" >&2
  ls -1t backups/aqualog-*.db 2>/dev/null | head -1 >&2 || true
  exit 1
fi
REMOTE_DEPLOY

ok "deployed"
step "Done"
printf '  app:     http://%s:%s\n' "${REMOTE_HOST#*@}" "$APP_PORT"
printf '  logs:    ssh %s "tail -f %s/logs/streamlit.log"\n' "$REMOTE_HOST" "$REMOTE_DIR"
printf '  attach:  ssh %s -t "tmux attach -t %s"\n' "$REMOTE_HOST" "$TMUX_SESSION"
printf '  backups: ssh %s "ls -lt %s/backups | head"\n' "$REMOTE_HOST" "$REMOTE_DIR"
