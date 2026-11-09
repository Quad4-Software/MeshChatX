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
# shellcheck source=scripts/ci/user-space-pkgs.sh
. "$(dirname "$0")/user-space-pkgs.sh"

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

    # Minimal self-hosted images can ship a trimmed PATH (the runner invokes
    # bash by absolute path so steps still work, but tests that subprocess
    # `bash`/`node` by name fail). Make sure the standard dirs are present.
    for _std_dir in /usr/local/bin /usr/bin /bin; do
        case ":${PATH}:" in
            *":${_std_dir}:"*) ;;
            *) PATH="${PATH}:${_std_dir}" ;;
        esac
    done
    export PATH
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "PATH=${PATH}" >> "$GITHUB_ENV"
    fi

    # If bash still does not resolve (nonstandard layouts), link the first
    # real bash found into ~/.local/bin which is on PATH.
    if ! command -v bash >/dev/null 2>&1; then
        _bash_bin="$(find /bin /usr/bin /usr/local/bin /opt -maxdepth 3 -name bash -type f 2>/dev/null | head -n1)"
        if [[ -n "${_bash_bin}" ]]; then
            mkdir -p "${HOME}/.local/bin"
            ln -sf "${_bash_bin}" "${HOME}/.local/bin/bash"
            export PATH="${HOME}/.local/bin:${PATH}"
            [[ -n "${GITHUB_ENV:-}" ]] && echo "${HOME}/.local/bin" >> "${GITHUB_PATH}"
        fi
    fi

    # GNU make, binutils and pkg-config for source builds (codec2, sdists)
    # on runners with no root. Fetched as Arch packages into $HOME.
    ensure_build_tools() {
        local t missing=0
        for t in make ar ranlib nm objcopy pkg-config; do
            command -v "${t}" >/dev/null 2>&1 || missing=1
        done
        if [[ ${missing} -eq 1 ]]; then
            command -v make >/dev/null 2>&1 || fetch_arch_pkg make || true
            fetch_arch_pkg binutils || true
            command -v pkg-config >/dev/null 2>&1 || fetch_arch_pkg pkgconf || true
            link_syslib_bins
        fi
        for t in make ar ranlib nm objcopy pkg-config; do
            command -v "${t}" >/dev/null 2>&1 || return 1
        done
        return 0
    }

    # pyogg dlopens libogg/libopus (& friends) at runtime; fetch the Arch
    # packages and unpack them into $HOME, then point the dynamic loader
    # at syslibs/usr/lib via LD_LIBRARY_PATH.
    install_user_audio_libs() {
        local dest="$HOME/.local/meshchatx-ci/syslibs"
        [[ -f "${dest}/usr/lib/libopus.so.0" && -f "${dest}/usr/lib/libogg.so.0" ]] && return 0
        local pkg
        for pkg in opus libogg opusfile libvorbis flac speex opus-tools; do
            fetch_arch_pkg "${pkg}" || true
        done
        [[ -f "${dest}/usr/lib/libopus.so.0" && -f "${dest}/usr/lib/libogg.so.0" ]]
    }

    # User-space codec2 for Linux runners that cannot install packages
    # (self-hosted without sudo). Fetches the distro codec2 package into
    # syslibs — it ships libcodec2, headers and codec2.pc — and points the
    # compiler/pkg-config flags at it. Reused across jobs via $HOME.
    provide_user_codec2() {
        local dest="$HOME/.local/meshchatx-ci/syslibs"
        compgen -G "${dest}/usr/lib/libcodec2.so*" >/dev/null \
            && [[ -d "${dest}/usr/include/codec2" ]] && return 0
        fetch_arch_pkg codec2 || return 1
        compgen -G "${dest}/usr/lib/libcodec2.so*" >/dev/null \
            && [[ -d "${dest}/usr/include/codec2" ]]
    }

    # Real GCC toolchain for runners with no system compiler. The Arch
    # gcc package set is extracted into syslibs; GCC_EXEC_PREFIX makes
    # cc1, the cc1 headers and the support libs resolve relative to the
    # extraction root, and LD_LIBRARY_PATH covers the runtime libs
    # (gmp/mpfr/mpc/isl/zlib/zstd, libstdc++/libgcc_s). fetch_arch_pkg
    # only needs curl + the Arch package API, so this works on any glibc
    # Linux self-hosted runner, not just Arch.
    ensure_user_gcc() {
        local dest="$HOME/.local/meshchatx-ci/syslibs"
        local gcclib="${dest}/usr/lib/gcc"
        # The package files persist in $HOME across jobs but GITHUB_ENV
        # does not, so the exports below must run on every invocation.
        if ! compgen -G "${gcclib}/*/*/cc1" >/dev/null 2>&1 \
            || [[ ! -x "${dest}/usr/bin/gcc" ]]; then
            local pkg
            for pkg in gcc "libstdc++" libgcc libgomp libatomic libquadmath \
                gmp libisl libmpc mpfr zlib zstd; do
                fetch_arch_pkg "${pkg}" || return 1
            done
            [[ -x "${dest}/usr/bin/gcc" ]] || return 1
        fi
        compgen -G "${gcclib}/*/*/cc1" >/dev/null 2>&1 \
            && [[ -x "${dest}/usr/bin/gcc" ]] || return 1
        link_syslib_bins
        # GCC_EXEC_PREFIX must end in '/': without it gcc concatenates the
        # target triple onto the prefix and cc1 is never found.
        export GCC_EXEC_PREFIX="${gcclib}/"
        # COMPILER_PATH covers as/ld/cc1 lookups so the user-space
        # binutils from ensure_build_tools resolve even though they are
        # not under GCC_EXEC_PREFIX.
        export COMPILER_PATH="${dest}/usr/bin:${COMPILER_PATH:-}"
        export LD_LIBRARY_PATH="${dest}/usr/lib:${LD_LIBRARY_PATH:-}"
        export LIBRARY_PATH="${dest}/usr/lib:${LIBRARY_PATH:-}"
        # Self-verify with a real compile: partial extractions (e.g. a
        # full disk mid-tar) can leave gcc present but cc1 missing, and
        # env propagation issues only show up at compile time. Fall
        # through to zig when the toolchain cannot actually build.
        if ! printf 'int main(void){return 0;}\n' \
            | "${dest}/usr/bin/gcc" -x c - -o "${TMPDIR:-/tmp}/.meshchatx-cc-test" \
                >/dev/null 2>&1; then
            echo "::warning::user-space gcc failed self-test; falling back to zig"
            return 1
        fi
        rm -f "${TMPDIR:-/tmp}/.meshchatx-cc-test"
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            {
                echo "GCC_EXEC_PREFIX=${GCC_EXEC_PREFIX}"
                echo "COMPILER_PATH=${COMPILER_PATH}"
                echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
                echo "LIBRARY_PATH=${LIBRARY_PATH}"
            } >> "$GITHUB_ENV"
        fi
        return 0
    }

    # Some sdists (miniaudio, pycodec2, numpy) need a C/C++ compiler. Point
    # CC/CXX at whatever exists; on minimal self-hosted runners prefer a
    # real user-space GCC (meson and friends mis-detect zig's bundled
    # clang and its linker rejects GNU thin archives), with zig's clang
    # as the fully portable last resort.
    ensure_cpp() {
        command -v c++ >/dev/null 2>&1 && return 0
        command -v g++ >/dev/null 2>&1 && { export CXX=g++; return 0; }
        command -v clang++ >/dev/null 2>&1 && { export CXX=clang++; return 0; }
        ensure_user_gcc && { export CC=cc CXX=c++; return 0; }
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
        # Pin a gnu target so -dumpmachine and autoconfs report linux-gnu
        # (bare `zig cc` reports musl). Unknown arches fall back to native.
        local ztarget
        case "$(uname -m)" in
            x86_64) ztarget="x86_64-linux-gnu" ;;
            aarch64|arm64) ztarget="aarch64-linux-gnu" ;;
            armv7l) ztarget="arm-linux-gnueabihf" ;;
            *) ztarget="native" ;;
        esac
        # zig's linker rejects a few GNU-ld-only args that CPython's
        # sysconfig LDFLAGS inject into every extension link. Verified
        # unsupported on zig 0.15.2: --exclude-libs, -z separate-code,
        # -z unique. The wrapper drops them; everything else passes through.
        # Meson's linker probe runs 'cc -Wl,--version'; zig answers
        # 'zig ld ...' which trips a broken 'zig ld' branch in some
        # vendored meson releases (numpy 2.1.3 ships meson 1.5.2 whose
        # detect.py calls a nonexistent ZigCCDynamicLinker). zig's ld is
        # lld-derived, so answer LLD for linker probes instead.
        local zig_ver
        zig_ver="$("${zdir}/zig" version 2>/dev/null || echo 0.15.2)"
        for tool in cc c++ gcc g++; do
            case "${tool}" in
                cc|gcc) mode="cc" ;;
                *) mode="c++" ;;
            esac
            cat > "${zdir}/bin/${tool}" <<WRAPPER
