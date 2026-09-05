# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [中文](README.zh.md)

[Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat)（Liam Cottle）の独立フォークです。MeshChatX は LXST 通話、RRC リレーチャット、Nomad 地図オーバーレイ、プラグイン、生の SQLite（Peewee なし）、Electron 41 デスクトップビルドを追加します。アップストリームとは無関係です。

- ウェブサイト: [meshchatx.com](https://meshchatx.com)
- ソース: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- PyPI: [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- 寄付: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

## インストール

Docker:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

PyPI（`pip` / `pipx` / `uv tool install reticulum-meshchatx`）、その後 `meshchatx --headless --host 127.0.0.1`。

ソースから:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
# または rngit:
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
make install && make build && make run
# または: task install && task build && task run
```

詳細は [`docs/en/installation.md`](../docs/en/installation.md)。

このリポジトリの現在のバージョンは `4.8.6` です。

## セキュリティ・ライセンス・クレジット

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- 本プロジェクト固有部分: 0BSD。同梱サードパーティは各ライセンス。全文: [LICENSE](../LICENSE)。
- クレジット: [Liam Cottle](https://github.com/liamcottle)、[RFnexus](https://github.com/RFnexus)、[markqvist](https://github.com/markqvist)。
