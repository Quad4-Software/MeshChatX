#!/bin/sh
# Generate or verify a byte-level SHA-256 inventory of git-tracked files.
#
# Format (sha256sum style, deterministic):
#   # meshchatx tree manifest v1
#   <sha256-hex>  <path>
#
# meshchatx.rsm is excluded from the inventory (avoids a self-hash cycle).
# Paths under any vendor/ directory are excluded (vendored trees are not
# first-party inventory).
#
# Paths are listed via newline-delimited git ls-files (POSIX sh / dash safe).
# Do not use read -d or sort -z (bash/GNU-only).
#
# Usage:
#   tree-manifest.sh generate              write inventory to stdout
#   tree-manifest.sh verify [inventory]    verify against file or stdin
#   tree-manifest.sh verify-tracked [inv]  also fail if tracked files are missing from inv
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

MANIFEST_HEADER="# meshchatx tree manifest v1"
EXCLUDE_RSM="meshchatx.rsm"

# True when path is the root RSM or lives under a vendor directory.
is_excluded_path() {
	f="$1"
	[ "$f" = "$EXCLUDE_RSM" ] && return 0
	case "$f" in
	vendor | vendor/* | */vendor | */vendor/*)
		return 0
		;;
	esac
	return 1
}

file_sha256_stream() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum | awk '{print $1}'
	elif command -v shasum >/dev/null 2>&1; then
		shasum -a 256 | awk '{print $1}'
	else
		echo "tree-manifest.sh: need sha256sum or shasum" >&2
		return 1
	fi
}

file_sha256() {
	f="$1"
	file_sha256_stream <"$f"
}

# Hash the index blob (staged or HEAD), not unstaged working-tree dirt.
index_sha256() {
	f="$1"
	git show ":$f" | file_sha256_stream
}

tracked_paths() {
	git ls-files | LC_ALL=C sort
}

generate() {
	if command -v python3 >/dev/null 2>&1 && [ -f "$ROOT/scripts/ci/tree_manifest_generate.py" ]; then
		python3 "$ROOT/scripts/ci/tree_manifest_generate.py"
		return $?
	fi
	printf '%s\n' "$MANIFEST_HEADER"
	tracked_paths | while IFS= read -r f; do
		[ -n "$f" ] || continue
		if is_excluded_path "$f"; then
			continue
		fi
		if ! git cat-file -e ":$f" 2>/dev/null; then
			continue
		fi
		mode="$(git ls-files -s -- "$f" | awk '{print $1}')"
		case "$mode" in
		100644 | 100755) ;;
		*) continue ;;
		esac
		sum="$(index_sha256 "$f")"
		printf '%s  %s\n' "$sum" "$f"
	done
}

load_inventory() {
	inv_file="$1"
	if [ "$inv_file" = "-" ] || [ -z "$inv_file" ]; then
		cat
	else
		cat -- "$inv_file"
	fi
}

verify() {
	check_tracked="${1:-0}"
	inv_src="${2:-}"
	tmp="$(mktemp "${TMPDIR:-/tmp}/tree-manifest.XXXXXX")"
	trap 'rm -f "$tmp" "$tmp.expect" "$tmp.actual" "$tmp.tracked"' EXIT INT
	load_inventory "$inv_src" >"$tmp"

	header="$(sed -n '1p' "$tmp")"
	if [ "$header" != "$MANIFEST_HEADER" ]; then
		echo "tree-manifest.sh: bad header: $header" >&2
		return 1
	fi

	tmp_expect="${tmp}.expect"
	tmp_actual="${tmp}.actual"
	# Drop header and blank lines. normalize to "hash  path"
	sed '1d;/^$/d;/^#/d' "$tmp" | awk 'NF>=2 {print $1 "  " substr($0, index($0,$2))}' | LC_ALL=C sort -k2 >"$tmp_expect"

	fail=0
	while IFS= read -r line; do
		[ -z "$line" ] && continue
		hash="${line%%  *}"
		path="${line#*  }"
		if [ ! -f "$path" ]; then
			echo "tree-manifest.sh: missing: $path" >&2
			fail=1
			continue
		fi
		got="$(file_sha256 "$path")"
		if [ "$got" != "$hash" ]; then
			echo "tree-manifest.sh: modified: $path" >&2
			echo "  expected $hash" >&2
			echo "  got      $got" >&2
			fail=1
		fi
	done <"$tmp_expect"

	if [ "$check_tracked" = "1" ]; then
		tmp_tracked="${tmp}.tracked"
		: >"$tmp_tracked"
		tracked_paths | while IFS= read -r f; do
			[ -n "$f" ] || continue
			if is_excluded_path "$f"; then
				continue
			fi
			[ -f "$f" ] || continue
			[ -L "$f" ] && continue
			printf '%s\n' "$f"
		done | LC_ALL=C sort >"$tmp_tracked"

		awk '{print substr($0, index($0,$2))}' "$tmp_expect" | LC_ALL=C sort >"$tmp_actual"
		extra="$(comm -13 "$tmp_tracked" "$tmp_actual" || true)"
		missing="$(comm -23 "$tmp_tracked" "$tmp_actual" || true)"
		if [ -n "$extra" ]; then
			echo "tree-manifest.sh: inventory has paths not tracked (or excluded):" >&2
			printf '%s\n' "$extra" >&2
			fail=1
		fi
		if [ -n "$missing" ]; then
			echo "tree-manifest.sh: tracked files missing from inventory (added?):" >&2
			printf '%s\n' "$missing" >&2
			fail=1
		fi
	fi

	if [ "$fail" -ne 0 ]; then
		echo "tree-manifest.sh: verification failed" >&2
		return 1
	fi
	echo "tree-manifest.sh: OK ($(wc -l <"$tmp_expect" | tr -d ' ') files)"
}

cmd="${1:-}"
case "$cmd" in
generate)
	generate
	;;
verify)
	verify 0 "${2:-}"
	;;
verify-tracked)
	verify 1 "${2:-}"
	;;
*)
	echo "Usage: $0 generate | verify [file|-] | verify-tracked [file|-]" >&2
	exit 2
	;;
esac
