#!/usr/bin/env bash
# Boot MeshChatX inside a Firecracker microVM.
# Standalone: needs only firecracker, curl, tar, ip, nft, mkfs.ext4, truncate.
#
#   ./start.sh           build (if needed) + boot, foreground
#   ./start.sh --build   force rebuild the rootfs
#   ./start.sh --stop    kill the VM and remove TAP/NAT
#   ./start.sh --status  print guest URL and process state
#
# TAP networking and NAT need root. Run via sudo or a root shell.
# Override knobs: MEM_MIB VCPUS GUEST_IP HOST_IP TAP HOST_PORT ALPINE_VERSION

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${MICROVM_STATE_DIR:-$HERE/state}"
GUEST_DIR="$STATE_DIR/guest"
ROOTFS_IMG="$STATE_DIR/rootfs.ext4"
DATA_IMG="$STATE_DIR/data.ext4"
KERNEL_IMG="$STATE_DIR/vmlinux"
FC_SOCKET="$STATE_DIR/firecracker.sock"
FC_LOG="$STATE_DIR/firecracker.log"
FC_CONFIG="$STATE_DIR/firecracker.json"
FC_PIDFILE="$STATE_DIR/firecracker.pid"

ALPINE_VERSION="${ALPINE_VERSION:-3.24.2}"
ALPINE_URL="https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION%.*}/releases/x86_64/alpine-minirootfs-${ALPINE_VERSION}-x86_64.tar.gz"

MEM_MIB="${MEM_MIB:-1024}"
VCPUS="${VCPUS:-1}"
TAP="${TAP:-fc-mcx0}"
GUEST_IP="${GUEST_IP:-172.16.44.2}"
HOST_IP="${HOST_IP:-172.16.44.1}"
NETMASK="24"
HOST_PORT="${HOST_PORT:-8000}"

