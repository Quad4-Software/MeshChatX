# Reticulum MeshChatX

[English](../README.md) | [Русский](README.ru.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Umfassend modifizierter Fork von [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) von Liam Cottle. MeshChatX ergaenzt LXST-Anrufe, RRC Relay Chat, Nomad-Kartenoverlay, Plugins, rohes SQLite (ohne Peewee) und Electron-41-Desktopbuilds. Unabhaengig vom Upstream. Keine Zugehörigkeit.

- Website: [meshchatx.com](https://meshchatx.com)
- Forum: [forum.meshchatx.com](https://forum.meshchatx.com/)
- Quellcode: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Spenden: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

## Installation

Docker:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

PyPI (`pip` / `pipx` / `uv tool install reticulum-meshchatx`), dann `meshchatx --headless --host 127.0.0.1`.

Quellcode:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
# oder rngit:
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
make install && make build && make run
# oder: task install && task build && task run
```

Details: [`docs/en/installation.md`](../docs/en/installation.md).

Aktuelle Version in diesem Repository: `4.8.6`.

## Sicherheit, Lizenz, Credits

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Projektanteil: 0BSD. Upstream-MeshChat-Anteil: MIT. Volltext: [LICENSE](../LICENSE).
- Credits: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
