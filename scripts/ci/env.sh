# Shared portable CI environment. Source from run.sh or setup.sh.
_ci_script_dir="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(CDPATH= cd -- "${_ci_script_dir}/../.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/scripts/ci/versions.env" ]; then
	# shellcheck disable=SC1091
	. "$ROOT/scripts/ci/versions.env"
fi

export PNPM_CONFIG_STRICT_DEP_BUILDS="${PNPM_CONFIG_STRICT_DEP_BUILDS:-false}"
export RNS_REQUIRED_SIGNER="${RNS_REQUIRED_SIGNER:-e46112d44649266d71fe2193e00a4710}"
export UV_PYTHON="${UV_PYTHON:-python${PYTHON_VERSION:-3.14}}"

_ci_toolchain="${CI_TOOLCHAIN_ROOT:-$ROOT/.cache/ci-toolchain}"
if [ -d "$_ci_toolchain/bin" ]; then
	export PATH="$_ci_toolchain/bin:$_ci_toolchain/go/bin:$_ci_toolchain/node/bin:$PATH"
	export GOPATH="${GOPATH:-$_ci_toolchain/gopath}"
	export GOCACHE="${GOCACHE:-$_ci_toolchain/gocache}"
fi

ci_truthy() {
	case "${1:-}" in
	1 | true | TRUE | yes | YES) return 0 ;;
	esac
	return 1
}

ci_on_linux() {
	[ "$(uname -s)" = "Linux" ]
}

require_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		echo "ci: need $1 on PATH" >&2
		exit 1
	fi
}

require_task() {
	require_cmd task
}

verify_workspace_clean() {
	if [ -z "${RNS_INVENTORY_OUT:-}" ] || [ ! -f "$RNS_INVENTORY_OUT" ]; then
		return 0
	fi
	export RNS_CLEAN_SOFT="${RNS_CLEAN_SOFT:-1}"
	sh "$ROOT/scripts/ci/verify-workspace-clean.sh" "$RNS_INVENTORY_OUT"
}
