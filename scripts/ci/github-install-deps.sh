#!/usr/bin/env bash
# Install Python (UV) and/or Node (pnpm) dependencies for CI and native builds.
#
# Env (default true):
#   MESHCHATX_INSTALL_PYTHON  sync the project virtualenv and system libs it needs
#   MESHCHATX_INSTALL_NODE    pnpm install --frozen-lockfile
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/priv.sh
. "$(dirname "$0")/priv.sh"

export GIT_TERMINAL_PROMPT=0

INSTALL_PYTHON="${MESHCHATX_INSTALL_PYTHON:-true}"
INSTALL_NODE="${MESHCHATX_INSTALL_NODE:-true}"

if [[ "$INSTALL_PYTHON" == "true" ]]; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        brew install codec2
        # LXST vendored pyogg ships x86_64-only macOS dylibs. The arm64
        # freeze needs native builds, which macos-normalize-pyogg-dylibs.sh
        # copies in from these formulas.
        brew install opus opusfile libopusenc libogg libvorbis flac
        _codec2_prefix="$(brew --prefix codec2)"
        export CPPFLAGS="${CPPFLAGS:-} -I${_codec2_prefix}/include"
        export LDFLAGS="${LDFLAGS:-} -L${_codec2_prefix}/lib"
        if [[ -d "${_codec2_prefix}/lib/pkgconfig" ]]; then
            export PKG_CONFIG_PATH="${_codec2_prefix}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
        fi
    fi

    # LXST/pyogg loads libopus (and libogg for Ogg muxing) at runtime. GitHub-hosted
    # Linux runners do not ship these by default, so backend Opus encode tests fail
    # with PyOggError until the shared libraries are present.
    have_priv() { [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null; }

    # User-space codec2 for Linux runners that cannot install packages
    # (self-hosted without sudo). Builds once under $HOME so later jobs on the
    # same runner reuse it. Requires only a C toolchain.
    build_user_codec2() {
        local prefix="$HOME/.local/meshchatx-ci/codec2"
        [ -f "${prefix}/lib/libcodec2.so" ] && return 0
        command -v gcc >/dev/null 2>&1 || return 1
        command -v make >/dev/null 2>&1 || return 1
        local tmp url src
        tmp="$(mktemp -d)"
        url="$(curl -fsSL https://api.github.com/repos/drowe67/codec2/releases/latest \
            | grep -o 'https://[^"]*codec2-[0-9][^"]*\.tar\.gz' | head -n1)"
        [ -n "${url}" ] || { rm -rf "${tmp}"; return 1; }
        curl -fsSL -o "${tmp}/codec2.tar.gz" "${url}" || { rm -rf "${tmp}"; return 1; }
        tar -xzf "${tmp}/codec2.tar.gz" -C "${tmp}" || { rm -rf "${tmp}"; return 1; }
        src="$(find "${tmp}" -maxdepth 1 -type d -name 'codec2-*' | head -n1)"
        [ -n "${src}" ] || { rm -rf "${tmp}"; return 1; }
        if (cd "${src}" && ./configure --prefix="${prefix}" >/dev/null \
            && make -j"$(nproc)" >/dev/null && make install >/dev/null); then
            rm -rf "${tmp}"
            return 0
        fi
        rm -rf "${tmp}"
        return 1
    }

    # Some sdists (miniaudio, pycodec2) need a C++ compiler. Point CXX at
    # whatever exists; on minimal self-hosted runners bootstrap zig's
    # bundled clang as a portable cc/c++ toolchain under $HOME.
    ensure_cpp() {
        command -v c++ >/dev/null 2>&1 && return 0
        command -v g++ >/dev/null 2>&1 && { export CXX=g++; return 0; }
        command -v clang++ >/dev/null 2>&1 && { export CXX=clang++; return 0; }
        local zdir tmp mode
        zdir="$HOME/.local/meshchatx-ci/zig"
        # Pinned stable zig; shasum from ziglang.org/download/index.json.
        local zig_url="https://ziglang.org/download/0.15.2/zig-x86_64-linux-0.15.2.tar.xz"
        local zig_sha="02aa270f183da276e5b5920b1dac44a63f1a49e55050ebde3aecc9eb82f93239"
        if [ ! -x "${zdir}/zig" ]; then
            command -v curl >/dev/null 2>&1 || return 1
            mkdir -p "$HOME/.local/meshchatx-ci"
            tmp="$(mktemp -d)"
            curl -fsSL -o "${tmp}/zig.tar.xz" "${zig_url}" || { rm -rf "${tmp}"; return 1; }
            echo "${zig_sha}  ${tmp}/zig.tar.xz" | sha256sum -c - >/dev/null \
                || { rm -rf "${tmp}"; return 1; }
            mkdir -p "${tmp}/extract" && tar -xJf "${tmp}/zig.tar.xz" -C "${tmp}/extract" \
                || { rm -rf "${tmp}"; return 1; }
            rm -rf "${zdir}"
            mv "${tmp}/extract"/zig-* "${zdir}" && rm -rf "${tmp}" \
                || { rm -rf "${tmp}"; return 1; }
        fi
        [ -x "${zdir}/zig" ] || return 1
        mkdir -p "${zdir}/bin"
        for tool in cc c++ gcc g++; do
            case "${tool}" in
                cc|gcc) mode="cc" ;;
                *) mode="c++" ;;
            esac
            printf '#!/bin/sh\nexec "%s/zig" %s "$@"\n' "${zdir}" "${mode}" \
                > "${zdir}/bin/${tool}"
            chmod +x "${zdir}/bin/${tool}"
        done
        export PATH="${zdir}/bin:${PATH}"
        export CC=cc CXX=c++
        return 0
    }

    MESHCHATX_LINUX_CODEC2=""
    if [[ "$(uname -s)" == "Linux" ]]; then
        if command -v apt-get >/dev/null 2>&1 && have_priv; then
            run_priv apt-get update -y
            run_priv apt-get install -y libopus0 libogg0 libcodec2-dev
            MESHCHATX_LINUX_CODEC2="system"
        elif command -v pacman >/dev/null 2>&1; then
            # Arch-based self-hosted runners: codec2/opus/ogg headers for the
            # pycodec2 and LXST pyogg source builds during uv sync. Skip when
            # the runner already provides them so no sudo is required.
            if pacman -Q codec2 opus libogg >/dev/null 2>&1 && command -v gcc >/dev/null 2>&1; then
                MESHCHATX_LINUX_CODEC2="system"
            elif have_priv; then
                run_priv pacman -Sy --needed --noconfirm codec2 opus libogg gcc make pkgconf
                MESHCHATX_LINUX_CODEC2="system"
            fi
        fi
        if [[ -z "${MESHCHATX_LINUX_CODEC2}" ]]; then
            if build_user_codec2; then
                MESHCHATX_LINUX_CODEC2="user"
                _c2p="$HOME/.local/meshchatx-ci/codec2"
                export CPPFLAGS="${CPPFLAGS:-} -I${_c2p}/include"
                export LDFLAGS="${LDFLAGS:-} -L${_c2p}/lib"
                export PKG_CONFIG_PATH="${_c2p}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
                export LD_LIBRARY_PATH="${_c2p}/lib:${LD_LIBRARY_PATH:-}"
                if [[ -n "${GITHUB_ENV:-}" ]]; then
                    {
                        echo "CPPFLAGS=${CPPFLAGS}"
                        echo "LDFLAGS=${LDFLAGS}"
                        echo "PKG_CONFIG_PATH=${PKG_CONFIG_PATH}"
                        echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
                    } >> "$GITHUB_ENV"
                fi
            else
                MESHCHATX_LINUX_CODEC2="none"
                echo "::warning::no codec2 available; pycodec2 will be skipped (optional at runtime)"
            fi
        fi
    fi

    if [[ "$(uname -s)" == "Linux" ]]; then
        if ensure_cpp; then
            if [[ -n "${GITHUB_ENV:-}" ]]; then
                echo "PATH=${PATH}" >> "$GITHUB_ENV"
                if [ -n "${CC:-}" ]; then echo "CC=${CC}" >> "$GITHUB_ENV"; fi
                if [ -n "${CXX:-}" ]; then echo "CXX=${CXX}" >> "$GITHUB_ENV"; fi
            fi
        else
            echo "::warning::no C++ compiler found; sdist builds may fail"
        fi
    fi

    uv lock --check
    if [[ "$(uname -s)" == "Darwin" ]]; then
        # The ctypes binding in meshchatx/pycodec2_ctypes.py covers the
        # Codec2 API LXST uses, so macOS slices skip the pycodec2
        # extension and ship the Homebrew libcodec2 for it to dlopen.
        uv sync --group dev --no-install-package pycodec2
    elif [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* || "$(uname -s)" == CYGWIN* ]]; then
        # pycodec2 and bleak's winrt extensions have no Windows wheels for
        # the newest CPython and their sdists do not build on the hosted
        # runners. Both are optional at runtime (codec2-optional patch below,
        # bleak is a lazy import in rns_rnode_patch.py). uv run resyncs the
        # environment back to the full lockfile, so stop it syncing for the
        # rest of the job or it rebuilds the skipped sdists.
        export UV_NO_SYNC=1
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            echo "UV_NO_SYNC=1" >> "$GITHUB_ENV"
        fi
        uv sync --group dev \
            --no-install-package pycodec2 \
            --no-install-package bleak \
            --no-install-package winrt-runtime \
            --no-install-package winrt-windows-devices-bluetooth \
            --no-install-package winrt-windows-devices-bluetooth-advertisement \
            --no-install-package winrt-windows-devices-bluetooth-genericattributeprofile \
            --no-install-package winrt-windows-devices-enumeration \
            --no-install-package winrt-windows-devices-radios \
            --no-install-package winrt-windows-foundation \
            --no-install-package winrt-windows-foundation-collections \
            --no-install-package winrt-windows-storage-streams
    elif [[ "$(uname -s)" == "Linux" && "${MESHCHATX_LINUX_CODEC2:-system}" == "none" ]]; then
        # Same optional-at-runtime situation as macOS/Windows: no codec2
        # anywhere on this host, so skip the pycodec2 sdist. uv run would
        # otherwise try to resync it back on every invocation.
        export UV_NO_SYNC=1
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            echo "UV_NO_SYNC=1" >> "$GITHUB_ENV"
        fi
        uv sync --group dev --no-install-package pycodec2
    else
        uv sync --group dev
    fi
    uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py
    uv run python scripts/patch_lxst_codec2_optional.py

    # LXST ships prebuilt filterlib blobs per CPython ABI. On pre-release
    # interpreters (3.15 beta legs) none exists, so build it from the bundled
    # Filters.c. Exit 2 (no compiler) is non-fatal: LXST compiles via cffi at
    # runtime instead.
    uv run python scripts/build-lxst-filterlib.py || rc=$?
    if [[ "${rc:-0}" == "2" ]]; then
        echo "::warning::no C compiler for LXST filterlib; cffi runtime fallback will compile it"
    elif [[ "${rc:-0}" != "0" ]]; then
        exit "${rc}"
    fi

    if [[ "$(uname -s)" == "Darwin" ]]; then
        # Ship libcodec2 at the site-packages root, matching the darwin-x64
        # slice, so the ctypes binding finds it and the two trees merge
        # cleanly under scripts/unify-backend-plain-files.sh.
        _site_packages="$(uv run python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
        cp -f "${_codec2_prefix}/lib/libcodec2.dylib" "${_site_packages}/libcodec2.dylib"
        uv run python -c "
