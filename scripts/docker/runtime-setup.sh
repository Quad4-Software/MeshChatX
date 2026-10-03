#!/bin/sh
# SPDX-License-Identifier: 0BSD
# Alpine final-stage packages, pip removal, and meshchat user.
# Usage: runtime-setup.sh [standard|extra]
set -eu

VARIANT="${1:-${VARIANT:-standard}}"

apk upgrade --no-cache
apk add --no-cache opusfile libffi espeak-ng su-exec libseccomp

# The runtime image runs /opt/venv only. Removing pip and ensurepip drops
# unused vulnerable vendored packages that scanners flag in the base image.
rm -rf /usr/local/lib/python*/ensurepip /usr/local/lib/python*/site-packages/pip* \
	/usr/local/bin/pip*

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

addgroup -g 1000 meshchat
adduser -u 1000 -G meshchat -S meshchat
mkdir -p /config
chown meshchat:meshchat /config
