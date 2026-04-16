# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [中文](README.zh.md)

Liam Cottle 氏による Reticulum MeshChat を大幅に改修・機能拡張したフォークです。

本プロジェクトはオリジナルの Reticulum MeshChat とは独立しており、提携関係にありません。

- ウェブサイト: [meshchatx.com](https://meshchatx.com)
- ソースコード: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- 公式ミラー: [github.com/Quad4/MeshChatX](https://github.com/Quad4/MeshChatX) — 現時点では Windows / macOS ビルドにも使用。
- リリース: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- 変更履歴: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Reticulum MeshChat からの主な変更

- LXST を使用
- Peewee ORM を生 SQL に置き換え
- Axios をネイティブ `fetch` に置き換え
- 最新の Electron
- Web サーバーと同梱フロントエンドを含む `.whl` によりデプロイの選択肢を拡張
- i18n
- 依存関係管理に PNPM と Poetry

> [!WARNING]
> MeshChatX は旧バージョンの Reticulum MeshChat とのデータ互換性を保証しません。マイグレーションやテスト前にデータをバックアップしてください。

> [!WARNING]
> レガシーシステムはまだ完全にはサポートされていません。現在の最低要件: Python `>=3.11`、Node `>=24`。

## 必要条件

- Python `>=3.11`（`pyproject.toml` より）
- Node.js `>=24`（`package.json` より）
- pnpm `10.32.1`（`package.json` より）
- Poetry（`Taskfile.yml` および CI ワークフローで使用）

```bash
task install
task lint:all
task test:all
task build:all
```

## インストール方法

環境とパッケージ形式に合わせて選んでください。

| 方法                       | フロントエンド含む | アーキテクチャ                        | 最適な用途                               |
| -------------------------- | ------------------ | ------------------------------------- | ---------------------------------------- |
| Docker イメージ            | はい               | `linux/amd64`, `linux/arm64`          | Linux サーバーでの迅速なセットアップ     |
| Python wheel (`.whl`)      | はい               | Python がサポートする全アーキテクチャ | Node ビルド不要のヘッドレス/Web サーバー |
| Linux AppImage             | はい               | `x64`, `arm64`                        | ポータブルデスクトップ                   |
| Debian パッケージ (`.deb`) | はい               | `x64`, `arm64`                        | Debian/Ubuntu                            |
| RPM パッケージ (`.rpm`)    | はい               | CI 依存                               | Fedora/RHEL/openSUSE                     |
| ソースから                 | ローカルビルド     | ホストアーキテクチャ                  | 開発・カスタムビルド                     |

備考:

- リリースワークフローは Linux `x64` および `arm64` の AppImage + DEB を明示的にビルドします。
- RPM も試行され、成功時にアップロードされます。

## クイックスタート: Docker

```bash
docker compose up -d
```

デフォルトの compose ファイル:

- ホスト `127.0.0.1:8000` -> コンテナポート `8000`
- `./meshchat-config` -> `/config`（永続化）

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

リリースの wheel にはビルド済みの Web アセットが含まれます。

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

`pipx` もサポート:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## ソースからの実行（Web サーバーモード）

開発時やローカルのカスタムビルド向け。

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

## サンドボックスで実行（Linux）

ネイティブの `meshchatx`（エイリアス: `meshchat`）をファイルシステムをより隔離した状態で動かすには、Reticulum と Web UI 向けの通常のネットワークアクセスを保ちつつ **Firejail** または **Bubblewrap**（`bwrap`）を使えます。詳しい例（pip/pipx、Poetry、USB シリアルの注意）は次を参照:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

同梱または同期された `meshchatx-docs` から配信される場合、アプリ内の **ドキュメント**（MeshChatX ドキュメント）一覧にも同じページが表示されます。

## Linux デスクトップ: 絵文字フォント

絵文字ピッカーはシステムフォント（Electron/Chromium）で標準 Unicode 絵文字を描画します。絵文字が空の四角（「豆腐」）になる場合はカラー絵文字パッケージをインストールし、アプリを再起動してください。

| ディストリビューション（例） | パッケージ                                                            |
| ---------------------------- | --------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro   | `noto-fonts-emoji`（`sudo pacman -S noto-fonts-emoji`）               |
| Debian, Ubuntu               | `fonts-noto-color-emoji`（`sudo apt install fonts-noto-color-emoji`） |
| Fedora                       | `google-noto-emoji-color-fonts`                                       |

インストール後も表示されない場合は `fc-cache -fv` を実行してください。最小インストールでは記号の網羅用に `noto-fonts` も任意で入れてください。

## ソースからのデスクトップパッケージビルド

スクリプトは `package.json` と `Taskfile.yml` に定義されています。

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

Task 経由:

```bash
task dist:fe:rpm
```

## アーキテクチャサポート

- Docker イメージ: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（ビルドスクリプトあり）
- macOS: ローカルビルド向けにビルドスクリプトあり（`arm64`, `universal`）
- Android: ネイティブ APK — ABI `arm64-v8a`、`x86_64`、および universal

## Android

MeshChatX はネイティブ Android APK のビルドに対応しています（Termux のみに限りません）。

### ソースから APK をビルド

リポジトリのルートで:

```bash
# 1) android/app/build.gradle で使う Chaquopy 用ホイールをビルド
bash scripts/build-android-wheels-local.sh

# 2) 両方の APK バリアントをビルド
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

APK の出力（ABI 分割と universal APK。`android/app/build.gradle` の `splits { abi { ... } }` を参照）:

デバッグ（`android/app/build/outputs/apk/debug/`）:

- `app-arm64-v8a-debug.apk`（ARM64 端末）
- `app-x86_64-debug.apk`（x86_64 エミュレータ）
- `app-universal-debug.apk`（同梱 ABI を 1 パッケージに）

リリース（`android/app/build/outputs/apk/release/`）:

- `app-arm64-v8a-release-unsigned.apk`
- `app-x86_64-release-unsigned.apk`
- `app-universal-release-unsigned.apk`

備考:

- リリース出力は署名を設定しない限りデフォルトで未署名です。
- どちらか一方でよい場合は `:app:assembleDebug` または `:app:assembleRelease`。
- Android の対象 ABI は `android/app/build.gradle` で設定されている `arm64-v8a` と `x86_64` です。

追加ドキュメント:

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## 設定

| 引数                       | 環境変数                                 | デフォルト  | 説明                                                                                   |
| -------------------------- | ---------------------------------------- | ----------- | -------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1` | Web サーバーのバインドアドレス                                                         |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`      | Web サーバーポート                                                                     |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`     | HTTPS を無効化                                                                         |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | （なし）    | PEM 証明書と鍵のパス。両方指定。アイデンティティの `ssl/` 下の自動生成証明書を上書き。 |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | （なし）    | Reticulum（RNS）のログレベル（上記の名前または数値）。CLI は環境変数より優先。         |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`     | ブラウザを自動で開かない                                                               |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`     | 基本認証を有効化                                                                       |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage` | データディレクトリ                                                                     |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | 自動/同梱   | フロントエンドファイルディレクトリ（同梱資産のないインストール向け）                   |

## ブランチ

| ブランチ | 目的                                                       |
| -------- | ---------------------------------------------------------- |
| `master` | 安定版リリース。本番向けのコードのみ。                     |
| `dev`    | 活発な開発。不安定または不完全な変更を含む場合があります。 |

## 開発

`Taskfile.yml` のよく使うタスク:

```bash
task install
task lint:all
task test:all
task build:all
```

`Makefile` のショートカット:

| コマンド       | 説明                                    |
| -------------- | --------------------------------------- |
| `make install` | pnpm と poetry の依存関係をインストール |
| `make run`     | poetry 経由で MeshChatX を実行          |
| `make build`   | フロントエンドをビルド                  |
| `make lint`    | eslint と ruff を実行                   |
| `make test`    | フロントエンドとバックエンドのテスト    |
| `make clean`   | ビルド成果物と node_modules を削除      |

## バージョン管理

このリポジトリの現在のバージョンは `4.5.0` です。

- JavaScript / Electron のバージョンソースは `package.json`。
- `meshchatx/src/version.py` は次で `package.json` と同期します:

```bash
pnpm run version:sync
```

リリースの一貫性のため、必要に応じて (`package.json`、`pyproject.toml`、`meshchatx/__init__.py`) のバージョンを揃えてください。

## セキュリティ

- [`SECURITY.md`](../SECURITY.md)
- アプリ実行時の組み込み整合性チェックとデフォルトの HTTPS/WSS
- `.gitea/workflows/` の CI スキャンワークフロー

## 言語の追加

ロケールは自動検出されます。新しい言語には JSON ファイル 1 つで足ります:

1. `en.json` から空のテンプレートを生成:

```bash
python scripts/generate_locale_template.py
```

全キーを空文字にした `locales.json` が書き出されます。

2. 名前を変更してロケールディレクトリへ移動:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. ファイル先頭の `_languageName` にその言語の母語名を設定（例: `"Espanol"`, `"Francais"`）。言語選択に表示されます。

4. 残りの値をすべて翻訳。

5. キーの整合性を確認: `pnpm test -- tests/frontend/i18n.test.js --run`

他のコード変更は不要です。アプリ・言語選択・テストはビルド時に `meshchatx/src/frontend/locales/` からロケールを読み込みます。

## クレジット

- [Liam Cottle](https://github.com/liamcottle) - オリジナル Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - Micron パーサー（JavaScript）
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## ライセンス

プロジェクト独自の部分は 0BSD です。
MeshChat 由来の元の上流部分は MIT のままです。
全文と通知は [`../LICENSE`](../LICENSE) を参照してください。
