#!/bin/sh
# Test dinit service file and the command it would run.
set -eu
. /test/common-setup.sh

svc=/packaging/dinit/rns-filesync
install -d /etc/dinit.d
install -m 644 "$svc" /etc/dinit.d/rns-filesync

echo "==> validate dinit service keys"
grep -Eq '^type = process$' /etc/dinit.d/rns-filesync
grep -Eq '^restart = true$' /etc/dinit.d/rns-filesync
grep -Eq '^runs-as = rns-filesync$' /etc/dinit.d/rns-filesync
grep -Eq '^command = .*/usr/bin/rns-filesync' /etc/dinit.d/rns-filesync

if command -v dinitcheck >/dev/null 2>&1; then
  echo "==> dinitcheck"
  dinitcheck /etc/dinit.d/rns-filesync || dinitcheck -d /etc/dinit.d
fi

echo "==> run service command as rns-filesync"
su -s /bin/sh -c \
  'exec /usr/bin/env HOME=/var/lib/rns-filesync /usr/bin/rns-filesync --config /var/lib/rns-filesync/config --rnsconfig /var/lib/rns-filesync/reticulum -d /var/lib/rns-filesync/sync --no-repl -q' \
  rns-filesync &
pid=$!
sleep 1
fs_pid="$(pgrep -u rns-filesync -f '/usr/bin/rns-filesync' | head -n1 || true)"
if [ -z "$fs_pid" ]; then
  echo "FAIL: rns-filesync not running as rns-filesync"
  ps aux || true
  exit 1
fi
/test/assert-running.sh "$fs_pid" rns-filesync

echo "PASS: dinit"
