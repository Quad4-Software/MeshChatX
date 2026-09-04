#!/bin/sh
# Shared setup for packaging service tests inside containers.
set -eu

echo "==> install rns-filesync from wheel"
if python3 -m pip install --help 2>/dev/null | grep -q break-system-packages; then
  python3 -m pip install --break-system-packages /wheels/*.whl
else
  python3 -m pip install /wheels/*.whl
fi
BIN="$(command -v rns-filesync)"
case "$BIN" in
  /usr/bin/rns-filesync) ;;
  *) ln -sfn "$BIN" /usr/bin/rns-filesync ;;
esac
test -x /usr/bin/rns-filesync
/usr/bin/rns-filesync -v

echo "==> create non-root user and state dirs"
if ! id rns-filesync >/dev/null 2>&1; then
  if command -v useradd >/dev/null 2>&1; then
    useradd --system --home-dir /var/lib/rns-filesync --create-home \
      --shell /usr/sbin/nologin rns-filesync 2>/dev/null \
    || useradd -r -d /var/lib/rns-filesync -m -s /sbin/nologin rns-filesync
  elif command -v adduser >/dev/null 2>&1; then
    adduser -S -D -h /var/lib/rns-filesync -s /sbin/nologin rns-filesync 2>/dev/null \
    || adduser --system --home /var/lib/rns-filesync --shell /usr/sbin/nologin rns-filesync
  else
    echo "FAIL: no useradd/adduser"
    exit 1
  fi
fi

# Ensure group exists for chown -g
if ! getent group rns-filesync >/dev/null 2>&1; then
  if command -v groupadd >/dev/null 2>&1; then
    groupadd --system rns-filesync 2>/dev/null || groupadd rns-filesync
  elif command -v addgroup >/dev/null 2>&1; then
    addgroup -S rns-filesync 2>/dev/null || addgroup rns-filesync
  fi
fi

install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/config
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/reticulum
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/sync

cat >/var/lib/rns-filesync/config/config <<'EOF'
[filesync]
announce_interval = 300
directory = /var/lib/rns-filesync/sync
identity = rns_filesync

[access]
sync = r:all

[logging]
loglevel = 6
EOF

cat >/var/lib/rns-filesync/reticulum/config <<'EOF'
[reticulum]
  enable_transport = Yes
  share_instance = No
  shared_instance_port = 37428
  instance_name = filesync_svc_test
  panic_on_interface_error = No

[logging]
  loglevel = 6

[interfaces]
  [[Loopback UDP]]
    type = UDPInterface
    enabled = yes
    listen_ip = 127.0.0.1
    listen_port = 42500
    forward_ip = 127.0.0.1
    forward_port = 42501
EOF

chown -R rns-filesync:rns-filesync /var/lib/rns-filesync

echo "==> shared setup done"
