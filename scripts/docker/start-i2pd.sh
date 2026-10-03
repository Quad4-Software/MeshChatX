#!/bin/sh
# Start i2pd with SAM and the MeshChatX HTTP tunnel when the extra image is used.
set -eu

I2PD=""
for p in /usr/sbin/i2pd /usr/bin/i2pd; do
	if [ -x "$p" ]; then
		I2PD="$p"
		break
	fi
done
if [ -z "$I2PD" ]; then
	exit 0
fi

if [ "${I2P_DISABLE:-0}" = "1" ]; then
	exit 0
fi

DATADIR="${I2P_DATADIR:-/config/i2pd}"
mkdir -p "$DATADIR"

if [ ! -f "$DATADIR/i2pd.conf" ]; then
	cp /etc/i2pd/i2pd.conf "$DATADIR/i2pd.conf"
fi

if [ ! -f "$DATADIR/tunnels.conf" ]; then
	if [ "${I2P_SITE:-1}" = "0" ]; then
		: >"$DATADIR/tunnels.conf"
	else
		port="${I2P_SITE_PORT:-8000}"
		ssl="${I2P_SITE_SSL:-}"
		if [ -z "$ssl" ]; then
			ssl="false"
		fi
		cat >"$DATADIR/tunnels.conf" <<EOF
[meshchatx]
type = http
host = 127.0.0.1
port = ${port}
keys = meshchatx-site.dat
hostoverride = 127.0.0.1
ssl = ${ssl}
inbound.quantity = 3
outbound.quantity = 3
EOF
	fi
fi

"$I2PD" \
	--datadir "$DATADIR" \
	--conf "$DATADIR/i2pd.conf" \
	--tunconf "$DATADIR/tunnels.conf" \
	--log=file \
	--logfile "$DATADIR/i2pd.log" &