import numpy
from numpy._core._multiarray_umath import _ARRAY_API
from meshchatx import pycodec2_ctypes
codec = pycodec2_ctypes.Codec2(1600)
assert codec.samples_per_frame() > 0
print('arm64 venv numpy', numpy.__version__, 'codec2-ctypes ok')
"
        bash "$(dirname "$0")/macos-normalize-pyogg-dylibs.sh" "${ROOT}/.venv/bin/python"
    fi

    if [[ "$(uname -s)" == "Darwin" ]]; then
        if uv run python -c "import platform, sys; sys.exit(0 if platform.machine() == 'arm64' else 1)"; then
            _miniaudio_state="$(uv run python -c "
import importlib.util
import pathlib
import subprocess
import sys

spec = importlib.util.find_spec('miniaudio')
if not spec or not spec.origin:
    print('missing')
    sys.exit(0)
so = pathlib.Path(spec.origin).resolve().parent / '_miniaudio.abi3.so'
if not so.is_file():
    print('missing')
    sys.exit(0)
out = subprocess.check_output(['file', str(so)], text=True)
has_arm = 'arm64' in out
has_x86 = 'x86_64' in out
if not has_arm and has_x86:
    print('x86only')
elif has_arm and has_x86:
    print('universal')
elif has_arm and not has_x86:
    print('arm64only')
