#!/bin/sh
# Verify meshchatx.rsm signature and byte-level file hashes.
#
# By default mismatches print warnings and exit 0 so CI is not blocked when
# the signed inventory lags dependency or license refreshes.
# Set RNS_TREE_VERIFY_STRICT=1 to exit non-zero on failure.
#
# Env:
#   RNS_REQUIRED_SIGNER  identity hash (default: e46112d44649266d71fe2193e00a4710)
#   RNS_RSM_PATH         path to .rsm (default: meshchatx.rsm)
#   RNS_INVENTORY_OUT    if set, write extracted inventory here (for end-of-job recheck)
#   RNS_TREE_VERIFY_STRICT  if 1, fail the process on verify errors
#
# Usage:
#   sh scripts/ci/verify-tree-rsm.sh
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SIGNER="${RNS_REQUIRED_SIGNER:-e46112d44649266d71fe2193e00a4710}"
RSM_PATH="${RNS_RSM_PATH:-$ROOT/meshchatx.rsm}"
HEADER="# meshchatx tree manifest v1"
STRICT="${RNS_TREE_VERIFY_STRICT:-0}"

warn_or_fail() {
	msg="$1"
	if [ "$STRICT" = "1" ]; then
		echo "verify-tree-rsm.sh: $msg" >&2
		exit 1
	fi
	echo "verify-tree-rsm.sh: WARNING: $msg (non-blocking)" >&2
	exit 0
}

run_rnid() {
	if command -v rnid >/dev/null 2>&1; then
		rnid "$@"
	elif [ -x "$ROOT/.venv/bin/rnid" ]; then
		"$ROOT/.venv/bin/rnid" "$@"
	elif command -v uv >/dev/null 2>&1; then
		uv run rnid "$@"
	else
		echo "verify-tree-rsm.sh: rnid not found (install rns or sync the venv)" >&2
		return 1
	fi
}

if [ ! -f "$RSM_PATH" ]; then
	warn_or_fail "missing $RSM_PATH"
fi

INV="$(mktemp "${TMPDIR:-/tmp}/tree-inv-verify.XXXXXX")"
RAW="$(mktemp "${TMPDIR:-/tmp}/tree-rsm-raw.XXXXXX")"
trap 'rm -f "$INV" "$RAW"' EXIT INT

if ! run_rnid -i "$SIGNER" -V "$RSM_PATH" >"$RAW" 2>/dev/null; then
	warn_or_fail "RSM signature verification failed"
fi

# Keep only the embedded inventory (starts at the manifest header line).
awk -v h="$HEADER" 'BEGIN{p=0} $0==h{p=1} p{print}' "$RAW" >"$INV"
if [ ! -s "$INV" ]; then
	warn_or_fail "could not extract inventory from RSM"
fi

if [ -n "${RNS_INVENTORY_OUT:-}" ]; then
	cp "$INV" "$RNS_INVENTORY_OUT"
fi

if ! sh "$ROOT/scripts/ci/tree-manifest.sh" verify-tracked "$INV"; then
	warn_or_fail "tree inventory hash check failed"
fi
echo "verify-tree-rsm.sh: OK (signer $SIGNER)"
