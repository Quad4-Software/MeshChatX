#!/bin/sh
# Exercise the documented Bubblewrap sandbox command on the host.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
if [ -x "$ROOT/.venv/bin/rns-filesync" ]; then
  RNS_BIN="$ROOT/.venv/bin/rns-filesync"
elif command -v rns-filesync >/dev/null 2>&1; then
  RNS_BIN="$(command -v rns-filesync)"
else
  echo "FAIL: rns-filesync not found"
  exit 1
fi

if ! command -v bwrap >/dev/null 2>&1; then
  echo "FAIL: bwrap not installed (package bubblewrap)"
  exit 1
fi

DATA="${XDG_DATA_HOME:-$HOME/.local/share}/rns-filesync-sandbox-test"
rm -rf "$DATA"
mkdir -p "$DATA/config" "$DATA/sync" "$DATA/reticulum"

cat > "$DATA/config/config" <<EOF
[filesync]
announce_interval = 300
directory = $DATA/sync
identity = rns_filesync

[access]
sync = r:all

[logging]
loglevel = 6
EOF

cat > "$DATA/reticulum/config" <<'EOF'
[reticulum]
  enable_transport = Yes
  share_instance = No
  shared_instance_port = 37501
  instance_name = filesync_bwrap_test
  panic_on_interface_error = No

[logging]
  loglevel = 6

[interfaces]
  [[Loopback UDP]]
    type = UDPInterface
    enabled = yes
    listen_ip = 127.0.0.1
    listen_port = 42610
    forward_ip = 127.0.0.1
    forward_port = 42611
EOF

echo "==> version inside bwrap"
bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --uid "$(id -u)" --gid "$(id -g)" \
  "$RNS_BIN" --version

echo "==> start sandboxed daemon (README command shape)"
bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --uid "$(id -u)" --gid "$(id -g)" \
  "$RNS_BIN" \
    --config "$DATA/config" \
    --rnsconfig "$DATA/reticulum" \
    -d "$DATA/sync" \
    --no-repl \
    -q &
BPID=$!
sleep 3
if ! kill -0 "$BPID" 2>/dev/null; then
  echo "FAIL: bwrap daemon died"
  wait "$BPID" || true
  exit 1
fi
echo "OK: sandboxed daemon pid=$BPID alive"

echo sandbox-write-ok > "$DATA/sync/probe.txt"
test -f "$DATA/sync/probe.txt"
echo "OK: DATA sync dir is writable"

if bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --uid "$(id -u)" --gid "$(id -g)" \
  /bin/sh -c 'echo should-fail > /etc/rns-filesync-bwrap-probe'; then
  echo "FAIL: wrote outside DATA"
  kill "$BPID" 2>/dev/null || true
  exit 1
fi
echo "OK: root outside DATA is read-only"

kill "$BPID" 2>/dev/null || true
wait "$BPID" 2>/dev/null || true
rm -rf "$DATA"
echo "PASS: bwrap sandbox command"
