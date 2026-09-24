#!/usr/bin/env bash
# Replace the x86_64-only pyogg dylibs vendored inside LXST with builds that
# match the interpreter architecture, and bundle their package-manager
# dependencies next to them.
#
# LXST vendors a pyogg copy whose libs/macos/*.dylib are x86_64-only. On
# Apple Silicon they fail to dlopen, so the frozen arm64 backend shipped
# with no working Opus codec: calls connected but carried no audio. The
# vendored set is correct for the darwin-x64 slice, so this script only
# rewrites dylibs that lack the target arch. Replaced dylibs get
# @loader_path ids and their Homebrew/MacPorts dependencies are copied in
# and rewritten the same way, so the directory is self-contained.
#
# Usage: macos-normalize-pyogg-dylibs.sh <python-executable>
set -euo pipefail

PY="${1:?usage: macos-normalize-pyogg-dylibs.sh <python-executable>}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macos-normalize-pyogg-dylibs: skipping (not macOS)" >&2
    exit 0
fi

_target_arch="$("$PY" -c 'import platform; print(platform.machine())')"
case "$_target_arch" in
arm64 | x86_64) ;;
*)
    echo "macos-normalize-pyogg-dylibs: unsupported arch ${_target_arch}" >&2
    exit 1
    ;;
esac

_pyogg_libs="$("$PY" -c '
import importlib.metadata
from pathlib import Path
try:
    dist = importlib.metadata.distribution("lxst")
except importlib.metadata.PackageNotFoundError:
    raise SystemExit(0)
for rel in dist.files or ():
    if tuple(rel.parts) == ("LXST", "__init__.py"):
        root = Path(dist.locate_file(rel)).parent
        print(root / "Codecs" / "libs" / "pyogg" / "libs" / "macos")
        break
')"

if [[ -z "${_pyogg_libs}" || ! -d "${_pyogg_libs}" ]]; then
    echo "macos-normalize-pyogg-dylibs: LXST pyogg libs/macos not found, skipping" >&2
    exit 0
fi

_has_arch() {
    local ft
    ft=$(file --brief --no-pad "$1" 2>/dev/null || true)
    [[ "$ft" == Mach-O* && "$ft" == *"$_target_arch"* ]]
}

_formula_for() {
    case "$1" in
    libopusfile*.dylib) echo opusfile ;;
    libopusenc*.dylib) echo libopusenc ;;
    libopus*.dylib) echo opus ;;
    libogg*.dylib) echo libogg ;;
    libvorbis*.dylib) echo libvorbis ;;
    libFLAC*.dylib) echo flac ;;
    *) return 1 ;;
    esac
}

# Package-manager prefixes whose dylibs may be bundled in. Homebrew arm64
# and Intel prefixes plus the MacPorts prefix used by the x86_64 runner.
# Overridable for tests.
_managed_roots="${MESHCHATX_PYOGG_LIB_ROOTS:-/opt/homebrew /usr/local /opt/local}"

