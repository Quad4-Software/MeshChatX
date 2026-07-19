#!/bin/sh
# Test OpenRC service on Alpine.
set -eu
. /test/common-setup.sh

install -m 755 /packaging/openrc/rns-filesync /etc/init.d/rns-filesync

echo "==> shell syntax check"
sh -n /etc/init.d/rns-filesync

echo "==> openrc script metadata"
grep -q 'command="/usr/bin/rns-filesync"' /etc/init.d/rns-filesync
grep -q 'command_user="rns-filesync:rns-filesync"' /etc/init.d/rns-filesync
grep -q 'command_background=yes' /etc/init.d/rns-filesync

echo "==> mimic start_pre (checkpath dirs)"
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/config
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/reticulum
install -d -o rns-filesync -g rns-filesync -m 0700 /var/lib/rns-filesync/sync

echo "==> start daemon via openrc command + args as service user"
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

echo "PASS: openrc"
