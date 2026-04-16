#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Build Android wheels locally for Chaquopy (Linux x86_64 host).

This script:
1) Clones/updates Chaquopy sources locally
2) Downloads a matching Chaquopy Python target toolchain
3) Builds pycodec2 Android wheels with Chaquopy's build-wheel tool
4) Optionally patches LXST wheel metadata for local Android constraints
5) Copies outputs to android/vendor

Usage:
  scripts/build-android-wheels-local.sh [options]

Options:
  --python-minor X.Y         Python minor for target wheels (default: 3.11)
  --target-version V         Explicit Chaquopy target version (default: auto latest for python minor)
  --chaquopy-ref REF         Chaquopy git ref/commit to checkout (default: master)
  --abis LIST                Comma-separated ABIs (default: arm64-v8a,x86_64)
  --api-level N              Android API level for wheel tag (default: 24)
  --pycodec2-version V       pycodec2 version to build (default: 4.1.1)
  --numpy-version V          NumPy version used during pycodec2 build (default: 1.26.2)
  --lxst-version V           LXST wheel version for metadata patch (default: 0.4.6)
  --no-lxst-patch            Skip LXST metadata patch
  --work-dir PATH            Working directory (default: ./.local/chaquopy-build-wheel)
  --out-dir PATH             Output wheel directory (default: ./android/vendor)
  -h, --help                 Show this help
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_MINOR="3.11"
TARGET_VERSION=""
CHAQUOPY_REF="${CHAQUOPY_REF:-master}"
ABI_LIST="arm64-v8a,x86_64"
API_LEVEL="24"
PYCODEC2_VERSION="4.1.1"
LIBCODEC2_VERSION="1.2.0"
NUMPY_VERSION="1.26.2"
LXST_VERSION="0.4.6"
PATCH_LXST="1"
WORK_DIR="${ROOT_DIR}/.local/chaquopy-build-wheel"
OUT_DIR="${ROOT_DIR}/android/vendor"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --python-minor)
            PYTHON_MINOR="${2:?missing value for --python-minor}"
            shift 2
            ;;
        --target-version)
            TARGET_VERSION="${2:?missing value for --target-version}"
            shift 2
            ;;
        --chaquopy-ref)
            CHAQUOPY_REF="${2:?missing value for --chaquopy-ref}"
            shift 2
            ;;
        --abis)
            ABI_LIST="${2:?missing value for --abis}"
            shift 2
            ;;
        --api-level)
            API_LEVEL="${2:?missing value for --api-level}"
            shift 2
            ;;
        --pycodec2-version)
            PYCODEC2_VERSION="${2:?missing value for --pycodec2-version}"
            shift 2
            ;;
        --numpy-version)
            NUMPY_VERSION="${2:?missing value for --numpy-version}"
            shift 2
            ;;
        --lxst-version)
            LXST_VERSION="${2:?missing value for --lxst-version}"
            shift 2
            ;;
        --no-lxst-patch)
            PATCH_LXST="0"
            shift
            ;;
        --work-dir)
            WORK_DIR="${2:?missing value for --work-dir}"
            shift 2
            ;;
        --out-dir)
            OUT_DIR="${2:?missing value for --out-dir}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

abi_to_platform_tag() {
    case "$1" in
        arm64-v8a) echo "android_21_arm64_v8a" ;;
        x86_64) echo "android_21_x86_64" ;;
        armeabi-v7a) echo "android_16_armeabi_v7a" ;;
        x86) echo "android_16_x86" ;;
        *)
            echo "Unsupported ABI: $1" >&2
            exit 1
            ;;
    esac
}

discover_latest_target() {
    local python_minor="$1"
    local metadata versions latest
    metadata="$(curl -fsSL "https://repo.maven.apache.org/maven2/com/chaquo/python/target/maven-metadata.xml")"
    versions="$(printf '%s\n' "$metadata" \
        | sed -n 's|.*<version>\(.*\)</version>.*|\1|p' \
        | awk -v p="${python_minor}." 'index($0, p)==1')"
    latest="$(printf '%s\n' "$versions" | sort -V | tail -n 1)"
    if [[ -z "${latest}" ]]; then
        echo "Could not discover Chaquopy target version for Python ${python_minor}" >&2
        exit 1
    fi
    printf '%s\n' "$latest"
}

