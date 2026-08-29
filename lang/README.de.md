# Reticulum MeshChatX

[English](../README.md) | [Русский](README.ru.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Umfassend modifizierter Fork von [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) von Liam Cottle. MeshChatX ergaenzt LXST-Anrufe, RRC Relay Chat, Nomad-Kartenoverlay, Plugins, rohes SQLite (ohne Peewee) und Electron-41-Desktopbuilds. Unabhaengig vom Upstream. Keine Zugehörigkeit.

- Website: [meshchatx.com](https://meshchatx.com)
- Forum: [forum.meshchatx.com](https://forum.meshchatx.com/)
- Quellcode: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Spiegel: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Spenden: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

Ausfuehrliche Anleitungen stehen unter [`docs/en/`](../docs/en/) (englisch) und in der In-App-Dokumentation:

| Leitfaden                                                      | Inhalt                                 |
| -------------------------------------------------------------- | -------------------------------------- |
| [Getting started](../docs/en/getting-started.md)               | Einstieg                               |
| [Installation](../docs/en/installation.md)                     | Docker, Wheel, AppImage, deb/rpm, CLI  |
| [Building](../docs/en/building.md)                             | Offline-Builds, Packaging, Android-APK |
| [Development](../docs/en/development.md)                       | task/make, Versionierung, Locales      |
| [Identities and security](../docs/en/identity-and-security.md) | Backups, Korruption, Wipe              |
| [Platform guides](../docs/en/platform-guides/)                 | Pi, Termux, Quest, Linux-Sandbox       |

## Schnellstart

Voraussetzungen: Python 3.11+, Node.js 24+, pnpm 11.1.2, UV.

```bash
docker compose up -d
```

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Aktuelle Version in diesem Repository: `4.8.6`.

## Sicherheit, Lizenz, Credits

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Projektanteil: 0BSD. Upstream-MeshChat-Anteil: MIT. Volltext: [LICENSE](../LICENSE).
- Credits: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
