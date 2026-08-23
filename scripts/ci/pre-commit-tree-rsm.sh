#!/bin/sh
# Resign meshchatx.rsm when staged paths change the tree inventory.
# Called from pre-commit. Skip with SKIP=meshchatx-rsm or SKIP_TREE_RSM_HOOK=1.
# SPDX-License-Identifier: 0BSD
set -eu

if [ "${SKIP_TREE_RSM_HOOK:-0}" = "1" ]; then
	exit 0
fi

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

need_resign=0
while IFS= read -r path; do
	[ -n "$path" ] || continue
	case "$path" in
	meshchatx.rsm) continue ;;
	vendor | vendor/* | */vendor | */vendor/*) continue ;;
	*)
		need_resign=1
		break
		;;
	esac
done <<EOF
$(git diff --cached --name-only --diff-filter=ACMR)
EOF

if [ "$need_resign" -eq 0 ]; then
	exit 0
fi

ID_PATH="${RNS_ID_PATH:-}"
if [ -z "$ID_PATH" ]; then
	for candidate in \
		"$HOME/.local/share/reticulum-go/reticulum-go-release.rid" \
		"$HOME/.rngit/client_identity"
	do
		if [ -f "$candidate" ]; then
			ID_PATH="$candidate"
			break
		fi
	done
fi

if [ -z "$ID_PATH" ] || [ ! -f "$ID_PATH" ]; then
	echo "pre-commit: staged inventory paths changed but no signing identity found." >&2
	echo "pre-commit: set RNS_ID_PATH or run: make tree-rsm-sign" >&2
	echo "pre-commit: or skip with SKIP=meshchatx-rsm or SKIP_TREE_RSM_HOOK=1" >&2
	exit 0
fi

export RNS_ID_PATH="$ID_PATH"

echo "pre-commit: resigning meshchatx.rsm"
sh "$ROOT/scripts/ci/sign-tree-rsm.sh"
git add -- "$ROOT/meshchatx.rsm"
