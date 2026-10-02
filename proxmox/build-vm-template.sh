#!/bin/bash
# SPDX-License-Identifier: 0BSD
# Build a MeshChatX VM template on a Proxmox host.
# Creates a Debian 13 cloud-init VM with Docker + MeshChatX.
#
# Run on the Proxmox host as root.
#
# Usage:
#   bash build-vm-template.sh [options]
#   --vmid N        template VMID (default 9000)
#   --name NAME     template name (default meshchatx-template)
#   --storage S     storage pool for disk (default local-lvm)
#   --bridge B      network bridge (default vmbr0)
#   --image-url URL Debian cloud image URL override
set -euo pipefail

VMID=9000
NAME="meshchatx-template"
STORAGE="local-lvm"
BRIDGE="vmbr0"
IMAGE_URL="https://cdimage.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vmid) VMID="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --storage) STORAGE="$2"; shift 2 ;;
        --bridge) BRIDGE="$2"; shift 2 ;;
        --image-url) IMAGE_URL="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 1 ;;
    esac
done

IMG="/tmp/debian-cloud-${VMID}.qcow2"

echo "==> Downloading Debian cloud image"
curl -fsSL -o "$IMG" "$IMAGE_URL"

echo "==> Creating VM $VMID"
qm create "$VMID" \
    --name "$NAME" \
    --memory 2048 \
    --cores 2 \
    --cpu host \
    --net0 "virtio,bridge=$BRIDGE" \
    --scsihw virtio-scsi-single \
    --ostype l26 \
    --agent enabled=1,fstrim_cloned_disks=1

qm importdisk "$VMID" "$IMG" "$STORAGE"
qm set "$VMID" --scsi0 "${STORAGE}:vm-${VMID}-disk-0"
qm set "$VMID" --ide2 "${STORAGE}:cloudinit"
qm set "$VMID" --boot order=scsi0
qm set "$VMID" --serial0 socket --vga serial0
qm set "$VMID" --ciuser meshchatx --ipconfig0 ip=dhcp

# Cloud-init snippet: install Docker + run MeshChatX
SNIP="/var/lib/vz/snippets/meshchatx-cloudinit.yaml"
mkdir -p /var/lib/vz/snippets
cat > "$SNIP" <<'EOF'
#cloud-config
package_update: true
packages:
    - docker.io
    - docker-compose-v2
runcmd:
    - systemctl enable --now docker
    - mkdir -p /opt/meshchatx/config
    - |
      docker run -d --name reticulum-meshchatx \
        --restart unless-stopped \
        --read-only --cap-drop ALL --security-opt no-new-privileges:true \
        --tmpfs /tmp:noexec,nosuid,size=256m \
        --tmpfs /home/meshchat:nosuid,size=64m \
        -p 8000:8000 \
        -v /opt/meshchatx/config:/config \
        quad4io/meshchatx:latest
EOF

qm set "$VMID" --cicustom "user=local:snippets/meshchatx-cloudinit.yaml"

echo "==> Converting VM $VMID to template"
qm template "$VMID"
rm -f "$IMG"

echo "Done. Clone template $NAME in the Proxmox GUI, set cloud-init credentials, boot."
echo "MeshChatX will be at https://<vm-ip>:8000"
