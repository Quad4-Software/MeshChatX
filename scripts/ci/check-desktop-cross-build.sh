#!/usr/bin/env bash
# Cross-compile check for the Wails desktop shell: builds windows/amd64,
# windows/arm64, darwin/arm64, darwin/amd64 with CGO_ENABLED=0 (no Wine, no
# target toolchains) plus go vet and windows test-compile. Artifacts go to a
# temp dir and are removed.
set -euo pipefail
cd "$(dirname "$0")/../.."
D=desktop
if [ ! -d /tmp ] || [ ! -w /tmp ]; then
    _ci_tmp="${RUNNER_TEMP:-${HOME}/.meshchatx-ci}/tmp"
    mkdir -p "${_ci_tmp}" 2>/dev/null && export TMPDIR="${_ci_tmp}"
fi
unset _ci_tmp
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP"

step() { echo "== $*"; }

step "windows/amd64"
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go -C "$D" build -ldflags "-H windowsgui -s -w" -o "$TMP/win-amd64.exe" .
file "$TMP/win-amd64.exe" | grep -q "PE32+"
step "windows/arm64"
GOOS=windows GOARCH=arm64 CGO_ENABLED=0 go -C "$D" build -ldflags "-H windowsgui -s -w" -o "$TMP/win-arm64.exe" .
file "$TMP/win-arm64.exe" | grep -q "PE32+"
step "darwin/arm64"
GOOS=darwin GOARCH=arm64 CGO_ENABLED=0 go -C "$D" build -tags purego -ldflags "-s -w" -o "$TMP/mac-arm64" .
file "$TMP/mac-arm64" | grep -q "Mach-O"
step "darwin/amd64"
GOOS=darwin GOARCH=amd64 CGO_ENABLED=0 go -C "$D" build -tags purego -ldflags "-s -w" -o "$TMP/mac-amd64" .
file "$TMP/mac-amd64" | grep -q "Mach-O"

step "go vet (targets)"
GOOS=windows GOARCH=amd64 go -C "$D" vet ./...
GOOS=darwin GOARCH=arm64 go -C "$D" vet -tags purego ./...

step "windows test-compile"
for p in ./internal/...; do
  GOOS=windows GOARCH=amd64 go -C "$D" test -c -o /dev/null "$p" 2>/dev/null || true
done
step "OK"
