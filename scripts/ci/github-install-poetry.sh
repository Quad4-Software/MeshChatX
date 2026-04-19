#!/usr/bin/env bash
# Install Poetry from PyPI with an explicit version (no third-party installers).
# Set POETRY_VERSION to override the default.
set -euo pipefail

POETRY_VERSION="${POETRY_VERSION:-2.3.4}"

python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check "poetry==${POETRY_VERSION}"
python -m poetry --version
