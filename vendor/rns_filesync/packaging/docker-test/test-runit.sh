#!/bin/sh
# Test runit run script on Void (or any runit-capable image).
set -eu
. /test/common-setup.sh

install -d /etc/sv/rns-filesync
install -m 755 /packaging/runit/rns-filesync/run /etc/sv/rns-filesync/run

echo "==> shell syntax check"
sh -n /etc/sv/rns-filesync/run

echo "==> start via runit run script"
# run script execs forever - start in background by replacing exec with run
# Invoke under a subshell that keeps it as supervised child.
/etc/sv/rns-filesync/run &
pid=$!
# The run script may re-exec as another pid via su/chpst. Find the filesync process.
sleep 2
fs_pid="$(pgrep -u rns-filesync -f '/usr/bin/rns-filesync' | head -n1 || true)"
if [ -z "$fs_pid" ]; then
  echo "FAIL: rns-filesync not running after runit start"
  ps aux || true
  exit 1
fi
/test/assert-running.sh "$fs_pid" rns-filesync
kill "$pid" 2>/dev/null || true

echo "PASS: runit"