require_cmd git
require_cmd curl
require_cmd sed
require_cmd awk
require_cmd sort

PYTHON_BIN="python${PYTHON_MINOR}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "Required interpreter not found on PATH: ${PYTHON_BIN}" >&2
    echo "Install Python ${PYTHON_MINOR} locally before running this script." >&2
    exit 1
fi

mkdir -p "${WORK_DIR}" "${OUT_DIR}"

CHAQUOPY_DIR="${WORK_DIR}/chaquopy"
if [[ ! -d "${CHAQUOPY_DIR}/.git" ]]; then
    git clone --depth 1 https://github.com/chaquo/chaquopy.git "${CHAQUOPY_DIR}"
fi
git -C "${CHAQUOPY_DIR}" fetch --depth 1 origin "${CHAQUOPY_REF}"
git -C "${CHAQUOPY_DIR}" checkout --detach FETCH_HEAD

if [[ -z "${TARGET_VERSION}" ]]; then
    TARGET_VERSION="$(discover_latest_target "${PYTHON_MINOR}")"
fi
echo "Using Chaquopy git ref: ${CHAQUOPY_REF}"
echo "Using Chaquopy target version: ${TARGET_VERSION}"

pushd "${CHAQUOPY_DIR}" >/dev/null
TARGET_PATH="maven/com/chaquo/python/target/${TARGET_VERSION}"
if [[ ! -d "${TARGET_PATH}" ]]; then
    ./target/download-target.sh "${TARGET_PATH}"
else
    echo "Chaquopy target already present: ${TARGET_PATH}"
fi
popd >/dev/null

PYPIDIR="${CHAQUOPY_DIR}/server/pypi"
VENV_DIR="${PYPIDIR}/.venv-local"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${PYPIDIR}/requirements.txt"
"${VENV_DIR}/bin/pip" install "numpy==${NUMPY_VERSION}"
# Chaquopy build-wheel.py shells out to `wheel pack`, so ensure the venv scripts are first on PATH.
export PATH="${VENV_DIR}/bin:${PATH}"
if ! command -v wheel >/dev/null 2>&1; then
    echo "Missing required wheel CLI in virtualenv at ${VENV_DIR}" >&2
    exit 1
fi