log() { printf 'microvm: %s\n' "$*"; }
die() { printf 'microvm: ERROR %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }

preflight() {
    need firecracker; need curl; need tar; need ip; need truncate
    need mkfs.ext4; need nft
    [ -c /dev/kvm ] || die "/dev/kvm missing - enable KVM or run on bare metal"
    [ -w /dev/kvm ] || [ "$(id -u)" = "0" ] || die "/dev/kvm not writable - run as root or add yourself to the kvm group"
}

# ---------- kernel ----------

fetch_kernel() {
    # Prefer the host kernel image; fall back to the Firecracker CI kernel.
    local host_vmlinuz="/usr/lib/modules/$(uname -r)/vmlinuz"
    if [ -f "$host_vmlinuz" ]; then
        log "using host kernel $host_vmlinuz"
        cp "$host_vmlinuz" "$KERNEL_IMG"
        return
    fi
    log "host kernel not found, downloading Firecracker CI kernel"
    curl -fsSL "https://s3.amazonaws.com/spec.ccfc.min/firecracker-ci/v1.13/x86_64/vmlinux-6.1.141" -o "$KERNEL_IMG"
}

# ---------- rootfs ----------

build_rootfs() {
    log "building rootfs (alpine ${ALPINE_VERSION})"
    rm -rf "$GUEST_DIR"
    mkdir -p "$GUEST_DIR"
    curl -fsSL "$ALPINE_URL" -o "$STATE_DIR/alpine.tar.gz"
    tar -xzf "$STATE_DIR/alpine.tar.gz" -C "$GUEST_DIR"
    rm -f "$STATE_DIR/alpine.tar.gz"

    # Copy the meshchatx template into the guest
    mkdir -p "$GUEST_DIR/opt/template"
    cp "$HERE/meshchatx/install.sh" "$GUEST_DIR/opt/template/install.sh"
    cp "$HERE/meshchatx/run.sh" "$GUEST_DIR/opt/template/run.sh"
    cp "$HERE/meshchatx/manifest.env" "$GUEST_DIR/opt/template/manifest.env"
    cp "$HERE/meshchatx/firewall.env" "$GUEST_DIR/opt/template/firewall.env"
    chmod +x "$GUEST_DIR/opt/template/install.sh" "$GUEST_DIR/opt/template/run.sh"

    # Guest init: busybox + static IP + first-boot install + exec run.sh
    cat > "$GUEST_DIR/init" <<'INIT'
#!/bin/busybox sh
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev 2>/dev/null || true
mkdir -p /data /run
ip link set lo up
ip link set eth0 up
ip addr add __GUEST_IP__/__NETMASK__ dev eth0
ip route add default via __HOST_IP__
echo "nameserver 1.1.1.1" > /etc/resolv.conf
echo "nameserver 9.9.9.9" >> /etc/resolv.conf

# data disk
if [ -b /dev/vdb ]; then
    mount -t ext4 /dev/vdb /data 2>/dev/null || {
        mkfs.ext4 -q /dev/vdb && mount -t ext4 /dev/vdb /data
    }
fi
mkdir -p /data/meshchatx

if [ ! -f /data/.installed ]; then
    echo "[init] first boot, running install"
    sh /opt/template/install.sh && touch /data/.installed
fi

echo "[init] starting meshchatx"
exec /bin/sh /opt/template/run.sh
INIT
    sed -i "s|__GUEST_IP__|$GUEST_IP|g; s|__HOST_IP__|$HOST_IP|g; s|__NETMASK__|$NETMASK|g" "$GUEST_DIR/init"
    chmod +x "$GUEST_DIR/init"

    # mkfs.ext4 -d populates the image without mounting (no root needed)
    truncate -s 1536M "$ROOTFS_IMG"
    mkfs.ext4 -q -d "$GUEST_DIR" "$ROOTFS_IMG"

    # persistent data disk
    if [ ! -f "$DATA_IMG" ]; then
        truncate -s 2048M "$DATA_IMG"
        mkfs.ext4 -q "$DATA_IMG"
    fi
    log "rootfs built at $ROOTFS_IMG"
}

# ---------- networking ----------

setup_net() {
    [ "$(id -u)" = "0" ] || die "network setup needs root - run: sudo $0"
    ip link show "$TAP" >/dev/null 2>&1 || ip tuntap add dev "$TAP" mode tap
    ip addr replace "$HOST_IP/$NETMASK" dev "$TAP" 2>/dev/null || ip addr add "$HOST_IP/$NETMASK" dev "$TAP"
    ip link set "$TAP" up
    sysctl -w net.ipv4.ip_forward=1 >/dev/null

    local wan
    wan="$(ip route show default | awk '/default/ {print $5; exit}')"
    [ -n "$wan" ] || die "no default route on host"

    nft add table ip meshchatx-mvm 2>/dev/null || true
    nft add chain ip meshchatx-mvm post '{ type nat hook postrouting priority 100; }' 2>/dev/null || true
    nft add rule ip meshchatx-mvm post oifname "$wan" masquerade 2>/dev/null || true
    nft add chain ip meshchatx-mvm prerouting '{ type nat hook prerouting priority -100; }' 2>/dev/null || true
    nft add rule ip meshchatx-mvm prerouting iifname "$wan" tcp dport "$HOST_PORT" dnat to "$GUEST_IP:$HOST_PORT" 2>/dev/null || true
    nft add rule ip meshchatx-mvm prerouting iifname "lo" tcp dport "$HOST_PORT" dnat to "$GUEST_IP:$HOST_PORT" 2>/dev/null || true
    log "NAT up: host:$HOST_PORT -> $GUEST_IP:$HOST_PORT via $wan"
}

teardown_net() {
    nft delete table ip meshchatx-mvm 2>/dev/null || true
    ip link del "$TAP" 2>/dev/null || true
    log "NAT + TAP removed"
}

# ---------- firecracker ----------

write_config() {
    cat > "$FC_CONFIG" <<EOF
{
    "boot-source": {
        "kernel_image_path": "$KERNEL_IMG",
        "boot_args": "console=ttyS0 reboot=k panic=1 pci=off init=/init"
    },
    "drives": [
        {
            "drive_id": "rootfs",
            "path_on_host": "$ROOTFS_IMG",
            "is_root_device": true,
            "is_read_only": false
        },
        {
            "drive_id": "data",
            "path_on_host": "$DATA_IMG",
            "is_root_device": false,
            "is_read_only": false
        }
    ],
    "machine-config": {
        "vcpu_count": $VCPUS,
        "mem_size_mib": $MEM_MIB
    },
    "network-interfaces": [
        {
            "iface_id": "eth0",
            "guest_mac": "AA:FC:00:00:00:01",
            "host_dev_name": "$TAP"
        }
    ],
    "logger": {
        "log_path": "$FC_LOG",
        "level": "Info",
        "show_level": true,
        "show_log_origin": true
    }
}
EOF
}

start_vm() {
    [ -f "$KERNEL_IMG" ] || fetch_kernel
    [ -f "$ROOTFS_IMG" ] || build_rootfs
    write_config
    rm -f "$FC_SOCKET"

    firecracker --api-sock "$FC_SOCKET" --config-file "$FC_CONFIG" \
        > "$FC_LOG.console" 2>&1 &
    echo $! > "$FC_PIDFILE"
    sleep 1
    kill -0 "$(cat "$FC_PIDFILE")" 2>/dev/null || die "firecracker failed to start - see $FC_LOG.console"
    log "firecracker up (pid $(cat "$FC_PIDFILE"), socket $FC_SOCKET)"
    log "meshchatx will be reachable at http://127.0.0.1:$HOST_PORT once first-boot install finishes"
    log "guest console: tail -f $FC_LOG.console"
}

stop_vm() {
    if [ -f "$FC_PIDFILE" ]; then
        kill "$(cat "$FC_PIDFILE")" 2>/dev/null || true
        rm -f "$FC_PIDFILE"
    fi
    teardown_net
}

# ---------- main ----------

case "${1:-}" in
    --build) preflight; mkdir -p "$STATE_DIR"; build_rootfs ;;
    --stop)  stop_vm ;;
    --status)
        if [ -f "$FC_PIDFILE" ] && kill -0 "$(cat "$FC_PIDFILE")" 2>/dev/null; then
            echo "running (pid $(cat "$FC_PIDFILE")) - http://127.0.0.1:$HOST_PORT"
        else
            echo "stopped"
        fi
        ;;
    *)
        preflight
        mkdir -p "$STATE_DIR"
        [ "${2:-}" = "--rebuild" ] && rm -f "$ROOTFS_IMG"
        [ -f "$ROOTFS_IMG" ] || build_rootfs
        [ -f "$KERNEL_IMG" ] || fetch_kernel
        setup_net
        start_vm
        ;;
esac
