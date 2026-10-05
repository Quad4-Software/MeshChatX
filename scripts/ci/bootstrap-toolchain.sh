#!/usr/bin/env bash
# Verify or install pinned CI toolchain without GitHub Actions.
#
# Usage:
#   bash scripts/ci/bootstrap-toolchain.sh verify
#   bash scripts/ci/bootstrap-toolchain.sh install
set -euo pipefail

. "$(dirname "$0")/env.sh"
. "$ROOT/scripts/ci/versions.env"

mode="${1:-${CI_BOOTSTRAP:-verify}}"

toolchain="${CI_TOOLCHAIN_ROOT:-$ROOT/.cache/ci-toolchain}"
bindir="$toolchain/bin"
gopath="$toolchain/gopath"

export PATH="$bindir:$PATH"
export GOPATH="$gopath"
export GOCACHE="${GOCACHE:-$toolchain/gocache}"

go_want="${GO_VERSION:-1.27.1}"
node_want="${NODE_VERSION}"
pnpm_want="${PNPM_VERSION}"
task_want="${TASK_VERSION}"
uv_want="${UV_VERSION}"
py_want="${PYTHON_VERSION}"

semver_ge() {
	awk -v a="$1" -v b="$2" 'BEGIN {
		split(a, A, "."); split(b, B, ".")
		for (i = 1; i <= 3; i++) {
			ai = A[i] + 0; bi = B[i] + 0
			if (ai > bi) exit 0
			if (ai < bi) exit 1
		}
		exit 0
	}'
}

have_go() {
	command -v go >/dev/null 2>&1 || return 1
	local v
	v="$(go env GOVERSION 2>/dev/null | sed 's/^go//')"
	semver_ge "$v" "$go_want"
}

have_node() {
	command -v node >/dev/null 2>&1 || return 1
	local v
	v="$(node -p "process.versions.node" 2>/dev/null)"
	semver_ge "$v" "$node_want"
}

have_pnpm() {
	command -v pnpm >/dev/null 2>&1 || return 1
	local v
	v="$(pnpm --version 2>/dev/null | tr -d 'v')"
	semver_ge "$v" "$pnpm_want"
}

have_task() {
	command -v task >/dev/null 2>&1 || return 1
	local v
	v="$(task --version 2>/dev/null | awk '{print $NF}' | tr -d 'v')"
	semver_ge "$v" "$task_want"
}

have_uv() {
	command -v uv >/dev/null 2>&1 || return 1
	local v
	v="$(uv --version 2>/dev/null | awk '{print $2}')"
	semver_ge "$v" "$uv_want"
}

verify_all() {
	local ok=1
	have_uv || { echo "bootstrap-toolchain: need uv >= $uv_want on PATH" >&2; ok=0; }
	have_node || { echo "bootstrap-toolchain: need Node >= $node_want on PATH" >&2; ok=0; }
	have_pnpm || { echo "bootstrap-toolchain: need pnpm >= $pnpm_want on PATH" >&2; ok=0; }
	have_task || { echo "bootstrap-toolchain: need Task >= $task_want on PATH" >&2; ok=0; }
	[ "$ok" -eq 1 ]
}

linux_arch() {
	local m
	m="$(uname -m)"
	case "$m" in
	x86_64) echo amd64 ;;
	aarch64 | arm64) echo arm64 ;;
	*) echo "bootstrap-toolchain: unsupported cpu: $m" >&2; exit 1 ;;
	esac
}

node_linux_arch() {
	local arch
	arch="$(linux_arch)"
	case "$arch" in
	amd64) echo x64 ;;
	arm64) echo arm64 ;;
	*) echo "$arch" ;;
	esac
}

fetch() {
	local url="$1" dest="$2"
	if command -v curl >/dev/null 2>&1; then
		curl -fsSL "$url" -o "$dest"
	elif command -v wget >/dev/null 2>&1; then
		wget -qO "$dest" "$url"
	else
		echo "bootstrap-toolchain: need curl or wget" >&2
		exit 1
	fi
}

install_uv() {
	if have_uv; then
		return 0
	fi
	local arch uv_tgz
	arch="$(uname -m)"
	case "$arch" in
	x86_64) uv_arch=x86_64 ;;
	aarch64 | arm64) uv_arch=aarch64 ;;
	*) echo "bootstrap-toolchain: unsupported arch for uv: $arch" >&2; exit 1 ;;
	esac
	uv_tgz="uv-${uv_arch}-unknown-linux-gnu.tar.gz"
	mkdir -p "$bindir"
	tmp="$(mktemp "${TMPDIR:-/tmp}/uv-bootstrap.XXXXXX")"
	fetch "https://github.com/astral-sh/uv/releases/download/${uv_want}/${uv_tgz}" "$tmp"
	tar -xzf "$tmp" -C "$bindir" --strip-components=1
	rm -f "$tmp"
	export PATH="$bindir:$PATH"
}

install_go() {
	if have_go; then
		return 0
	fi
	local arch go_tgz
	arch="$(linux_arch)"
	go_tgz="go${go_want}.linux-${arch}.tar.gz"
	mkdir -p "$toolchain"
	tmp="$(mktemp "${TMPDIR:-/tmp}/go-bootstrap.XXXXXX")"
	fetch "https://go.dev/dl/${go_tgz}" "$tmp"
	rm -rf "$toolchain/go"
	tar -C "$toolchain" -xzf "$tmp"
	rm -f "$tmp"
	ln -sf "$toolchain/go/bin/go" "$bindir/go"
	export PATH="$bindir:$PATH"
}

install_node() {
	if have_node && have_pnpm; then
		return 0
	fi
	local arch node_tgz
	arch="$(node_linux_arch)"
	node_tgz="node-v${node_want}-linux-${arch}.tar.xz"
	mkdir -p "$toolchain"
	tmp="$(mktemp "${TMPDIR:-/tmp}/node-bootstrap.XXXXXX")"
	fetch "https://nodejs.org/dist/v${node_want}/${node_tgz}" "$tmp"
	rm -rf "$toolchain/node"
	mkdir -p "$toolchain/node"
	tar -C "$toolchain/node" --strip-components=1 -xJf "$tmp"
	rm -f "$tmp"
	ln -sf "$toolchain/node/bin/node" "$bindir/node"
	ln -sf "$toolchain/node/bin/npm" "$bindir/npm"
	export PATH="$bindir:$PATH"
	if ! have_pnpm; then
		npm config set prefix "$toolchain/node"
		npm install -g "pnpm@${pnpm_want}"
		ln -sf "$toolchain/node/bin/pnpm" "$bindir/pnpm" 2>/dev/null || true
	fi
}

install_task() {
	if have_task; then
		return 0
	fi
	if have_go; then
		GOFLAGS= GOBIN="$bindir" go install "github.com/go-task/task/v3/cmd/task@v${task_want}"
		export PATH="$bindir:$PATH"
		return 0
	fi
	install_go
	GOFLAGS= GOBIN="$bindir" go install "github.com/go-task/task/v3/cmd/task@v${task_want}"
	export PATH="$bindir:$PATH"
}

install_python() {
	install_uv
	uv python install "$py_want"
}

install_all() {
	mkdir -p "$bindir" "$gopath" "$GOCACHE"
	install_uv
	install_python
	install_node
	install_task
	verify_all
	echo "bootstrap-toolchain: ready under $toolchain"
}

case "$mode" in
verify)
	verify_all
	echo "bootstrap-toolchain: verify OK"
	;;
install)
	install_all
	;;
*)
	echo "bootstrap-toolchain: usage: bootstrap-toolchain.sh verify|install" >&2
	exit 2
	;;
esac
