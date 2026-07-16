#!/usr/bin/env bash
# Fail if release artifacts contain paths that should not ship
# (dev trees, duplicate frontend sources, vendor offline caches, etc.).
#
# Usage:
#   verify-package-contents.sh frozen [build/exe]
#   verify-package-contents.sh docker [image:tag]
#   verify-package-contents.sh wheel [path/to.whl]
#   verify-package-contents.sh dir [path]
#   verify-package-contents.sh appimage [path/to.AppImage]
#   verify-package-contents.sh deb [path/to.deb]
#   verify-package-contents.sh apk [path/to.apk]
#
# Env:
#   PACKAGE_BLOAT_MAX_HITS   stop after N hits (default 40)
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
MODE="${1:-}"
TARGET="${2:-}"
MAX_HITS="${PACKAGE_BLOAT_MAX_HITS:-40}"

usage() {
	cat <<'EOF' >&2
Usage:
  verify-package-contents.sh frozen [build/exe]
  verify-package-contents.sh docker [image:tag]
  verify-package-contents.sh wheel [file.whl]
  verify-package-contents.sh dir [path]
  verify-package-contents.sh appimage [file.AppImage]
  verify-package-contents.sh deb [file.deb]
  verify-package-contents.sh apk [file.apk]
EOF
	exit 2
}

[ -n "$MODE" ] || usage

hits=0
hit_lines=()

record_hit() {
	hits=$((hits + 1))
	if [ "${#hit_lines[@]}" -lt "$MAX_HITS" ]; then
		hit_lines+=("$1")
	fi
}

# Shared denylist patterns (grep -E against relative paths).
# Bytecode (__pycache__) is denied for frozen/wheel/dir but not docker:
# Dockerfiles run compileall on purpose for faster cold start.
#
# Do not use a bare /(^|/)android(/|$)/ pattern: LXST ships
# LXST/Platforms/android for mobile hosts. That path must remain allowed in
# APKs and must not false-fail Docker scans of site-packages.
COMMON_DENY_RE='(^|/)\.git(/|$)|(^|/)node_modules(/|$)|(^|/)\.pnpm-store(/|$)|(^|/)\.venv(/|$)|(^|/)vendor/offline(/|$)|(^|/)vendor/lxmfy/tests(/|$)|(^|/)vendor/lxmfy/docs(/|$)|(^|/)vendor/lxmfy/docker(/|$)|(^|/)\.github(/|$)|(^|/)docs/agents(/|$)|(^|/)screenshots(/|$)|(^|/)\.pytest_cache(/|$)|(^|/)mutants(/|$)|(^|/)coverage(/|$)'

BYTECODE_DENY_RE='(^|/)__pycache__(/|$)'

# MeshChatX Android app sources (gradle/app tree), not LXST.Platforms.android.
ANDROID_APP_DENY_RE='(^|/)android/(app|gradle)(/|$)|(^|/)android/[^/]+\.(gradle|kts|properties)$|(^)android(/|$)'

FROZEN_DENY_RE="${COMMON_DENY_RE}|${BYTECODE_DENY_RE}|(^|/)lib/meshchatx/public(/|$)|(^|/)lib/meshchatx/src/frontend/.+\.vue$|(^|/)lib/meshchatx/src/frontend/.+\.css$|(^|/)lib/setuptools(/|$)|(^|/)lib/pydoc_data(/|$)|(^|/)lib/numpy/.*/tests(/|$)|(^|/)lib/numpy/tests(/|$)"

DOCKER_DENY_RE="${COMMON_DENY_RE}|${ANDROID_APP_DENY_RE}|(^|/)meshchatx/src/frontend/.+\.vue$|(^|/)meshchatx/src/frontend/.+\.css$|(^|/)tests(/|$)|(^|/)electron(/|$)|(^|/)LXST/Platforms/android(/|$)"

WHEEL_DENY_RE="${COMMON_DENY_RE}|${BYTECODE_DENY_RE}|(^|/)meshchatx/src/frontend/.+\.vue$|(^|/)meshchatx/src/frontend/.+\.css$|(^|/)tests(/|$)"

APK_DENY_RE="${COMMON_DENY_RE}|${BYTECODE_DENY_RE}|${ANDROID_APP_DENY_RE}|(^|/)tests(/|$)|(^|/)electron(/|$)|(^|/)\.github(/|$)"

DIR_DENY_RE="${COMMON_DENY_RE}|${BYTECODE_DENY_RE}"

# Read relative paths from stdin. Must not run in a pipe subshell so hits persist.
scan_path_list() {
	deny_re="$1"
	while IFS= read -r rel || [ -n "${rel:-}" ]; do
		[ -n "$rel" ] || continue
		rel="${rel#./}"
		case "$rel" in
		"") continue ;;
		esac
		if printf '%s\n' "$rel" | grep -Eq "$deny_re"; then
			record_hit "$rel"
		fi
	done
}

