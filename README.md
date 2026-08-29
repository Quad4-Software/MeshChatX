# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

Fork of [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) by Liam Cottle. MeshChatX adds LXST voice calls, RRC relay chat, Nomad map overlays, plugins, raw SQLite (no Peewee), and Electron 41 desktop builds. Independent from upstream. Not affiliated with it.

- Website: [meshchatx.com](https://meshchatx.com)
- Forum: [forum.meshchatx.com](https://forum.meshchatx.com/)
- Source: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Mirror: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Donate: [donate.md](donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`
- Umbrel: [apps.umbrel.com/app/meshchatx](https://apps.umbrel.com/app/meshchatx)

<a href="https://apps.obtainium.imranr.dev/redirect.html?r=obtainium://add/https://github.com/Quad4-Software/MeshChatX"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" height="60" alt="Get it on Obtainium"></a>

rngit NomadNet Node: `132f67e79d9b24aad014e93015fb858f:/page/index.mu`

## Install

Requirements for source builds: Python 3.11+, Node.js 24+, pnpm 11.1.2, UV. Web UI needs Safari 16.4, Chrome 111, or Firefox 128+. PyPI and Docker ship the built frontend (no Node on the runtime host).

### Docker

```bash
docker compose up -d
```

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Images: `quad4io/meshchatx` (Docker Hub) and `ghcr.io/quad4-software/meshchatx`. Hardened and extra tags are in [Installation](docs/en/installation.md).

### PyPI (pip, pipx, uv)

Package: [`reticulum-meshchatx`](https://pypi.org/project/reticulum-meshchatx/)

```bash
pip install reticulum-meshchatx
# or
pipx install reticulum-meshchatx
# or
uv tool install reticulum-meshchatx
```

```bash
meshchatx --headless --host 127.0.0.1
```

`meshchat` is the same entry point. Release wheels from GitHub also work: `pip install ./reticulum_meshchatx-*-py3-none-any.whl`.

### From source (git clone, make, task)

HTTPS:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
cd MeshChatX
```

Over Reticulum (rngit / `git-remote-rns`):

```bash
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
```

Then install and run with either Make or Task (same targets):

```bash
make install && make build && make run
```

```bash
task install && task build && task run
```

Or step through UV / pnpm yourself:

```bash
corepack enable
pnpm install --frozen-lockfile
uv sync --group dev
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

AppImage, deb, rpm, Electron, and Android: [Installation](docs/en/installation.md) and [Building](docs/en/building.md).

Current version is 4.8.6.

## Docs

| Guide                                                       | Covers                                 |
| ----------------------------------------------------------- | -------------------------------------- |
| [Getting started](docs/en/getting-started.md)               | First-day flow                         |
| [Installation](docs/en/installation.md)                     | Docker details, packages, CLI flags    |
| [Building](docs/en/building.md)                             | Offline builds, packaging, Android APK |
| [Development](docs/en/development.md)                       | task/make, versioning, locales         |
| [Identities and security](docs/en/identity-and-security.md) | Backups, corruption recovery, wipe     |
| [Platform guides](docs/en/platform-guides/)                 | Pi, Termux, Quest, Linux sandbox       |

## Changes from Reticulum MeshChat

LXST calls, [RRC](https://rrc.kc1awv.net/0) relay chat, MBTiles map plus remote KMZ/KML/GeoJSON overlays, raw SQL instead of Peewee, native fetch instead of Axios, Electron 41 (Node 24), wheels with built frontend, i18n, pnpm and UV.

## Security, license, credits

- [SECURITY.md](SECURITY.md) · [LEGAL.md](LEGAL.md) · [donate.md](donate.md)
- Project-owned code is 0BSD. Upstream MeshChat portions remain MIT. Full text: [LICENSE](LICENSE).
- Credits: [Liam Cottle](https://github.com/liamcottle) (original MeshChat), [RFnexus](https://github.com/RFnexus) (micron parser JS), [markqvist](https://github.com/markqvist) (Reticulum, LXMF, LXST).