NUMPY_DIST_DIR="${PYPIDIR}/dist/numpy"
mkdir -p "${NUMPY_DIST_DIR}"
PYTHON_ABI_TAG="cp${PYTHON_MINOR/./}"
for abi in ${ABI_LIST//,/ }; do
    platform_tag="$(abi_to_platform_tag "${abi}")"
    echo "Resolving NumPy wheel for ABI ${abi} (${platform_tag})"
    if ! "${VENV_DIR}/bin/pip" download \
        --only-binary=:all: \
        --no-deps \
        --platform "${platform_tag}" \
        --python-version "${PYTHON_MINOR/./}" \
        --implementation cp \
        --abi "${PYTHON_ABI_TAG}" \
        "numpy==${NUMPY_VERSION}" \
        --index-url https://pypi.org/simple \
        --extra-index-url https://chaquo.com/pypi-13.1 \
        --dest "${NUMPY_DIST_DIR}"; then
        echo "No prebuilt NumPy wheel for ${abi}; building locally via Chaquopy recipe"
        "${VENV_DIR}/bin/python" "${PYPIDIR}/build-wheel.py" \
            --python "${PYTHON_MINOR}" \
            --api-level "${API_LEVEL}" \
            --abi "${abi}" \
            "${PYPIDIR}/packages/numpy"
        cp -f "${PYPIDIR}/dist/numpy"/numpy-"${NUMPY_VERSION}"-*.whl "${NUMPY_DIST_DIR}/"
    fi
done

RECIPE_DIR="${WORK_DIR}/recipes/pycodec2-local"
LIBCODEC2_RECIPE_DIR="${WORK_DIR}/recipes/chaquopy-libcodec2-local"
SOURCE_DIR="${WORK_DIR}/sources/pycodec2-${PYCODEC2_VERSION}"
rm -rf "${RECIPE_DIR}" "${LIBCODEC2_RECIPE_DIR}"
mkdir -p "${RECIPE_DIR}" "${LIBCODEC2_RECIPE_DIR}" "${WORK_DIR}/sources"

rm -rf "${SOURCE_DIR}"
"${VENV_DIR}/bin/python" - <<PY
import json
import tarfile
import urllib.request
from pathlib import Path

version = "${PYCODEC2_VERSION}"
work_dir = Path("${WORK_DIR}")
sources_dir = Path("${WORK_DIR}/sources")
sdist_path = work_dir / f"pycodec2-{version}.tar.gz"

with urllib.request.urlopen(f"https://pypi.org/pypi/pycodec2/{version}/json") as resp:
    payload = json.load(resp)

sdist_url = None
for file_entry in payload.get("urls", []):
    if file_entry.get("packagetype") == "sdist":
        sdist_url = file_entry.get("url")
        break

if not sdist_url:
    raise SystemExit(f"No sdist URL found for pycodec2 {version}")

urllib.request.urlretrieve(sdist_url, sdist_path)
with tarfile.open(sdist_path, "r:gz") as tf:
    tf.extractall(path=sources_dir)
sdist_path.unlink()
PY

"${VENV_DIR}/bin/python" - <<PY
from pathlib import Path

pyproject = Path("${SOURCE_DIR}/pyproject.toml")
text = pyproject.read_text()
text = text.replace('numpy==2.1.*', 'numpy==${NUMPY_VERSION}')
text = text.replace('numpy>=2.00, <3.0.0', 'numpy==${NUMPY_VERSION}')
pyproject.write_text(text)

setup_py = Path("${SOURCE_DIR}/setup.py")
setup_text = setup_py.read_text()
if "from pathlib import Path" not in setup_text:
    setup_text = setup_text.replace("import sys\n", "import sys\nfrom pathlib import Path\n")
setup_text = setup_text.replace(
    'libraries=["libcodec2"] if sys.platform == "win32" else ["codec2"],',
    'libraries=["libcodec2"] if sys.platform == "win32" else [],'
)
if "extra_objects=[] if sys.platform == \"win32\"" not in setup_text:
    setup_text = setup_text.replace(
        'libraries=["libcodec2"] if sys.platform == "win32" else [],',
        'libraries=["libcodec2"] if sys.platform == "win32" else [],\n'
        '        extra_objects=[] if sys.platform == "win32" else [str((Path(__file__).resolve().parent / "pycodec2" / "libcodec2.so"))],'
    )
if "class ChaquopyBuildExt" not in setup_text:
    setup_text = setup_text.replace(
        "setup(",
        "class ChaquopyBuildExt(Cython.Build.build_ext):\n"
        "    def build_extensions(self):\n"
        "        c_file = Path(__file__).resolve().parent / \"pycodec2\" / \"pycodec2.c\"\n"
        "        if c_file.exists():\n"
        "            text = c_file.read_text()\n"
        "            text = text.replace(\n"
        "                \"#ifndef CYTHON_NO_PYINIT_EXPORT\",\n"
        "                \"#undef CYTHON_NO_PYINIT_EXPORT\\\\n#ifndef CYTHON_NO_PYINIT_EXPORT\",\n"
        "            )\n"
        "            text = text.replace(\n"
        "                \"#define __Pyx_PyMODINIT_FUNC PyMODINIT_FUNC\",\n"
        '                \'#define __Pyx_PyMODINIT_FUNC __attribute__((visibility("default"))) PyObject *\',\n'
        "            )\n"
        "            c_file.write_text(text)\n"
        "        if sys.platform != \"win32\":\n"
        "            self.compiler.linker_so = [\n"
        "                arg for arg in self.compiler.linker_so\n"
        "                if \"python3\" not in arg and arg != \"-Wl,--no-undefined\"\n"
        "            ]\n"
        "        super().build_extensions()\n\n"
        "setup("
    )
setup_text = setup_text.replace(
    'cmdclass={"build_ext": Cython.Build.build_ext},',
    'cmdclass={"build_ext": ChaquopyBuildExt},'
)
setup_py.write_text(setup_text)

import shutil
import numpy as np
import re

numpy_headers = Path(np.get_include()) / "numpy"
vendored_numpy = Path("${SOURCE_DIR}/pycodec2/numpy")
if vendored_numpy.exists():
    shutil.rmtree(vendored_numpy)
shutil.copytree(numpy_headers, vendored_numpy)

include_pattern = re.compile(r'#include\s+<numpy/([^>]+)>')
for header in vendored_numpy.rglob("*.h"):
    content = header.read_text()
    content = include_pattern.sub(r'#include "\1"', content)
    header.write_text(content)
PY

cat > "${LIBCODEC2_RECIPE_DIR}/meta.yaml" <<EOF
package:
  name: chaquopy-libcodec2
  version: "${LIBCODEC2_VERSION}"

source:
  git_url: "https://github.com/drowe67/codec2.git"
  git_rev: "${LIBCODEC2_VERSION}"

requirements:
  build:
    - cmake 3.22.1

about:
  license_file: COPYING
EOF

cat > "${LIBCODEC2_RECIPE_DIR}/build.sh" <<'EOF'
#!/bin/bash
set -eu

# Build a host-native codebook generator and patch CMake to use it while cross-compiling.
cc src/generate_codebook.c -lm -o src/generate_codebook_host
python3 - <<'PY'
from pathlib import Path

cmake_file = Path("src/CMakeLists.txt")
text = cmake_file.read_text()
old_block = """# when crosscompiling we need a native executable
if(CMAKE_CROSSCOMPILING)
    set(CMAKE_DISABLE_SOURCE_CHANGES OFF)
    include(ExternalProject)
    ExternalProject_Add(codec2_native
       SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/..
       BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR}/codec2_native
       BUILD_COMMAND ${CMAKE_COMMAND} --build . --target generate_codebook
       INSTALL_COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_BINARY_DIR}/codec2_native/src/generate_codebook ${CMAKE_CURRENT_BINARY_DIR}
       BUILD_BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/generate_codebook
    )
    add_executable(generate_codebook IMPORTED)
    set_target_properties(generate_codebook PROPERTIES
        IMPORTED_LOCATION ${CMAKE_CURRENT_BINARY_DIR}/generate_codebook)
    add_dependencies(generate_codebook codec2_native)
    set(CMAKE_DISABLE_SOURCE_CHANGES ON)
else(CMAKE_CROSSCOMPILING)
# Build code generator binaries. These do not get installed.
    # generate_codebook
    add_executable(generate_codebook generate_codebook.c)
    target_link_libraries(generate_codebook m)
    # Make native builds available for cross-compiling.
    export(TARGETS generate_codebook
        FILE ${CMAKE_BINARY_DIR}/ImportExecutables.cmake)
endif(CMAKE_CROSSCOMPILING)
"""
new_block = """# Use host-native generator to avoid nested cross-compilation recursion.
set(HOST_GENERATE_CODEBOOK ${CMAKE_CURRENT_SOURCE_DIR}/generate_codebook_host)
"""
if old_block not in text:
    raise SystemExit("Could not find expected generate_codebook block in CMakeLists.txt")
text = text.replace(old_block, new_block)
text = text.replace("COMMAND generate_codebook", "COMMAND ${HOST_GENERATE_CODEBOOK}")
text = text.replace("DEPENDS generate_codebook ", "DEPENDS ")
cmake_file.write_text(text)

codec2_h = Path("src/codec2.h")
codec2_text = codec2_h.read_text()
codec2_text = codec2_text.replace("#include <codec2/version.h>", '#include "version.h"')
codec2_h.write_text(codec2_text)

Path("src/version.h").write_text(
    "#ifndef CODEC2_VERSION_H\n"
    "#define CODEC2_VERSION_H\n"
    "#define CODEC2_VERSION_MAJOR 1\n"
    "#define CODEC2_VERSION_MINOR 2\n"
    "#define CODEC2_VERSION_PATCH 0\n"
    "#define CODEC2_VERSION \"1.2.0\"\n"
    "#endif\n"
)

root_cmake = Path("CMakeLists.txt")
root_text = root_cmake.read_text()
root_text = root_text.replace("add_subdirectory(demo)\n", "")
root_cmake.write_text(root_text)
PY

mkdir -p build-chaquopy
cd build-chaquopy
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DBUILD_SHARED_LIBS=ON
mkdir -p src
cp -f ../src/defines.h src/defines.h
make -j "$CPU_COUNT"
make install
mkdir -p "$PREFIX/include/codec2"
cp -f ../src/version.h "$PREFIX/include/codec2/version.h"

rm -f "$PREFIX"/lib/*.a || true
rm -rf "$PREFIX"/lib/cmake || true
rm -rf "$PREFIX"/share || true
EOF
chmod +x "${LIBCODEC2_RECIPE_DIR}/build.sh"

cat > "${RECIPE_DIR}/meta.yaml" <<EOF
package:
  name: pycodec2
  version: "${PYCODEC2_VERSION}"

source:
  path: "${SOURCE_DIR}"

requirements:
  build:
    - cython 3.0.11
  host:
    - chaquopy-libcodec2 ${LIBCODEC2_VERSION}
    - python

about:
  license_file: LICENSE
EOF

pushd "${PYPIDIR}" >/dev/null
for abi in ${ABI_LIST//,/ }; do
    abi_tag="${abi//-/_}"

    echo "Building chaquopy-libcodec2 ${LIBCODEC2_VERSION} for ${abi}"
    "${VENV_DIR}/bin/python" "${PYPIDIR}/build-wheel.py" \
        --python "${PYTHON_MINOR}" \
        --api-level "${API_LEVEL}" \
        --abi "${abi}" \
        "${LIBCODEC2_RECIPE_DIR}"

    LIBCODEC2_PREFIX="${LIBCODEC2_RECIPE_DIR}/build/${LIBCODEC2_VERSION}/py3-none-android_${API_LEVEL}_${abi_tag}/prefix/chaquopy"
    if [[ ! -f "${LIBCODEC2_PREFIX}/lib/libcodec2.so" ]]; then
        echo "Missing libcodec2 output for ${abi}: ${LIBCODEC2_PREFIX}/lib/libcodec2.so" >&2
        exit 1
    fi
    mkdir -p "${SOURCE_DIR}/pycodec2/codec2"
    cp -f "${LIBCODEC2_PREFIX}/include/codec2/codec2.h" "${SOURCE_DIR}/pycodec2/codec2/codec2.h"
    cp -f "${LIBCODEC2_PREFIX}/include/codec2/version.h" "${SOURCE_DIR}/pycodec2/codec2/version.h"
    cp -f "${LIBCODEC2_PREFIX}/lib/libcodec2.so" "${SOURCE_DIR}/pycodec2/libcodec2.so"
    sed -i 's|#include <codec2/version.h>|#include "version.h"|' "${SOURCE_DIR}/pycodec2/codec2/codec2.h"

    PYCODEC2_PREFIX="${RECIPE_DIR}/build/${PYCODEC2_VERSION}/${PYTHON_ABI_TAG}-${PYTHON_ABI_TAG}-android_${API_LEVEL}_${abi_tag}/requirements/chaquopy"
    PY_INCLUDE_DIR="${PYCODEC2_PREFIX}/include/python${PYTHON_MINOR}"
    mkdir -p "${PY_INCLUDE_DIR}/numpy" "${PY_INCLUDE_DIR}/codec2" "${PYCODEC2_PREFIX}/lib"
    cp -f "${SOURCE_DIR}/pycodec2/codec2/codec2.h" "${PY_INCLUDE_DIR}/codec2/codec2.h"
    cp -f "${SOURCE_DIR}/pycodec2/codec2/version.h" "${PY_INCLUDE_DIR}/codec2/version.h"
    cp -rf "${SOURCE_DIR}/pycodec2/numpy/." "${PY_INCLUDE_DIR}/numpy/"
    cp -f "${SOURCE_DIR}/pycodec2/libcodec2.so" "${PYCODEC2_PREFIX}/lib/libcodec2.so"

    echo "Building pycodec2 ${PYCODEC2_VERSION} for ${abi}"
    C_INCLUDE_PATH="${PY_INCLUDE_DIR}" CPLUS_INCLUDE_PATH="${PY_INCLUDE_DIR}" LIBRARY_PATH="${PYCODEC2_PREFIX}/lib" "${VENV_DIR}/bin/python" "${PYPIDIR}/build-wheel.py" \
        --python "${PYTHON_MINOR}" \
        --api-level "${API_LEVEL}" \
        --abi "${abi}" \
        "${RECIPE_DIR}"
done
popd >/dev/null

mkdir -p "${OUT_DIR}"
cp -f "${PYPIDIR}/dist/chaquopy-libcodec2"/chaquopy_libcodec2-"${LIBCODEC2_VERSION}"-*.whl "${OUT_DIR}/"
cp -f "${PYPIDIR}/dist/pycodec2"/pycodec2-"${PYCODEC2_VERSION}"-*.whl "${OUT_DIR}/"

if [[ "${PATCH_LXST}" == "1" ]]; then
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "${TMP_DIR}"' EXIT

    "${VENV_DIR}/bin/pip" download \
        --only-binary=:all: \
        --no-deps \
        "lxst==${LXST_VERSION}" \
        --dest "${TMP_DIR}" \
        --index-url https://pypi.org/simple

    LXST_WHEEL="$(ls "${TMP_DIR}"/lxst-"${LXST_VERSION}"-py3-none-any.whl)"
    PATCHED_LXST_WHEEL="${OUT_DIR}/lxst-${LXST_VERSION}-py3-none-any.whl"

    "${VENV_DIR}/bin/python" - <<PY
import zipfile
from pathlib import Path

src = Path("${LXST_WHEEL}")
dst = Path("${PATCHED_LXST_WHEEL}")
patched_codecs_init = """from .Codec import CodecError as CodecError
from .Codec import Codec as Codec
from .Codec import Null as Null
from .Raw import Raw as Raw
from .Opus import Opus as Opus

_CODEC2_IMPORT_ERROR = None
try:
    from .Codec2 import Codec2 as Codec2
except Exception as _codec2_exc:
    Codec2 = None
    _CODEC2_IMPORT_ERROR = _codec2_exc

NULL   = 0xFF
RAW    = 0x00
OPUS   = 0x01
CODEC2 = 0x02

def _raise_codec2_unavailable():
    if _CODEC2_IMPORT_ERROR is not None:
        raise CodecError(f"Codec2 backend unavailable: {_CODEC2_IMPORT_ERROR}")
    raise CodecError("Codec2 backend unavailable")

def codec_header_byte(codec):
    if codec == Raw:
        return RAW.to_bytes()
    elif codec == Opus:
        return OPUS.to_bytes()
    elif Codec2 is not None and codec == Codec2:
        return CODEC2.to_bytes()

    raise TypeError(f"No header mapping for codec type {codec}")

def codec_type(header_byte):
    if header_byte == RAW:
        return Raw
    elif header_byte == OPUS:
        return Opus
    elif header_byte == CODEC2:
        if Codec2 is None:
            _raise_codec2_unavailable()
        return Codec2
"""

with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "LXST/Codecs/__init__.py":
            data = patched_codecs_init.encode("utf-8")
        elif item.filename.endswith(".dist-info/METADATA"):
            text = data.decode("utf-8")
            text = text.replace("Requires-Dist: numpy>=2.3.4", "Requires-Dist: numpy==${NUMPY_VERSION}")
            text = text.replace("Requires-Dist: cffi>=2.0.0", "Requires-Dist: cffi==1.15.1")
            data = text.encode("utf-8")
        zout.writestr(item, data)
PY
fi

echo "Done."
echo "Built wheels in: ${OUT_DIR}"
