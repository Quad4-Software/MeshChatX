#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Alpine builder-stage compile toolchain for uv sync and LXST musl bake.
set -eu

apk upgrade --no-cache
apk add --no-cache gcc g++ musl-dev linux-headers python3-dev libffi-dev openssl-dev git curl ca-certificates