resolve_frozen_root() {
	base="${1:-}"
	if [ -z "$base" ]; then
		base="$ROOT/build/exe"
	fi
	if [ ! -d "$base" ]; then
		echo "verify-package-contents.sh: frozen root missing: $base" >&2
		exit 1
	fi
	if [ -d "$base/lib" ]; then
		printf '%s\n' "$base"
		return 0
	fi
	for sub in "$base"/*; do
		if [ -d "$sub/lib" ]; then
			printf '%s\n' "$sub"
			return 0
		fi
	done
	echo "verify-package-contents.sh: no lib/ under $base" >&2
	exit 1
}

scan_directory_tree() {
	root="$1"
	deny_re="$2"
	# Process substitution keeps scan_path_list in this shell (hits accumulate).
	scan_path_list "$deny_re" < <(
		CDPATH= cd -- "$root" || exit 1
		find . -print 2>/dev/null | sed 's|^\./||'
	)
}

scan_archive_listing() {
	archive="$1"
	deny_re="$2"
	if command -v unzip >/dev/null 2>&1; then
		scan_path_list "$deny_re" < <(unzip -Z1 "$archive" 2>/dev/null)
		return 0
	fi
	echo "verify-package-contents.sh: unzip required to inspect $archive" >&2
	exit 1
}

scan_frozen() {
	root="$(resolve_frozen_root "${TARGET:-}")"
	echo "verify-package-contents.sh: scanning frozen tree $root"
	scan_directory_tree "$root" "$FROZEN_DENY_RE"
}

scan_dir() {
	root="${TARGET:-}"
	[ -n "$root" ] || usage
	[ -d "$root" ] || {
		echo "verify-package-contents.sh: missing dir $root" >&2
		exit 1
	}
	echo "verify-package-contents.sh: scanning dir $root"
	scan_directory_tree "$root" "$DIR_DENY_RE"
}

scan_wheel() {
	whl="${TARGET:-}"
	if [ -z "$whl" ]; then
		whl="$(ls -1 "$ROOT"/python-dist/*.whl 2>/dev/null | head -n 1 || true)"
	fi
	[ -n "$whl" ] && [ -f "$whl" ] || {
		echo "verify-package-contents.sh: wheel not found" >&2
		exit 1
	}
	echo "verify-package-contents.sh: scanning wheel $whl"
	scan_archive_listing "$whl" "$WHEEL_DENY_RE"
}

scan_apk() {
	apk="${TARGET:-}"
	[ -n "$apk" ] && [ -f "$apk" ] || {
		echo "verify-package-contents.sh: apk not found" >&2
		exit 1
	}
	echo "verify-package-contents.sh: scanning apk $apk"
	scan_archive_listing "$apk" "$APK_DENY_RE"
}

scan_deb() {
	deb="${TARGET:-}"
	[ -n "$deb" ] && [ -f "$deb" ] || {
		echo "verify-package-contents.sh: deb not found" >&2
		exit 1
	}
	tmp="$(mktemp -d "${TMPDIR:-/tmp}/pkg-bloat-deb.XXXXXX")"
	trap 'rm -rf "$tmp"' EXIT INT
	echo "verify-package-contents.sh: extracting deb $deb"
	dpkg-deb -x "$deb" "$tmp"
	scan_directory_tree "$tmp" "$FROZEN_DENY_RE"
}

scan_appimage() {
	ai="${TARGET:-}"
	[ -n "$ai" ] && [ -f "$ai" ] || {
		echo "verify-package-contents.sh: AppImage not found" >&2
		exit 1
	}
	tmp="$(mktemp -d "${TMPDIR:-/tmp}/pkg-bloat-ai.XXXXXX")"
	trap 'rm -rf "$tmp"' EXIT INT
	echo "verify-package-contents.sh: extracting AppImage $ai"
	chmod +x "$ai" || true
	(
		CDPATH= cd -- "$tmp"
		"$ai" --appimage-extract >/dev/null
	)
	scan_directory_tree "$tmp/squashfs-root" "$FROZEN_DENY_RE"
}

scan_docker() {
	image="${TARGET:-}"
	[ -n "$image" ] || {
		echo "verify-package-contents.sh: docker image tag required" >&2
		exit 1
	}
	if ! command -v docker >/dev/null 2>&1; then
		echo "verify-package-contents.sh: docker not available" >&2
		exit 1
	fi
	echo "verify-package-contents.sh: scanning docker image $image (/opt/venv)"
	# Use python (always present) so Alpine and Chainguard/hardened images both work.
	# Emit paths relative to /opt/venv or /app so denylist matches cleanly.
	list="$(
		docker run --rm --user 0 --entrypoint python "$image" -c '
import os
roots = [p for p in ("/opt/venv", "/app") if os.path.isdir(p)]
if not roots:
    roots = ["/"]
skip_top = {"proc", "sys", "dev", "tmp", "run"}
for root in roots:
    for dirpath, dirnames, filenames in os.walk(root):
        if root == "/":
            if dirpath == "/":
                dirnames[:] = [d for d in dirnames if d not in skip_top]
            rel_dir = dirpath.lstrip("/") or "."
        elif dirpath == root:
            rel_dir = "."
        else:
            rel_dir = dirpath[len(root) + 1 :]
        print(rel_dir)
        for name in filenames:
            if rel_dir == ".":
                print(name)
            else:
                print(rel_dir + "/" + name)
' 2>/dev/null || true
	)"
	if [ -z "$list" ]; then
		echo "verify-package-contents.sh: could not list files in $image" >&2
		exit 1
	fi
	scan_path_list "$DOCKER_DENY_RE" <<<"$list"
}

case "$MODE" in
frozen)
	scan_frozen
	;;
dir)
	scan_dir
	;;
wheel)
	scan_wheel
	;;
apk)
	scan_apk
	;;
deb)
	scan_deb
	;;
appimage)
	scan_appimage
	;;
docker)
	scan_docker
	;;
*)
	usage
	;;
esac

if [ "$hits" -gt 0 ]; then
	shown="${#hit_lines[@]}"
	echo "verify-package-contents.sh: FAIL ($hits forbidden path(s), showing $shown)" >&2
	for line in "${hit_lines[@]}"; do
		echo "  - $line" >&2
	done
	exit 1
fi

echo "verify-package-contents.sh: OK ($MODE)"
