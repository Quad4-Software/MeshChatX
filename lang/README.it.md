# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Русский](README.ru.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Fork di [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) di Liam Cottle. MeshChatX aggiunge chiamate LXST, RRC relay chat, overlay mappa Nomad, plugin, SQLite grezzo (senza Peewee) e build desktop Electron 41. Indipendente dall'upstream. Non affiliato.

- Sito: [meshchatx.com](https://meshchatx.com)
- Sorgente: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Donazioni: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

## Installazione

Docker:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

PyPI (`pip` / `pipx` / `uv tool install reticulum-meshchatx`), poi `meshchatx --headless --host 127.0.0.1`.

Dal sorgente:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
# oppure rngit:
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
make install && make build && make run
# oppure: task install && task build && task run
```

Dettagli: [`docs/en/installation.md`](../docs/en/installation.md).

Versione attuale nel repository: `4.8.6`.

## Sicurezza, licenza, crediti

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Codice del progetto: 0BSD. Porzioni upstream MeshChat: MIT. Testo completo: [LICENSE](../LICENSE).
- Crediti: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
