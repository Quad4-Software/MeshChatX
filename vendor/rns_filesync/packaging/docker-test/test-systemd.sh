#!/bin/sh
# Test systemd unit inside a running systemd container.
set -eu
. /test/common-setup.sh

install -m 644 /packaging/sysusers.d/rns-filesync.conf /usr/lib/sysusers.d/ 2>/dev/null || true
install -m 644 /packaging/tmpfiles.d/rns-filesync.conf /usr/lib/tmpfiles.d/ 2>/dev/null || true
systemd-sysusers || true
systemd-tmpfiles --create || true

install -m 644 /packaging/systemd/rns-filesync.service /etc/systemd/system/rns-filesync.service
install -m 644 /packaging/systemd/rns-filesync.user.service /tmp/rns-filesync.user.service

echo "==> systemd-analyze verify (system unit)"
# Documentation=man: fails verify when man page is not installed in the image.
cp /etc/systemd/system/rns-filesync.service /tmp/rns-filesync.verify.service
sed -i '/^Documentation=/d' /tmp/rns-filesync.verify.service
systemd-analyze verify /tmp/rns-filesync.verify.service

echo "==> check user unit file parses"
grep -q 'ExecStart=' /tmp/rns-filesync.user.service
grep -q 'NoNewPrivileges=true' /tmp/rns-filesync.user.service

echo "==> systemctl enable and start"
systemctl daemon-reload
systemctl enable rns-filesync.service
systemctl start rns-filesync.service
sleep 4
systemctl --no-pager --full status rns-filesync.service || true
if ! systemctl is-active --quiet rns-filesync.service; then
  echo "WARN: systemctl start did not reach active (common in nested cgroup docker)"
  echo "==> fallback: start ExecStart as service user"
  su -s /bin/sh -c \
    'exec /usr/bin/rns-filesync --config /var/lib/rns-filesync/config --rnsconfig /var/lib/rns-filesync/reticulum -d /var/lib/rns-filesync/sync --no-repl -q' \
    rns-filesync &
  sleep 1
  fs_pid="$(pgrep -u rns-filesync -f '/usr/bin/rns-filesync' | head -n1 || true)"
  if [ -z "$fs_pid" ]; then
    echo "FAIL: rns-filesync not running as rns-filesync"
    ps aux || true
    exit 1
  fi
  /test/assert-running.sh "$fs_pid" rns-filesync
else
  echo "==> active via systemd"
  sleep 2
  systemctl is-active rns-filesync.service | grep -qx active
  systemctl stop rns-filesync.service
fi

echo "PASS: systemd"
