# Proxmox deployment

Two options:

## VM template (cloud-init)

`build-vm-template.sh` creates a Debian 13 cloud-image VM template with
Docker, cloud-init, and MeshChatX as a systemd unit. Run on the Proxmox host:

```bash
bash proxmox/build-vm-template.sh --vmid 9000 --name meshchatx-template \
    --storage local-lvm --bridge vmbr0
```

Then clone the template in the GUI, set the cloud-init user/SSH key, and
boot. MeshChatX is available at `https://<vm-ip>:8000`.

## LXC container

`build-lxc.sh` creates a Debian 13 LXC running Docker + MeshChatX.
Requires nesting (`features: nesting=1`) for Docker inside LXC:

```bash
bash proxmox/build-lxc.sh --ctid 200 --name meshchatx \
    --storage local-lvm --bridge vmbr0 --ip 192.168.1.50/24 --gw 192.168.1.1
```