# Locate a native-arch build of the named dylib: the Homebrew formula lib
# dir first, then each managed prefix's shared lib dir (which covers both
# brew-linked and MacPorts-installed copies).
_find_native() {
    local name="$1" formula prefix root candidate
    formula="$(_formula_for "$name")" || return 1
    if command -v brew >/dev/null 2>&1; then
        prefix="$(brew --prefix "$formula" 2>/dev/null || true)"
        if [[ -n "$prefix" && -d "$prefix/lib" ]]; then
            if [[ -f "$prefix/lib/$name" ]]; then
                echo "$prefix/lib/$name"
                return 0
            fi
            candidate="$(find "$prefix/lib" -maxdepth 1 -name "${name%%.*}.*.dylib" | sort | head -n1)"
            if [[ -n "$candidate" ]]; then
                echo "$candidate"
                return 0
            fi
        fi
    fi
    for root in ${_managed_roots}; do
        if [[ -f "${root}/lib/${name}" ]]; then
            echo "${root}/lib/${name}"
            return 0
        fi
        candidate="$(find "${root}/lib" -maxdepth 1 -name "${name%%.*}.*.dylib" 2>/dev/null | sort | head -n1)"
        if [[ -n "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# Dependency refs reported by otool that live under a package-manager prefix.
_dep_refs() {
    otool -L "$1" 2>/dev/null | awk 'NR > 1 { print $1 }'
}

_is_managed_ref() {
    local root
    for root in ${_managed_roots}; do
        case "$1" in
        "${root}"/*) return 0 ;;
        esac
    done
    return 1
}

_copy_deref() {
    # cp -L resolves symlinks so versioned soname links land as real files.
    cp -fL "$1" "$2"
    chmod u+w "$2" 2>/dev/null || true
}

replaced=0
kept=0

# Pass 1: replace vendored dylibs that lack the target arch.
for vendored in "${_pyogg_libs}"/*.dylib; do
    [[ -e "$vendored" ]] || continue
    name="$(basename "$vendored")"
    if _has_arch "$vendored"; then
        kept=$((kept + 1))
        continue
    fi
    src="$(_find_native "$name" || true)"
    if [[ -z "$src" ]]; then
        echo "macos-normalize-pyogg-dylibs: no ${_target_arch} build found for $name" >&2
        echo "  vendored file is wrong-arch and neither Homebrew nor MacPorts provide it." >&2
        echo "  Install the matching formula/port (brew opus / port libopus, opusfile, libopusenc, libogg, libvorbis, flac)." >&2
        exit 1
    fi
    _copy_deref "$src" "$vendored"
    echo "macos-normalize-pyogg-dylibs: replaced $name with $src"
    replaced=$((replaced + 1))
done

if [[ $replaced -eq 0 ]]; then
    echo "macos-normalize-pyogg-dylibs: all ${kept} dylib(s) already match ${_target_arch}, nothing to do"
    exit 0
fi

# Pass 2: pull in package-manager dependencies the replacements reference.
# Files that pyogg loads by fixed name are already in place. Dependencies
# keep their own basename so their install name resolves under @loader_path.
declare -a _queue=()
for f in "${_pyogg_libs}"/*.dylib; do
    _queue+=("$f")
done
for ((i = 0; i < ${#_queue[@]}; i++)); do
    f="${_queue[$i]}"
    while IFS= read -r ref; do
        _is_managed_ref "$ref" || continue
        [[ -f "$ref" ]] || continue
        base="$(basename "$ref")"
        dest="${_pyogg_libs}/${base}"
        if [[ ! -f "$dest" ]]; then
            _copy_deref "$ref" "$dest"
            echo "macos-normalize-pyogg-dylibs: bundled dependency $base ($ref)"
            _queue+=("$dest")
        fi
    done < <(_dep_refs "$f")
done

# Pass 3: repoint ids and cross-references at @loader_path so the frozen
# layout resolves regardless of where the bundle is installed.
for f in "${_pyogg_libs}"/*.dylib; do
    while IFS= read -r ref; do
        base="$(basename "$ref")"
        if [[ -f "${_pyogg_libs}/${base}" && "$ref" != "@loader_path/${base}" ]]; then
            install_name_tool -change "$ref" "@loader_path/${base}" "$f"
        fi
    done < <(_dep_refs "$f")
    install_name_tool -id "@loader_path/$(basename "$f")" "$f"
    codesign --force --sign - "$f" >/dev/null 2>&1 || true
done

# Pass 4: verify every shipped dylib now covers the target arch and has no
# dangling package-manager refs left pointing outside the bundle.
_bad=0
for f in "${_pyogg_libs}"/*.dylib; do
    if ! _has_arch "$f"; then
        echo "macos-normalize-pyogg-dylibs: $(basename "$f") still lacks ${_target_arch}" >&2
        _bad=1
    fi
    while IFS= read -r ref; do
        if _is_managed_ref "$ref"; then
            echo "macos-normalize-pyogg-dylibs: unresolved ref ${ref} in $(basename "$f")" >&2
            _bad=1
        fi
    done < <(_dep_refs "$f")
done
if [[ $_bad -ne 0 ]]; then
    exit 1
fi

echo "macos-normalize-pyogg-dylibs: normalized ${replaced} dylib(s) for ${_target_arch} under ${_pyogg_libs} (kept ${kept})"
