#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Sync third-party deps into /opt/venv, apply LXST patches, snapshot /opt/venv-deps.
# Requires PATH pointing at /opt/venv/bin and project files already copied to WORKDIR.
# Set MESHCHATX_DOCKER_SKIP_MUSL_FILTERLIB=1 on glibc (hardened) builds.
set -eu

VENV="${MESHCHATX_DOCKER_VENV:-/opt/venv}"
VENV_DEPS="${MESHCHATX_DOCKER_VENV_DEPS:-/opt/venv-deps}"

uv sync --no-group dev --no-install-project --inexact
rm -rf /root/.cache/pip /root/.cache/uv
uv pip install --no-cache --upgrade "setuptools" "jaraco.context>=6.1.0"

python scripts/patch_lxst_pyogg_ogg_ctypes.py
python scripts/patch_lxst_codec2_optional.py

if [ "${MESHCHATX_DOCKER_SKIP_MUSL_FILTERLIB:-0}" != "1" ]; then
	python scripts/docker-bake-lxst-filterlib-musl.py
fi

rm -rf "${VENV}"/lib/python*/site-packages/LXST/Platforms/android
find "${VENV}" -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf {} +

PYVER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python -m compileall -q "${VENV}/lib/python${PYVER}/site-packages"

rm -rf "${VENV_DEPS}"
cp -a "${VENV}" "${VENV_DEPS}"
