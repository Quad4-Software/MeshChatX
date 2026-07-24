#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Alpine final-stage packages, pip bootstrap, and meshchat user.
# Usage: runtime-setup.sh [standard|extra]
set -eu

VARIANT="${1:-${VARIANT:-standard}}"

apk upgrade --no-cache
apk add --no-cache opusfile libffi espeak-ng su-exec libseccomp

case "${VARIANT}" in
standard) ;;
extra)
	apk add --no-cache i2pd
	# yggdrasil post-install runs modprobe which fails without host modules
	apk add --no-cache --no-scripts yggdrasil
	;;
*)
	echo "runtime-setup.sh: unknown VARIANT '${VARIANT}' (expected standard or extra)" >&2
	exit 1
	;;
esac

python -m pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0"
rm -rf /root/.cache/pip

addgroup -g 1000 meshchat
adduser -u 1000 -G meshchat -S meshchat
mkdir -p /config
chown meshchat:meshchat /config
