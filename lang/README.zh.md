# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [日本語](README.ja.md)

[Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat)（Liam Cottle）的独立分支。MeshChatX 增加 LXST 语音通话、RRC 中继聊天、Nomad 地图叠加层、插件、原生 SQLite（无 Peewee）以及 Electron 41 桌面构建。与上游无关，无隶属关系。

- 网站: [meshchatx.com](https://meshchatx.com)
- 论坛: [forum.meshchatx.com](https://forum.meshchatx.com/)
- 源码: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- 镜像: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- 捐赠: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

完整指南见 [`docs/en/`](../docs/en/)（英文）及应用内 Documentation：

| 指南                                                           | 内容                                  |
| -------------------------------------------------------------- | ------------------------------------- |
| [Getting started](../docs/en/getting-started.md)               | 入门                                  |
| [Installation](../docs/en/installation.md)                     | Docker、wheel、AppImage、deb/rpm、CLI |
| [Building](../docs/en/building.md)                             | 离线构建、打包、Android APK           |
| [Development](../docs/en/development.md)                       | task/make、版本、语言包               |
| [Identities and security](../docs/en/identity-and-security.md) | 备份、数据库损坏、清除数据            |
| [Platform guides](../docs/en/platform-guides/)                 | Pi、Termux、Quest、Linux 沙箱         |

## 快速开始

需要：Python 3.11+、Node.js 24+、pnpm 11.1.2、UV。

```bash
docker compose up -d
```

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

本仓库当前版本: `4.8.6`。

## 安全、许可与致谢

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- 本项目自有代码：0BSD。上游 MeshChat 部分：MIT。全文：[LICENSE](../LICENSE)。
- 致谢：[Liam Cottle](https://github.com/liamcottle)、[RFnexus](https://github.com/RFnexus)、[markqvist](https://github.com/markqvist)。
