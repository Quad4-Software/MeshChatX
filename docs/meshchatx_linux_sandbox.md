# MeshChatX on Linux: Firejail and Bubblewrap

This page shows how to run **`meshchatx`** under **Firejail** or **Bubblewrap** (`bwrap`) on Linux. The legacy CLI name **`meshchat`** installs the same entry point and can be substituted in these examples. Use this when you install MeshChatX natively (wheel, package, or Poetry) and want an extra layer of filesystem and process isolation compared to running the binary directly.

These tools do **not** replace a full virtual machine or hardware-enforced boundary. They reduce exposure of your home directory and other paths the process can write to, when you configure them with tight whitelists or bind mounts.

**Containers:** If you already run MeshChatX with Docker or Podman, that is a different isolation model; this document is aimed at **host-installed** `meshchatx` (or `meshchat`).

## Prerequisites

Install one or both from your distribution:

- **Firejail:** package name is usually `firejail`.
- **Bubblewrap:** package name is usually `bubblewrap`; the binary is `bwrap`.

You need a working **`meshchatx`** on your `PATH` (for example after `pipx install`, `pip install --user`, or a distro package). The **`meshchat`** command is the same binary if both entry points are installed.

Pick a **dedicated data directory** for sandboxed runs so you do not mix permissions or policies with a non-sandboxed install. The examples below use:

```bash
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/meshchatx-sandbox"
mkdir -p "$DATA/storage" "$DATA/.reticulum"
```

Adjust paths if you prefer another location.

## Firejail

Firejail applies a profile (or defaults) on top of your command. For MeshChatX you typically want:

- **Network** left available so Reticulum and the web UI can work (do not use `--net=none` unless you know you need it).
- **Writable** only your chosen data directory (and anything else the app truly needs).

### Installed `meshchatx` (pip, pipx, or system package)

```bash
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/meshchatx-sandbox"
mkdir -p "$DATA/storage" "$DATA/.reticulum"

firejail --quiet \
  --whitelist="$DATA" \
  meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

If the default profile blocks something MeshChatX needs, you can start from a looser base and tighten later, for example:

```bash
firejail --noprofile --whitelist="$DATA" \
  meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

`--noprofile` disables many Firejail restrictions; treat it as a stepping stone, not the final hardening.

### From source with Poetry

Poetry needs the project tree and the virtualenv. Example:

```bash
cd /path/to/reticulum-meshchatX
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/meshchatx-sandbox"
VENV="$(poetry env info -p)"
mkdir -p "$DATA/storage" "$DATA/.reticulum"

firejail --quiet \
  --whitelist="$(pwd)" \
  --whitelist="$VENV" \
  --whitelist="$DATA" \
  poetry run meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

You may need extra `--whitelist=` entries if Poetry or dependencies read config elsewhere (for example under `$HOME/.config`).

### USB serial (RNode or similar)

If Reticulum talks to a radio over a serial device, Firejail may need explicit access to TTY devices, for example:

```bash
firejail --noblacklist=/dev/ttyACM0 --noblacklist=/dev/ttyUSB0 \
  ...
```

Use the device nodes your system actually exposes (`dmesg`, `ls /dev/tty*`).

## Bubblewrap (`bwrap`)

Bubblewrap does not ship profiles; you list every mount and option. The pattern below keeps the **whole root filesystem read-only**, mounts a **writable tmpfs** on `/tmp`, and makes **only** your data directory writable at its normal path. **Network namespaces are not changed**, so Reticulum and TCP/UDP behave like an unsandboxed process unless you add `--unshare-net` (which usually breaks mesh networking).

### Installed `meshchatx`

```bash
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/meshchatx-sandbox"
mkdir -p "$DATA/storage" "$DATA/.reticulum"

exec bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --uid "$(id -u)" --gid "$(id -g)" \
  meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

Notes:

- If `meshchatx` lives only inside a venv that is **not** under `$DATA`, the read-only root still allows **reading** that path; you do not have to bind-mount the venv separately unless you also need writes there.
- Distributions that merge `/` and `/usr` (merged-usr) still work with `--ro-bind / /` on typical glibc setups. If `bwrap` fails with missing library paths, add the extra `--ro-bind` lines your distro documents (for example `/lib64`).

### From source with Poetry

Bind the repository and the Poetry venv read-only, and keep `DATA` writable:

```bash
cd /path/to/reticulum-meshchatX
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/meshchatx-sandbox"
VENV="$(poetry env info -p)"
mkdir -p "$DATA/storage" "$DATA/.reticulum"
PROJ="$(pwd)"

exec bwrap \
  --die-with-parent \
  --new-session \
  --proc /proc \
  --dev /dev \
  --ro-bind / / \
  --tmpfs /tmp \
  --bind "$DATA" "$DATA" \
  --ro-bind "$PROJ" "$PROJ" \
  --ro-bind "$VENV" "$VENV" \
  --uid "$(id -u)" --gid "$(id -g)" \
  --setenv PATH "$VENV/bin:$PATH" \
  --chdir "$PROJ" \
  poetry run meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

`poetry` itself must be reachable on `PATH` inside the sandbox (often under `/usr` or `$HOME/.local/bin`, both visible with `--ro-bind / /`). If `poetry run` fails because it cannot read `~/.config/poetry`, add a read-only bind for that directory or invoke the venv interpreter directly instead of `poetry run`:

```bash
exec bwrap \
  ... same mounts as above ... \
  --setenv PATH "$VENV/bin:$PATH" \
  --chdir "$PROJ" \
  meshchatx --headless --host 127.0.0.1 \
    --storage-dir="$DATA/storage" \
    --reticulum-config-dir="$DATA/.reticulum"
```

(Use the `meshchatx` script, the legacy `meshchat` alias, or `python -m` entry point from `$VENV/bin` if your install exposes it there.)

### USB serial under Bubblewrap

You may need a clearer view of devices than the minimal `--dev /dev` provides. Options include `--dev-bind /dev /dev` (broader device exposure) or binding only the specific character device. Balance convenience against attack surface.
