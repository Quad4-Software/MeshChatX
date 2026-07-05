#!/usr/bin/env bash
# Normalize the installed pycodec2 package's bundled libcodec2 into a fixed,
# arch-independent relative layout:
#
#   pycodec2/pycodec2*.so       (extension module; @loader_path/libcodec2.dylib)
#   pycodec2/libcodec2.dylib    (single canonical name, no .dylibs/ subfolder)
#
# Published macOS wheels bundle libcodec2 under pycodec2/.dylibs/libcodec2.<ver>.dylib
# (delocate convention). Building pycodec2 from sdist for architectures without a
# published wheel (e.g. cp314 macOS x86_64) instead links against whatever Homebrew
# codec2 path was on LDFLAGS at build time. Without normalization the two cx_Freeze
# build trees (darwin-arm64 vs darwin-x64) have different relative file layouts for
# the same logical dependency, so scripts/unify-backend-plain-files.sh treats the
# bundled dylib as arch-only and drops it from BOTH trees, breaking Codec2 audio
# (voice messages) in the shipped universal macOS app.
#
# Usage: macos-normalize-pycodec2-dylib.sh <python-executable>
set -euo pipefail

PY="${1:?usage: macos-normalize-pycodec2-dylib.sh <python-executable>}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macos-normalize-pycodec2-dylib: skipping (not macOS)" >&2
    exit 0
fi

_site_dir="$("$PY" -c 'import pycodec2, pathlib; print(pathlib.Path(pycodec2.__file__).resolve().parent)' 2>/dev/null || true)"
if [[ -z "$_site_dir" || ! -d "$_site_dir" ]]; then
    echo "macos-normalize-pycodec2-dylib: pycodec2 not installed, skipping" >&2
    exit 0
fi

_ext_so="$(find "$_site_dir" -maxdepth 1 -name 'pycodec2*.so' -print -quit)"
if [[ -z "$_ext_so" ]]; then
    echo "macos-normalize-pycodec2-dylib: no pycodec2 extension module found under ${_site_dir}, skipping" >&2
    exit 0
fi

_target="${_site_dir}/libcodec2.dylib"
_dylibs_dir="${_site_dir}/.dylibs"
_src_dylib=""

if [[ -d "$_dylibs_dir" ]]; then
    _src_dylib="$(find "$_dylibs_dir" -maxdepth 1 -name 'libcodec2*.dylib' -print -quit)"
fi
if [[ -z "$_src_dylib" ]]; then
    for _candidate in "${_site_dir}/libcodec2.dylib" "${_site_dir}/libcodec2.so"; do
        if [[ -f "$_candidate" ]]; then
            _src_dylib="$_candidate"
            break
        fi
    done
fi

if [[ -z "$_src_dylib" ]]; then
    echo "macos-normalize-pycodec2-dylib: no bundled libcodec2 found under ${_site_dir}, skipping" >&2
    exit 0
fi

if [[ "$_src_dylib" != "$_target" ]]; then
    cp -f "$_src_dylib" "$_target"
fi
if [[ -d "$_dylibs_dir" ]]; then
    rm -rf "$_dylibs_dir"
fi
if [[ -f "${_site_dir}/libcodec2.so" && "${_site_dir}/libcodec2.so" != "$_target" ]]; then
    rm -f "${_site_dir}/libcodec2.so"
fi

_old_ref="$( (otool -L "$_ext_so" | awk '/libcodec2/{print $1; exit}') 2>/dev/null || true)"
if [[ -n "$_old_ref" && "$_old_ref" != "@loader_path/libcodec2.dylib" ]]; then
    install_name_tool -change "$_old_ref" "@loader_path/libcodec2.dylib" "$_ext_so"
    codesign --force --sign - "$_ext_so" >/dev/null 2>&1 || true
    echo "macos-normalize-pycodec2-dylib: rewrote ${_old_ref} -> @loader_path/libcodec2.dylib in $(basename "$_ext_so")"
fi

echo "macos-normalize-pycodec2-dylib: normalized $(basename "$_ext_so") + libcodec2.dylib under ${_site_dir}"
