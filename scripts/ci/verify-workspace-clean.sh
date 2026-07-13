#!/bin/sh
# Fail if tracked file bytes changed vs a saved inventory, or unexpected
# untracked files appeared (GitHub runner mutation check).
#
# Usage:
#   verify-workspace-clean.sh <inventory-file>
#
# Env:
#   RNS_CLEAN_ALLOW   space-separated path prefixes always ignored (optional)
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

INV="${1:?inventory file}"
if [ ! -f "$INV" ]; then
	echo "verify-workspace-clean.sh: missing inventory: $INV" >&2
	exit 1
fi

sh "$ROOT/scripts/ci/tree-manifest.sh" verify "$INV"

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
	echo "verify-workspace-clean.sh: workspace not clean" >&2
	exit 1
fi
echo "verify-workspace-clean.sh: OK"
