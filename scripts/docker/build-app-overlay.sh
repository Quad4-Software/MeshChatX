#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Install the project into /opt/venv and copy a thin app overlay for image layering.
# Requires PATH pointing at /opt/venv/bin and built frontend under meshchatx/public.
set -eu

VENV="${MESHCHATX_DOCKER_VENV:-/opt/venv}"
OUT="${MESHCHATX_DOCKER_APP_OVERLAY:-/opt/app-overlay}"

uv pip install --no-cache .

PYVER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
SP="${VENV}/lib/python${PYVER}/site-packages"

rm -rf "${OUT}"
mkdir -p "${OUT}/lib/python${PYVER}/site-packages" "${OUT}/bin"

for pkg in meshchatx lxmfy rns_filesync; do
	cp -a "${SP}/${pkg}" "${OUT}/lib/python${PYVER}/site-packages/"
done

cp -a "${SP}"/reticulum_meshchatx*.dist-info "${OUT}/lib/python${PYVER}/site-packages/"

for cmd in meshchat meshchatx meshchatx-repository-http lxmfy rns-filesync; do
	cp -a "${VENV}/bin/${cmd}" "${OUT}/bin/"
done

find "${OUT}" -type d -name __pycache__ -prune -exec rm -rf {} +
python -m compileall -q "${OUT}/lib/python${PYVER}/site-packages"
