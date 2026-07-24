#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Chainguard/Wolfi builder-stage compile toolchain.
set -eu

apk add --no-cache build-base git pkgconf openssl-dev libffi-dev linux-headers
