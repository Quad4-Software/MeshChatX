# RNS FileSync

Decentralized peer-to-peer file synchronization over the Reticulum Network Stack.

This package is designed as an embeddable library for host programs such as
MeshChatX and Sideband, with a thin CLI for standalone use. There is no TUI.

For usability and easy usage this follows rngit permissions and configuration.

## Features

- Peer-to-peer sync with no central server
- Delta sync for changed blocks
- Path-jailed writes and rngit-style ACL (permission:target)
- Embed-safe: reuses an existing RNS.Reticulum instance when present
- Works over any Reticulum medium (radio, LoRa, WiFi, internet)
- Daemon mode via --no-repl for init systems and containers

## Install

Over Reticulum with pip-rns (no internet required once you have a path):

```bash
pip-rns install rns://06a54b505bb67b25ef3f8097e8001edc/public/rns-filesync --pipx
```

From a release wheel over Reticulum (no source build):

```bash
pip-rns install --from-release rns://06a54b505bb67b25ef3f8097e8001edc/public/rns-filesync --ref v1.0.0 --pipx
```

From GitHub with pipx:

```bash
pipx install git+https://github.com/Quad4-Software/RNS-Filesync
```

From a local wheel:

```bash
make wheel
pipx install dist/rns_filesync-*.whl
# or: pip install dist/rns_filesync-*.whl
```

From a local checkout (development):

```bash
pip install -e ".[dev]"
# or: make install-user
```

Requires rns>=1.3.9. Current package version: **1.0.0**.

```bash
rns-filesync -v
# rns-filesync 1.0.0 | built 2026-07-19T12:00:00Z | commit abc1234
```

## Config

FileSync uses an rngit-like config directory (default `~/.rns_filesync/`):

```bash
rns-filesync -d ~/shared
# creates ~/.rns_filesync/config on first run
```

| Flag | Meaning |
|------|---------|
| `--config DIR` | FileSync config directory (default `~/.rns_filesync`) |
| `--rnsconfig DIR` | Reticulum config directory (default `~/.reticulum`) |
| `-d DIR` | Sync directory (overrides `[filesync] directory`) |

Example `~/.rns_filesync/config`:

```ini
[filesync]
announce_interval = 300
# directory = ~/shared
identity = rns_filesync
# peers = 9710b86ba12c42d1d8f30f74fe509286
# blocked_identities = d31aeea49873006f13b3415520666a4e

[aliases]
# alice = d09285e660cfe27cee6d9a0beb58b7e0

[access]
# sync = r:all, w:9710b86ba12c42d1d8f30f74fe509286, d:9710b86ba12c42d1d8f30f74fe509286

[logging]
loglevel = 4
```

Identities are stored under `~/.rns_filesync/identities/`.

## Permissions

Same rule form as rngit: `permission:target`.

| Perm | Meaning |
|------|---------|
| `r` | read |
| `w` | write |
| `d` | delete |
| `rw` | read/write |
| `rwd` | read/write/delete |
| `adm` | admin (all) |

Targets: identity hash, alias, `all`, or `none`.

When any ACL rule is loaded, access is **deny by default**. With no rules configured, the peer stays open (library/embed default).

Sidecar `.allowed` files (first found wins alongside config `[access]`):

- `<sync_dir>.allowed`
- `<parent>/<name>.allowed`
- `<sync_dir>/.allowed`

See `permissions.example`.

```bash
rns-filesync -d ~/shared --allow r:all --allow w:9710b86ba12c42d1d8f30f74fe509286
```

## CLI

```bash
rns-filesync -d ~/shared
rns-filesync -d ~/shared -p <peer_identity_hash>
rns-filesync --config ~/.rns_filesync --rnsconfig ~/.reticulum -d ~/shared
rns-filesync -v
rns-filesync --version
```

`-v` / `--version` prints version, bake build date, and git commit when available.

`-p` expects a peer **identity hash**. A destination hash is accepted as fallback
after the peer has announced.

Interactive commands: `status`, `peers`, `files`, `connect`, `disconnect`,
`browse`, `download`, `announce`, `quit`.

Logging verbosity uses `--verbose` (repeatable). Quiet mode is `-q`.

## Man page

```bash
make install-user   # installs man page to ~/.local/share/man/man1/
man rns-filesync
```

## Library embed (MeshChatX-style)

```python
from rns_filesync import FileSyncService
from rns_filesync.permissions import PermissionStore

perms = PermissionStore()
perms.add_rule("r:all")
perms.add_rule("w:9710b86ba12c42d1d8f30f74fe509286")

service = FileSyncService(
    identity=host_identity,
    sync_directory="/path/to/sync",
    reticulum=existing_reticulum,
    permissions=perms,
)
dest_hash = service.start(monitor=True)
service.connect_peer(peer_identity_hash)
service.stop()
```

Keep aspect `rns_filesync.filesync` for wire compatibility.

## Sideband plugin

Install `rns-filesync` into the same Python environment Sideband uses, then copy
the drop-in plugins from `sideband/` into Sideband's plugins directory and
enable service/command plugins in Sideband settings.

```bash
# After installing rns-filesync (pip / pipx / pip-rns):
cp sideband/rns_filesync_service.py ~/.config/sideband/plugins/
cp sideband/rns_filesync_command.py ~/.config/sideband/plugins/
```

Set Sideband's plugin path to that directory, enable **service plugins** and
**command plugins**, then restart Sideband.

The service plugin reuses Sideband's identity and Reticulum instance. Sync
directory, peers, and ACL come from `~/.rns_filesync/config`. If no directory
is set there, it defaults to `~/.config/sideband/filesync`.

Remote LXMF commands (from a peer allowed to run Sideband commands):

```text
filesync status
filesync peers
filesync files
filesync announce
filesync connect <identity_hash>
filesync disconnect <peer_id>
```

## Daemon and packaging

Init units (non-root) live under packaging/ for systemd (system and user),
OpenRC, dinit, and runit. See packaging/README.md.

```bash
# system (dedicated rns-filesync user, hardened)
sudo systemctl enable --now rns-filesync

# or per-user
systemctl --user enable --now rns-filesync
```

Daemon entrypoint:

```bash
rns-filesync -d ~/shared --no-repl -q
```

Bubblewrap sandbox example (full command in packaging/README.md):

```bash
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/rns-filesync-sandbox"
mkdir -p "$DATA/config" "$DATA/sync" "$DATA/reticulum"

exec bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --uid "$(id -u)" --gid "$(id -g)" \
  rns-filesync \
    --config "$DATA/config" \
    --rnsconfig "$DATA/reticulum" \
    -d "$DATA/sync" \
    --no-repl \
    -q
```

## Docker

Rootless multi-stage image and wheel builder under docker/. See docker/README.md.

```bash
docker build -f docker/Dockerfile -t rns-filesync:1.0.0 .
```

## Tests

```bash
make test
pytest -m "not live and not exploratory"
pytest -m e2e
pytest -m live
```

Markers: `unit`, `acceptance`, `smoke`, `e2e`, `fuzz`, `live`, `exploratory`.

Useful Make targets (aligned with pip-rns): `meta`, `wheel`, `sdist`, `test`,
`install-user`, `man`, `sign`, `release-rns`, `clean`, `test-services`.

## License

BSD-2-Clause. See LICENSE.