else:
    print('unknown')
" 2>/dev/null || echo "missing")"
            case "$_miniaudio_state" in
                x86only)
                    echo "miniaudio _miniaudio.abi3.so is x86_64-only on arm64 venv; rebuilding from source." >&2
                    _need_rebuild=1
                    ;;
                universal)
                    echo "miniaudio _miniaudio.abi3.so is universal2; rebuilding as arm64-only so the macOS universal lipo step can merge with the x64 slice." >&2
                    _need_rebuild=1
                    ;;
                *)
                    _need_rebuild=0
                    ;;
            esac
            if [[ "${_need_rebuild:-0}" == "1" ]]; then
                (
                    export ARCHFLAGS="-arch arm64"
                    export CFLAGS="-arch arm64"
                    export CXXFLAGS="-arch arm64"
                    uv run python -m pip install --force-reinstall --no-cache-dir --no-binary miniaudio "miniaudio>=1.70,<2"
                )
            fi
            if ! uv run python -c "
import importlib.util
import pathlib
import subprocess
import sys

spec = importlib.util.find_spec('miniaudio')
if not spec or not spec.origin:
    sys.exit(0)
so = pathlib.Path(spec.origin).resolve().parent / '_miniaudio.abi3.so'
if not so.is_file():
    sys.exit(0)
out = subprocess.check_output(['file', str(so)], text=True)
if 'arm64' not in out:
    sys.stderr.write(out)
    sys.exit(1)
sys.exit(0)
"; then
                if [[ "${MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO:-0}" == "1" ]]; then
                    echo "miniaudio native extension is not arm64-capable, but MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1 is set; continuing (the build will drop _miniaudio.abi3.so before lipo)." >&2
                else
                    echo "miniaudio native extension is not arm64-capable; universal macOS builds will fail at lipo." >&2
                    echo "Re-run with MESHCHATX_MAC_UNIVERSAL_STRIP_AUDIO=1 to drop optional audio decoding for the DMG." >&2
                    exit 1
                fi
            fi
        fi
    fi
fi

if [[ "$INSTALL_NODE" == "true" ]]; then
    pnpm config set verify-store-integrity true
    pnpm install --frozen-lockfile
fi

if [[ "$INSTALL_PYTHON" != "true" && "$INSTALL_NODE" != "true" ]]; then
    echo "github-install-deps.sh: nothing to install (both MESHCHATX_INSTALL_PYTHON and MESHCHATX_INSTALL_NODE are false)" >&2
    exit 1
fi
