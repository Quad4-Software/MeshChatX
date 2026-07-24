#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Chainguard/Wolfi final-stage packages, pip bootstrap, and meshchat user.
set -eu

apk add --no-cache opus libffi shadow libseccomp
pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0"
rm -rf /root/.cache/pip

groupadd -g 1000 meshchat
useradd --uid 1000 --gid 1000 --create-home --home-dir /home/meshchat \
	--shell /sbin/nologin meshchat
mkdir -p /config
chown meshchat:meshchat /config
