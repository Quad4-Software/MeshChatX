# Init and packaging files for RNS FileSync

All system units run as non-root user rns-filesync with state under
/var/lib/rns-filesync. Prefer the systemd user unit when you do not want a
system account.

## Layout

- systemd/rns-filesync.service - hardened system unit
- systemd/rns-filesync.user.service - per-user unit (systemctl --user)
- openrc/rns-filesync - OpenRC script
- dinit/rns-filesync - dinit service
- runit/rns-filesync/run - runit run script
- sysusers.d/rns-filesync.conf - system user
- tmpfiles.d/rns-filesync.conf - state directories
- rns-filesync.env.example - optional env file

## systemd (system)

```bash
sudo install -m 644 packaging/sysusers.d/rns-filesync.conf /usr/lib/sysusers.d/
sudo install -m 644 packaging/tmpfiles.d/rns-filesync.conf /usr/lib/tmpfiles.d/
sudo systemd-sysusers
sudo systemd-tmpfiles --create
sudo install -m 644 packaging/systemd/rns-filesync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rns-filesync
```

Ensure /usr/bin/rns-filesync exists (package install or symlink).

## systemd (user)

```bash
mkdir -p ~/.config/systemd/user ~/Filesync
cp packaging/systemd/rns-filesync.user.service ~/.config/systemd/user/rns-filesync.service
systemctl --user daemon-reload
systemctl --user enable --now rns-filesync
```

Adjust ExecStart paths if rns-filesync is not in ~/.local/bin.

## OpenRC

```bash
sudo install -m 755 packaging/openrc/rns-filesync /etc/init.d/rns-filesync
sudo rc-update add rns-filesync default
sudo rc-service rns-filesync start
```

Create user rns-filesync first if your distro does not use sysusers.

## dinit

```bash
sudo install -m 644 packaging/dinit/rns-filesync /etc/dinit.d/rns-filesync
sudo dinitctl enable rns-filesync
```

## runit

```bash
sudo mkdir -p /etc/sv/rns-filesync
sudo install -m 755 packaging/runit/rns-filesync/run /etc/sv/rns-filesync/run
sudo ln -s /etc/sv/rns-filesync /var/service/
```

## Security notes

System units use NoNewPrivileges, ProtectSystem=strict, empty capability set,
and ReadWritePaths limited to /var/lib/rns-filesync. Sync ACL still comes from
~/.rns_filesync style config under that state directory.

## Sandboxing

For an extra filesystem boundary on a host install (pip, pipx, or package),
run under Bubblewrap. Network stays shared so Reticulum interfaces keep working.
Do not add --unshare-net unless you intend to isolate networking.

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

Notes:

- Only "$DATA" is writable. The rest of the root filesystem is read-only.
- Put config, sync tree, and Reticulum config under "$DATA" so the process
  does not need write access to your home directory.
- If rns-filesync lives in a venv outside "$DATA", --ro-bind / / still allows
  reading it. Bind that path read-write only if the venv must be mutated.
- For USB radios, device nodes under /dev are available via --dev /dev.
  Tighten further if your policy requires it.
- Docker and Podman are a separate isolation model. See docker/README.md.

## Service file tests (Docker)

Run packaging unit tests against appropriate OS images:

| Init | Image |
|------|-------|
| systemd | debian:bookworm-slim (+ systemd) |
| OpenRC | alpine:3.21 |
| dinit | debian:bookworm-slim (service file + command) |
| runit | Void Linux (Alpine fallback) |

```bash
./packaging/docker-test/run-all.sh
# or: make test-services
```
