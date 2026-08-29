# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Fork di [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) di Liam Cottle. MeshChatX aggiunge chiamate LXST, RRC relay chat, overlay mappa Nomad, plugin, SQLite grezzo (senza Peewee) e build desktop Electron 41. Indipendente dall'upstream. Non affiliato.

- Sito: [meshchatx.com](https://meshchatx.com)
- Forum: [forum.meshchatx.com](https://forum.meshchatx.com/)
- Sorgente: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Mirror: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Donazioni: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

Guide complete in [`docs/en/`](../docs/en/) (inglese) e nella Documentation in-app:

| Guida                                                          | Contenuto                             |
| -------------------------------------------------------------- | ------------------------------------- |
| [Getting started](../docs/en/getting-started.md)               | Primi passi                           |
| [Installation](../docs/en/installation.md)                     | Docker, wheel, AppImage, deb/rpm, CLI |
| [Building](../docs/en/building.md)                             | Build offline, packaging, APK Android |
| [Development](../docs/en/development.md)                       | task/make, versioni, locale           |
| [Identities and security](../docs/en/identity-and-security.md) | Backup, corruzione DB, reset          |
| [Platform guides](../docs/en/platform-guides/)                 | Pi, Termux, Quest, sandbox Linux      |

## Avvio rapido

Requisiti: Python 3.11+, Node.js 24+, pnpm 11.1.2, UV.

```bash
docker compose up -d
```

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Versione attuale nel repository: `4.8.6`.

## Sicurezza, licenza, crediti

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Codice del progetto: 0BSD. Porzioni upstream MeshChat: MIT. Testo completo: [LICENSE](../LICENSE).
- Crediti: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
