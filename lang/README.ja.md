# Reticulum MeshChatX

Liam Cottle 氏による Reticulum MeshChat を大幅に改修・機能拡張したフォークです。

本プロジェクトはオリジナルの Reticulum MeshChat とは独立しており、提携関係にありません。

- ソースコード: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- リリース: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- 変更履歴: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [`TODO.md`](../TODO.md)
- [English README](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [中文](README.zh.md)

## 重要事項

- LXMF の完全サポートがプロジェクトの中核目標です。
- データ保存とマイグレーションは段階的に直接 SQL へ移行中です（レガシーの Peewee ORM パスを置換）。

> [!WARNING]
> MeshChatX は旧バージョンの Reticulum MeshChat とのデータ互換性を保証しません。マイグレーションやテスト前にデータをバックアップしてください。

> [!WARNING]
> レガシーシステムはまだ完全にはサポートされていません。現在の最低要件: Python `>=3.11`、Node `>=24`。

## デモとスクリーンショット

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

### UI プレビュー

![電話](../screenshots/phone.png)
![ネットワークビジュアライザ](../screenshots/network-visualiser.png)
![アーカイブ](../screenshots/archives.png)
![アイデンティティ](../screenshots/identities.png)

## 必要条件

- Python `>=3.11`（`pyproject.toml` より）
- Node.js `>=24`（`package.json` より）
- pnpm `10.30.0`（`package.json` より）
- Poetry（`Taskfile.yml` および CI ワークフローで使用）

## Nix (flake.nix)

リポジトリに `flake.nix` が含まれています。

### 開発シェルに入る

```bash
nix develop
```

### デフォルトの Nix パッケージをビルド

```bash
nix build .#default
```

### `nix develop` 内の典型的なワークフロー

```bash
task install
task lint:all
task test:all
task build:all
```

## インストール方法

| 方法                       | フロントエンド含む | アーキテクチャ                        | 最適な用途                               |
| -------------------------- | ------------------ | ------------------------------------- | ---------------------------------------- |
| Docker イメージ            | はい               | `linux/amd64`, `linux/arm64`          | Linux サーバーでの最速セットアップ       |
| Python wheel (`.whl`)      | はい               | Python がサポートする全アーキテクチャ | Node ビルド不要のヘッドレス/Web サーバー |
| Linux AppImage             | はい               | `x64`, `arm64`                        | ポータブルデスクトップ                   |
| Debian パッケージ (`.deb`) | はい               | `x64`, `arm64`                        | Debian/Ubuntu                            |
| RPM パッケージ (`.rpm`)    | はい               | CI 依存                               | Fedora/RHEL/openSUSE                     |
| ソースから                 | ローカルビルド     | ホストアーキテクチャ                  | 開発・カスタムビルド                     |

備考:

- リリースワークフローは Linux `x64` および `arm64` の AppImage + DEB を明示的にビルドします。
- RPM もビルドが試みられ、成功時にアップロードされます。

## クイックスタート: Docker

```bash
docker compose up -d
```

デフォルトの compose ファイル:

- ホスト `127.0.0.1:8000` -> コンテナポート `8000`
- `./meshchat-config` -> `/config`（永続化用）

権限エラーが発生した場合:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

## リリースアーティファクトからのインストール

### 1) Linux AppImage (x64/arm64)

1. リリースから `ReticulumMeshChatX-v<バージョン>-linux-<アーキテクチャ>.AppImage` をダウンロード。
2. 実行権限を付与して起動:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. `ReticulumMeshChatX-v<バージョン>-linux-<アーキテクチャ>.deb` をダウンロード。
2. インストール:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) RPM ベースのシステム

1. リリースに `ReticulumMeshChatX-v<バージョン>-linux-<アーキテクチャ>.rpm` がある場合はダウンロード。
2. インストール:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

リリースの wheel にはビルド済みの Web アセットが含まれています。

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchat --headless
```

`pipx` もサポート:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## ソースからの実行（Web サーバーモード）

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run meshchat --headless --host 127.0.0.1
```

## ソースからのデスクトップパッケージビルド

### Linux x64 AppImage + DEB

```bash
pnpm run dist:linux-x64
```

### Linux arm64 AppImage + DEB

```bash
pnpm run dist:linux-arm64
```

### RPM

```bash
pnpm run dist:rpm
```

## アーキテクチャサポート

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（ビルドスクリプトあり）
- macOS: ビルドスクリプトあり（`arm64`, `universal`）
- Android: リポジトリにプロジェクトと CI ワークフローあり

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## 設定

| 引数            | 環境変数               | デフォルト  | 説明                               |
| --------------- | ---------------------- | ----------- | ---------------------------------- |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1` | Web サーバーバインドアドレス       |
| `--port`        | `MESHCHAT_PORT`        | `8000`      | Web サーバーポート                 |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`     | HTTPS を無効化                     |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`     | ブラウザを自動で開かない           |
| `--auth`        | `MESHCHAT_AUTH`        | `false`     | 基本認証を有効化                   |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage` | データディレクトリ                 |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | 自動        | フロントエンドファイルディレクトリ |

## ブランチ

| ブランチ | 目的                                                         |
| -------- | ------------------------------------------------------------ |
| `master` | 安定版リリース。本番環境対応コードのみ。                     |
| `dev`    | 活発な開発中。不安定または不完全な変更を含む場合があります。 |

## 開発

```bash
task install
task lint:all
task test:all
task build:all
```

## セキュリティ

- [`SECURITY.md`](../SECURITY.md)
- 組み込みの整合性チェックと HTTPS/WSS デフォルト設定
- `.gitea/workflows/` の CI スキャンワークフロー

## クレジット

- [Liam Cottle](https://github.com/liamcottle) - オリジナル Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - JavaScript Micron パーサー
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