#!/usr/bin/env bash
for a in "\$@"; do
    case "\$a" in
        -Wl,--version|-Wl,-v) printf 'LLD ${zig_ver}\\n'; exit 0 ;;
    esac
done
args=()
for a in "\$@"; do
    case "\$a" in
        -Wl,--exclude-libs|-Wl,--exclude-libs,*|-Wl,--exclude-libs=*) ;;
        -Wl,-z,separate-code|-Wl,-z,separate-code=*|-Wl,-z,unique|-Wl,-z,unique=*) ;;
        *) args+=("\$a") ;;
    esac
done
exec "${zdir}/zig" ${mode} -target ${ztarget} "\${args[@]}"
WRAPPER
            chmod +x "${zdir}/bin/${tool}"
        done
        export PATH="${zdir}/bin:${PATH}"
        export CC=cc CXX=c++
        return 0
    }

    if [[ "$(uname -s)" == "Linux" ]]; then
        # Bootstrap the toolchain before codec2/sdist decisions: user-space
        # GNU make/binutils/pkg-config cover minimal self-hosted images and
        # must exist before ensure_cpp's gcc self-test can link.
        if ! ensure_build_tools; then
            echo "::warning::no make/binutils/pkg-config found; source builds may fail"
        fi
        if ! ensure_cpp; then
            echo "::warning::no C++ compiler found; sdist builds may fail"
        fi
        if [[ -n "${GITHUB_ENV:-}" ]]; then
            echo "PATH=${PATH}" >> "$GITHUB_ENV"
            if [ -n "${CC:-}" ]; then echo "CC=${CC}" >> "$GITHUB_ENV"; fi
            if [ -n "${CXX:-}" ]; then echo "CXX=${CXX}" >> "$GITHUB_ENV"; fi
        fi
    fi

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
            if provide_user_codec2; then
                MESHCHATX_LINUX_CODEC2="user"
                _c2p="$HOME/.local/meshchatx-ci/syslibs/usr"
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
        # pyogg needs libogg/libopus at runtime regardless of codec2. When the
        # system package route was unavailable, fetch the shared libs into
        # $HOME and export LD_LIBRARY_PATH for later steps.
        if [[ "${MESHCHATX_LINUX_CODEC2:-}" != "system" ]]; then
            if install_user_audio_libs; then
                export LD_LIBRARY_PATH="${HOME}/.local/meshchatx-ci/syslibs/usr/lib:${LD_LIBRARY_PATH:-}"
                if [[ -n "${GITHUB_ENV:-}" ]]; then
                    echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" >> "$GITHUB_ENV"
                fi
            else
                echo "::warning::could not provide libogg/libopus; Opus audio tests may fail"
            fi
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
    . scripts/ci/ensure-pnpm-store.sh
    pnpm install --frozen-lockfile
fi

if [[ "$INSTALL_PYTHON" != "true" && "$INSTALL_NODE" != "true" ]]; then
    echo "github-install-deps.sh: nothing to install (both MESHCHATX_INSTALL_PYTHON and MESHCHATX_INSTALL_NODE are false)" >&2
    exit 1
fi
