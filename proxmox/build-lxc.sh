#!/bin/bash
# SPDX-License-Identifier: 0BSD
# Build a MeshChatX LXC container on a Proxmox host.
# Creates a Debian 13 privileged LXC with nesting enabled for Docker.
#
# Run on the Proxmox host as root.
#
# Usage:
#   bash build-lxc.sh [options]
#   --ctid N        container ID (default 200)
#   --name NAME     hostname (default meshchatx)
#   --storage S     storage pool (default local-lvm)
#   --bridge B      network bridge (default vmbr0)
#   --ip CIDR       static IP (default dhcp)
#   --gw IP         gateway for static IP
#   --password PW   root password (default prompt)
set -euo pipefail

CTID=200
NAME="meshchatx"
STORAGE="local-lvm"
BRIDGE="vmbr0"
IP="dhcp"
GW=""
PASSWORD=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ctid) CTID="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --storage) STORAGE="$2"; shift 2 ;;
        --bridge) BRIDGE="$2"; shift 2 ;;
        --ip) IP="$2"; shift 2 ;;
        --gw) GW="$2"; shift 2 ;;
        --password) PASSWORD="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$PASSWORD" ]]; then
    read -rsp "Root password for container: " PASSWORD
    echo
fi

NETCFG="name=eth0,bridge=${BRIDGE},ip=${IP}"
[[ -n "$GW" ]] && NETCFG="${NETCFG},gw=${GW}"

TEMPLATE="debian-13-standard"
TEMPLATE_FILE=""
for d in /var/lib/vz/template/cache; do
    f=$(ls -t "$d"/${TEMPLATE}*.tar.zst 2>/dev/null | head -1)
    if [[ -n "$f" ]]; then TEMPLATE_FILE="$f"; break; fi
done

if [[ -z "$TEMPLATE_FILE" ]]; then
    echo "==> Downloading Debian 13 LXC template"
    pveam update >/dev/null
    pveam download local "${TEMPLATE}_amd64.tar.zst" 2>/dev/null || \
        pveam download local "debian-13-standard_13.1-2_amd64.tar.zst"
    TEMPLATE_FILE=$(ls -t /var/lib/vz/template/cache/${TEMPLATE}*.tar.zst | head -1)
fi

echo "==> Creating LXC $CTID ($NAME)"
pct create "$CTID" "$TEMPLATE_FILE" \
    --hostname "$NAME" \
    --memory 2048 \
    --cores 2 \
    --rootfs "${STORAGE}:10" \
    --net0 "$NETCFG" \
    --password "$PASSWORD" \
    --features nesting=1 \
    --unprivileged 0 \
    --start 0

pct start "$CTID"
sleep 5

echo "==> Installing Docker + MeshChatX inside LXC"
pct exec "$CTID" -- bash -c "
    apt-get update -qq &&
    apt-get install -y -qq docker.io docker-compose-v2 curl &&
    systemctl enable --now docker &&
    mkdir -p /opt/meshchatx/config &&
    docker run -d --name reticulum-meshchatx \
        --restart unless-stopped \
        --read-only --cap-drop ALL --security-opt no-new-privileges:true \
        --tmpfs /tmp:noexec,nosuid,size=256m \
        --tmpfs /home/meshchat:nosuid,size=64m \
        -p 8000:8000 \
        -v /opt/meshchatx/config:/config \
        quad4io/meshchatx:latest
"

echo "Done. LXC $CTID ($NAME) is running."
echo "MeshChatX: https://<container-ip>:8000"
