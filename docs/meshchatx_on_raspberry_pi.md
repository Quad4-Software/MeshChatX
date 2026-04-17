# MeshChatX on Raspberry Pi

This guide shows a simple headless setup for running MeshChatX on a Raspberry Pi 4
with a web UI you can access from another device on your network.

This install path uses a release wheel, which already includes frontend assets.

## Automated Setup Scripts

If you want one-command setup, use the interactive installer from repo root:

```bash
bash scripts/rpi/install_meshchatx.sh
```

The installer guides you through:

- Optional `espeak-ng` install (tries apt/dnf/pacman)
- Install method (`pipx` or `venv + pip`)
- Storage and Reticulum directories
- Bind host and port (with availability check)
- HTTPS on/off (default on)
- Service mode (`system`, `user`, or `none`)
- Service startup verification (`Running on ...`)

If startup validation fails, it prints recent logs and stops the service to avoid
restart loops.

The installer also applies compatibility dependencies needed by older wheel
releases.

For all options:

```bash
bash scripts/rpi/install_meshchatx.sh --help
```

## 1) Install Base Dependencies

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip pipx
```

## 2) Enable pipx Path

```bash
pipx ensurepath
source ~/.profile
```

If `pipx` is not available in your distro package repo, install it with:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
source ~/.profile
```

## 3) Install MeshChatX with pipx (recommended)

Preferred option (recommended): install from a release wheel (4.4.0 or newer),
because the wheel bundles frontend assets.

```bash
pipx install /path/to/reticulum_meshchatx-<version>-py3-none-any.whl
```

Direct example (v4.4.0):

```bash
pipx install "https://git.quad4.io/RNS-Things/MeshChatX/releases/download/v4.4.0/reticulum_meshchatx-4.4.0-py3-none-any.whl"
```

`py3-none-any` wheels are architecture-independent, so the same wheel artifact
works on Raspberry Pi ARM and x86_64 Linux systems.

Upgrade example:

```bash
pipx upgrade meshchatx
```

## 4) Install MeshChatX without pipx (venv + pip)

If you prefer not to use pipx:

```bash
mkdir -p ~/meshchatx
cd ~/meshchatx
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "https://git.quad4.io/RNS-Things/MeshChatX/releases/download/v4.4.0/reticulum_meshchatx-4.4.0-py3-none-any.whl"
```

Run command in venv mode:

```bash
~/meshchatx/.venv/bin/meshchatx --headless --host 0.0.0.0 --port 8000
```

## 5) Run MeshChatX (Headless)

```bash
meshchatx --headless --host 0.0.0.0 --port 8000
```

Then open:

```text
http://<pi-ip>:8000
```

## 6) Configure a systemd Service

`systemd` keeps MeshChatX running in the background and starts it automatically
on boot.

You have two service styles:

- System service (`/etc/systemd/system/...`) for always-on host services.
- User service (`~/.config/systemd/user/...`) for per-user sessions.

### Option A: System service (recommended for Pi node/server use)

Create `/etc/systemd/system/meshchatx.service`:

```ini
[Unit]
Description=MeshChatX Headless (system service)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/meshchatx
Environment="PATH=/home/pi/.local/bin:/usr/bin:/bin"
ExecStart=/home/pi/.local/bin/meshchatx --headless --host 0.0.0.0 --port 8000 --storage-dir /home/pi/meshchatx/storage --reticulum-config-dir /home/pi/.reticulum
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

The above service file is for pipx installs. For venv installs, use:

```ini
[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/meshchatx
Environment="PATH=/home/pi/meshchatx/.venv/bin:/usr/bin:/bin"
ExecStart=/home/pi/meshchatx/.venv/bin/meshchatx --headless --host 0.0.0.0 --port 8000 --storage-dir /home/pi/meshchatx/storage --reticulum-config-dir /home/pi/.reticulum
Restart=always
RestartSec=3
```

Update `User`, `Group`, and paths if your install location is different.

Enable and start:

```bash
mkdir -p /home/pi/meshchatx/storage /home/pi/.reticulum
sudo chown -R pi:pi /home/pi/meshchatx
sudo systemctl daemon-reload
sudo systemctl enable --now meshchatx.service
sudo systemctl status meshchatx.service
```

### Option B: User service (no sudo system unit)

Create `~/.config/systemd/user/meshchatx.service`:

```ini
[Unit]
Description=MeshChatX Headless (user service)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/meshchatx
Environment="PATH=%h/.local/bin:/usr/bin:/bin"
ExecStart=%h/.local/bin/meshchatx --headless --host 0.0.0.0 --port 8000 --storage-dir %h/meshchatx/storage --reticulum-config-dir %h/.reticulum
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```

Enable/start user service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now meshchatx.service
systemctl --user status meshchatx.service
```

If you want user services to stay active without login:

```bash
sudo loginctl enable-linger pi
```

### Service management commands

```bash
sudo systemctl restart meshchatx.service
sudo systemctl stop meshchatx.service
sudo systemctl disable meshchatx.service
```

Useful logs and troubleshooting:

```bash
journalctl -u meshchatx.service -f
journalctl -u meshchatx.service -n 200 --no-pager
systemctl show meshchatx.service -p ExecStart -p User -p Group
```

## Notes

- Reticulum configuration and identity data are stored in the service user's home
  directory by default (for example `~/.reticulum` and MeshChatX storage paths).
- If you attach RNode hardware by USB, make sure the service user has permission
  to access serial devices (`dialout` group on Debian-based systems).
