# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [中文](README.zh.md)

[Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat)（Liam Cottle）の独立フォークです。MeshChatX は LXST 通話、RRC リレーチャット、Nomad 地図オーバーレイ、プラグイン、生の SQLite（Peewee なし）、Electron 41 デスクトップビルドを追加します。アップストリームとは無関係です。

- ウェブサイト: [meshchatx.com](https://meshchatx.com)
- フォーラム: [forum.meshchatx.com](https://forum.meshchatx.com/)
- ソース: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- ミラー: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Changelog: [CHANGELOG.md](../CHANGELOG.md)
- 寄付: [donate.md](../donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`

詳細ガイドは [`docs/en/`](../docs/en/)（英語）とアプリ内 Documentation にあります。

| ガイド                                                         | 内容                                      |
| -------------------------------------------------------------- | ----------------------------------------- |
| [Getting started](../docs/en/getting-started.md)               | はじめに                                  |
| [Installation](../docs/en/installation.md)                     | Docker、wheel、AppImage、deb/rpm、CLI     |
| [Building](../docs/en/building.md)                             | オフラインビルド、パッケージ、Android APK |
| [Development](../docs/en/development.md)                       | task/make、バージョン、ロケール           |
| [Identities and security](../docs/en/identity-and-security.md) | バックアップ、DB 破損、データ削除         |
| [Platform guides](../docs/en/platform-guides/)                 | Pi、Termux、Quest、Linux サンドボックス   |

## クイックスタート

要件: Python 3.11+、Node.js 24+、pnpm 11.1.2、UV。

```bash
docker compose up -d
```

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

このリポジトリの現在のバージョンは `4.8.6` です。

## セキュリティ・ライセンス・クレジット

- [SECURITY.md](../SECURITY.md) · [LEGAL.md](../LEGAL.md) · [donate.md](../donate.md)
- 本プロジェクト固有部分: 0BSD。上流 MeshChat 部分: MIT。全文: [LICENSE](../LICENSE)。
- クレジット: [Liam Cottle](https://github.com/liamcottle)、[RFnexus](https://github.com/RFnexus)、[markqvist](https://github.com/markqvist)。
