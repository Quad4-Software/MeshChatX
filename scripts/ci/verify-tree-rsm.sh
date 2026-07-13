#!/bin/sh
# Verify meshchatx.rsm signature and byte-level file hashes.
#
# Env:
#   RNS_REQUIRED_SIGNER  identity hash (default: e46112d44649266d71fe2193e00a4710)
#   RNS_RSM_PATH         path to .rsm (default: meshchatx.rsm)
#   RNS_INVENTORY_OUT    if set, write extracted inventory here (for end-of-job recheck)
#
# Usage:
#   sh scripts/ci/verify-tree-rsm.sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SIGNER="${RNS_REQUIRED_SIGNER:-e46112d44649266d71fe2193e00a4710}"
RSM_PATH="${RNS_RSM_PATH:-$ROOT/meshchatx.rsm}"
HEADER="# meshchatx tree manifest v1"

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
	echo "verify-tree-rsm.sh: missing $RSM_PATH" >&2
	exit 1
fi

INV="$(mktemp "${TMPDIR:-/tmp}/tree-inv-verify.XXXXXX")"
RAW="$(mktemp "${TMPDIR:-/tmp}/tree-rsm-raw.XXXXXX")"
trap 'rm -f "$INV" "$RAW"' EXIT INT

if ! run_rnid -i "$SIGNER" -V "$RSM_PATH" >"$RAW" 2>/dev/null; then
	echo "verify-tree-rsm.sh: RSM signature verification failed" >&2
	exit 1
fi

# Keep only the embedded inventory (starts at the manifest header line).
awk -v h="$HEADER" 'BEGIN{p=0} $0==h{p=1} p{print}' "$RAW" >"$INV"
if [ ! -s "$INV" ]; then
	echo "verify-tree-rsm.sh: could not extract inventory from RSM" >&2
	exit 1
fi

if [ -n "${RNS_INVENTORY_OUT:-}" ]; then
	cp "$INV" "$RNS_INVENTORY_OUT"
fi

sh "$ROOT/scripts/ci/tree-manifest.sh" verify-tracked "$INV"
echo "verify-tree-rsm.sh: OK (signer $SIGNER)"
