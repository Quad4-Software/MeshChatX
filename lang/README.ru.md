# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Форк [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) от Liam Cottle. MeshChatX добавляет голосовые звонки LXST, RRC relay chat, оверлеи карты Nomad, плагины, сырой SQLite (без Peewee) и десктопные сборки Electron 41. Независим от upstream. Не связан с ним.

- Сайт: [meshchatx.com](https://meshchatx.com)
- Исходники: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Донаты: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

## Установка

Docker:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

PyPI (`pip` / `pipx` / `uv tool install reticulum-meshchatx`), затем `meshchatx --headless --host 127.0.0.1`.

Из исходников:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
# или rngit:
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
make install && make build && make run
# или: task install && task build && task run
```

Подробнее: [`docs/en/installation.md`](../docs/en/installation.md).

Текущая версия в репозитории: `4.8.6`.

## Безопасность, лицензия, благодарности

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Собственный код: 0BSD. Части upstream MeshChat: MIT. Полный текст: [LICENSE](../LICENSE).
- Credits: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
