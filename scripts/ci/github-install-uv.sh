#!/usr/bin/env bash
# Install UV (Python package manager) from PyPI with an explicit version.
# Set UV_VERSION to override the default.
set -euo pipefail

UV_VERSION="${UV_VERSION:-0.11.15}"

python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check "uv==${UV_VERSION}"
uv --version
