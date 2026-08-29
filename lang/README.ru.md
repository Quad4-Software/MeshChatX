# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [中文](README.zh.md) | [日本語](README.ja.md)

Форк [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) от Liam Cottle. MeshChatX добавляет голосовые звонки LXST, RRC relay chat, оверлеи карты Nomad, плагины, сырой SQLite (без Peewee) и десктопные сборки Electron 41. Независим от upstream. Не связан с ним.

- Сайт: [meshchatx.com](https://meshchatx.com)
- Форум: [forum.meshchatx.com](https://forum.meshchatx.com/)
- Исходники: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Зеркало: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- Донаты: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

Подробные руководства: [`docs/en/`](../docs/en/) (на английском) и встроенная Documentation:

| Руководство                                                    | О чём                                 |
| -------------------------------------------------------------- | ------------------------------------- |
| [Getting started](../docs/en/getting-started.md)               | Первый запуск                         |
| [Installation](../docs/en/installation.md)                     | Docker, wheel, AppImage, deb/rpm, CLI |
| [Building](../docs/en/building.md)                             | Офлайн-сборки, packaging, Android APK |
| [Development](../docs/en/development.md)                       | task/make, версии, локали             |
| [Identities and security](../docs/en/identity-and-security.md) | Бэкапы, повреждение БД, сброс         |
| [Platform guides](../docs/en/platform-guides/)                 | Pi, Termux, Quest, Linux sandbox      |

## Быстрый старт

Нужны: Python 3.11+, Node.js 24+, pnpm 11.1.2, UV.

```bash
docker compose up -d
```

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Текущая версия в репозитории: `4.8.6`.

## Безопасность, лицензия, благодарности

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- Собственный код: 0BSD. Части upstream MeshChat: MIT. Полный текст: [LICENSE](../LICENSE).
- Credits: [Liam Cottle](https://github.com/liamcottle), [RFnexus](https://github.com/RFnexus), [markqvist](https://github.com/markqvist).
