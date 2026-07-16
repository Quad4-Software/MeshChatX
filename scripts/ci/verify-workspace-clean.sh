#!/bin/sh
# Recheck byte-level tree inventory and report unexpected runner mutations.
#
# By default mismatches print warnings and exit 0 so CI is not blocked when
# signed inventories lag license refreshes or ephemeral runner dirt appears.
# Set RNS_TREE_VERIFY_STRICT=1 to exit non-zero on failure.
#
# Usage:
#   verify-workspace-clean.sh <inventory-file>
#
# Env:
#   RNS_CLEAN_ALLOW   space-separated path prefixes always ignored (optional)
#   RNS_TREE_VERIFY_STRICT  if 1, fail the process on verify errors
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

STRICT="${RNS_TREE_VERIFY_STRICT:-0}"

warn_or_fail() {
	msg="$1"
	if [ "$STRICT" = "1" ]; then
		echo "verify-workspace-clean.sh: $msg" >&2
		exit 1
	fi
	echo "verify-workspace-clean.sh: WARNING: $msg (non-blocking)" >&2
	exit 0
}

INV="${1:-}"
if [ -z "$INV" ] || [ ! -f "$INV" ]; then
	warn_or_fail "missing inventory: ${INV:-<unset>} (tree verify may have been skipped)"
fi

if ! sh "$ROOT/scripts/ci/tree-manifest.sh" verify "$INV"; then
	warn_or_fail "tree inventory hash check failed"
fi

# Default ephemeral prefixes created by CI / local builds
ALLOW="node_modules/ .pnpm-store/ .venv/ .venv-x64/ dist/ build/ electron/build/ meshchatx/public/ python-dist/ playwright-report/ mutants/ coverage/ .flatpak-builder/ parts/ prime/ stage/ android/.gradle/ android/app/build/ android/build/ android/vendor/ .cache/ __pycache__/ .pytest_cache/ vendor/offline/"
ALLOW="$ALLOW ${RNS_CLEAN_ALLOW:-}"

is_allowed() {
	p="$1"
	for a in $ALLOW; do
		case "$p" in
		"$a" | "$a"*)
			return 0
			;;
		esac
	done
	case "$p" in
	vendor | vendor/* | */vendor | */vendor/*)
		return 0
		;;
	*.log | *.tmp | *.swp | *.egg-info | *.pyc)
		return 0
		;;
	esac
	return 1
}

fail=0
tmp="$(mktemp "${TMPDIR:-/tmp}/ws-clean.XXXXXX")"
trap 'rm -f "$tmp"' EXIT INT
git status --porcelain -u --ignored=no >"$tmp" 2>/dev/null || git status --porcelain -u >"$tmp"
while IFS= read -r line; do
	[ -z "$line" ] && continue
	xy="$(printf '%s\n' "$line" | cut -c1-2)"
	path="$(printf '%s\n' "$line" | sed 's/^.. //;s/.* -> //')"
	case "$xy" in
	"??")
		if is_allowed "$path"; then
			continue
		fi
		echo "verify-workspace-clean.sh: unexpected untracked: $path" >&2
		fail=1
		;;
	*)
		if [ "$path" = "meshchatx.rsm" ]; then
			continue
		fi
		if is_allowed "$path"; then
			continue
		fi
		echo "verify-workspace-clean.sh: unexpected change: $line" >&2
		fail=1
		;;
	esac
done <"$tmp"

if [ "$fail" -ne 0 ]; then
	warn_or_fail "workspace not clean"
fi
echo "verify-workspace-clean.sh: OK"
