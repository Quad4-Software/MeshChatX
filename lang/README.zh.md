# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [日本語](README.ja.md)

[Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat)（Liam Cottle）的独立分支。MeshChatX 增加 LXST 语音通话、RRC 中继聊天、Nomad 地图叠加层、插件、原生 SQLite（无 Peewee）以及 Electron 41 桌面构建。与上游无关，无隶属关系。

- 网站: [meshchatx.com](https://meshchatx.com)
- 论坛: [forum.meshchatx.com](https://forum.meshchatx.com/)
- 源码: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- 捐赠: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

## 安装

Docker:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

PyPI（`pip` / `pipx` / `uv tool install reticulum-meshchatx`），然后 `meshchatx --headless --host 127.0.0.1`。

从源码:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
# 或 rngit:
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
make install && make build && make run
# 或: task install && task build && task run
```

详情见 [`docs/en/installation.md`](../docs/en/installation.md)。

本仓库当前版本: `4.8.6`。

## 安全、许可与致谢

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- 本项目自有代码：0BSD。上游 MeshChat 部分：MIT。全文：[LICENSE](../LICENSE)。
- 致谢：[Liam Cottle](https://github.com/liamcottle)、[RFnexus](https://github.com/RFnexus)、[markqvist](https://github.com/markqvist)。
