# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [中文](README.zh.md)

Liam Cottle 氏による Reticulum MeshChat を大幅に改修・機能拡張したフォークです。

本プロジェクトはオリジナルの Reticulum MeshChat とは独立しており、提携関係にありません。

- ウェブサイト: [meshchatx.com](https://meshchatx.com)
- ソースコード: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- 公式 GitHub ミラー: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- リリース: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- 変更履歴: [`CHANGELOG.md`](../CHANGELOG.md)
- 寄付: [`donate.md`](../donate.md)

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`
NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## Reticulum MeshChat からの主な変更

- 通話に LXST を使用
- Peewee ORM を生 SQL に置き換え
- Axios をネイティブ `fetch` に置き換え
- Electron 41.x（同梱 Node 24 ランタイム）
- Web サーバーと同梱フロントエンドを含む `.whl` によりデプロイの選択肢を拡張
- i18n
- 依存関係管理に PNPM と Poetry

> [!WARNING]
> MeshChatX は旧バージョンの Reticulum MeshChat とのデータ互換性を保証しません。マイグレーションやテスト前にデータをバックアップしてください。

> [!WARNING]
> レガシーシステムはまだサポートされません。現在の基準は Python `>=3.11` と Node `>=24`（Electron 41 は Node 24 に揃う；`package.json` の `engines` と CI も同じライン）。

## 必要条件

- Python `>=3.11`（`pyproject.toml` より）
- Node.js `>=24`（`package.json` の `engines`）
- pnpm `10.33.0`（`package.json` の `packageManager`）
- Poetry（`Taskfile.yml` および CI ワークフローで使用）

**Browser Versions Required:**

Safari 16.4 以降、Chrome 111 以降、Firefox 128 以降（同梱 Web UI）。

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
| RPM パッケージ (`.rpm`)    | はい               | 公開用 CI ランナーに依存              | Fedora/RHEL/openSUSE                     |
| ソースから                 | ローカルビルド     | ホストアーキテクチャ                  | 開発・カスタムビルド                     |

備考:

- GitHub Actions はタグ付きリリース（Linux wheel / AppImage / deb / rpm、Windows、macOS、Flatpak、dev/master 上のタグ時の Android APK、SLSA、ドラフトリリース）を 1 回のワークフローでビルドします: `.github/workflows/build-release.yml`。コンテナイメージは `.github/workflows/docker.yml`。ブランチと PR の Android CI は `.github/workflows/android-build.yml`。
- Linux `x64` および `arm64` の AppImage + DEB は GitHub でビルド。RPM も試行し、成果物があればアップロードします。

## Docker

- **Docker Hub:** `quad4io/meshchatx`
- **GHCR:** `ghcr.io/quad4-software/meshchatx`

```bash
docker compose up -d
```

```bash
docker run -d --name reticulum-meshchatx \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:8000:8000 \
  -v "$(pwd)/meshchat-config:/config" \
  ghcr.io/quad4-software/meshchatx:latest
```

GHCR の代わりに Docker Hub の `quad4io/meshchatx:latest` を使えます。

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
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "poetry==2.3.4"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

上記インストールコマンドに関する補足:

- `pnpm install --frozen-lockfile` は `pnpm-lock.yaml` の更新を拒否し、ロックファイルが `package.json` と一致しない場合は失敗します。これにより、想定外の上流バージョンが暗黙的にインストールされるのを防げます。
- `verify-store-integrity=true` はプロジェクトの `.npmrc` にも設定されています。上記の `pnpm config set` の行はユーザー設定側も明示的に固めるためのものです。
- pnpm v10 以降、ライフサイクルスクリプト (`preinstall`/`postinstall`) はデフォルトでブロックされます。インストールスクリプトを実行できるのは `package.json` の `pnpm.onlyBuiltDependencies` に列挙されたパッケージ（現在 `electron`、`electron-winstaller`、`esbuild`）だけです。
- `poetry check --lock` は `poetry.lock` と `pyproject.toml` が同期していない場合に即時失敗します。その後の `poetry install` はロックファイルからのみ解決します。
- 厳密にロックファイルだけで Poetry をインストールしたい場合は、CI と揃えるために `pip install "poetry==2.3.4"` で Poetry バージョンを固定してください。

意図的に依存を更新する場合は、`pnpm update` / `poetry update` を専用コミットで実行し、push 前にロックファイルの diff を必ず確認してください。

## サンドボックスで実行（Linux）

ネイティブの `meshchatx`（エイリアス: `meshchat`）をファイルシステムをより隔離した状態で動かすには、Reticulum と Web UI 向けの通常のネットワークアクセスを保ちつつ **Firejail** または **Bubblewrap**（`bwrap`）を使えます。詳しい例（pip/pipx、Poetry、USB シリアルの注意）は次を参照:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

同梱または同期された `meshchatx-docs` から配信する場合、同じページがアプリ内 **ドキュメント** 一覧（MeshChatX ドキュメント）にも表示されます。

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

## コンテナビルド（wheel、AppImage、deb、rpm）

`Dockerfile.build` は CI と同じ手順（Poetry、pnpm、`task`、APT 依存）を実行します。**linux/amd64** 向け（NodeSource の amd64 tarball、Task の amd64 バイナリ）。デフォルトは全ターゲット。build-arg で上書き可能。

`MESHCHATX_BUILD_TARGETS` の値: `all`（既定）、`wheel`、または `electron`（x64 / arm64 の AppImage + deb、RPM はベストエフォート、wheel なし）。

ビルド:

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

wheel のみ:

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

完成したイメージから `/artifacts` をホストにコピー:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## アーキテクチャサポート

- Docker イメージ: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（ビルドスクリプトあり）
- macOS: ローカルビルド向けにビルドスクリプトあり（`arm64`, `universal`）
- Android: universal APK のみ（[`android/README.md`](../android/README.md) 参照）

## Android

MeshChatX はネイティブ Android APK のビルドに対応しています（Termux のみに限りません）。

### ソースから APK をビルド

リポジトリのルートで:

```bash
# 1) android/app/build.gradle で使う Chaquopy 用ホイールをビルド
bash scripts/build-android-wheels-local.sh

# 2) universal APK をビルド（1 回の実行で debug 1 本 + release 1 本；android/README.md 参照）
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

**単一**の Android バリアント。Gradle が `meshchatx/` ツリー全体を `app/src/main/python/meshchatx/` に同期し、オフラインリポジトリ用ホイールも含みます。ドキュメントおよび公開ビルドは **universal** パッケージのみです。実行ごとにデバッグ APK 1 本とリリース APK 1 本が生成され、それぞれ `android/app/build.gradle` で選んだ全ネイティブ ABI を含みます。

- デバッグ: `android/app/build/outputs/apk/debug/app-debug.apk`
- リリース: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

備考:

- リリース成果物は、署名を設定するまで既定で未署名（`scripts/sign-android-apks.sh`）。
- universal APK に埋め込まれるネイティブ ABI は `android/app/build.gradle` の一覧（`armeabi-v7a` 有効時を含む）。`armeabi-v7a` 用ホイールのビルドには `ANDROID_HOME` の Android SDK が必要（`android/README.md` 参照）。
- リポジトリルートに `dist/reticulum_meshchatx-*.whl` があると（例: `python -m build --wheel -o dist .`）、同梱リポジトリの更新で PyPI よりその MeshChatX ホイールを優先。CI では Android Gradle の前にそのホイールをビルドします。

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
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | 自動/同梱   | フロントエンドのディレクトリ（同梱資産なしのソースインストールで必要）                 |

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

このリポジトリの現在のバージョンは `4.6.0` です。

- リリースのバージョン上げは **`package.json` の `version` のみ**編集します。
- **`pnpm run version:sync`**（**`pnpm run build`** 開始時にも実行）で、**`pyproject.toml`**、**`meshchatx/src/version.py`**、**`THIRD_PARTY_NOTICES.txt`**（製品行）、**README** / **lang/README.\***（現在のバージョン行）、**`docs/meshchatx_on_raspberry_pi.md`** の pipx 例、**`packaging/arch/PKGBUILD`** の補助フィールドに反映します。
- **`meshchatx.__version__`** は **`meshchatx/src/version.py`** から読み、**`meshchatx.src`** をインポートしないため、単なる `import meshchatx` は軽量のままです。
- **Changelog** のエントリはリリース時に手作業のままです。

## セキュリティ

- [`SECURITY.md`](../SECURITY.md)
- [`LEGAL.md`](../LEGAL.md)
- アプリランタイムの組み込み整合性チェックと既定の HTTPS/WSS。
- GitHub Actions での CI およびリリースビルド。

## 言語の追加

作業手順: ArgosTranslate から ローカル LLM（Qwen 3 + Gemma 4）へ。

そのあと、LXMF 等で修正を歓迎します。

ロケールの検出は自動です。`meshchatx/src/frontend/locales/` に新しいファイル（例: `xx.json`）を追加し、`en.json` と同じキーに加え、セレクタ表示用の `_languageName` を最上位に置きます。`en.json` をコピーし手作業で訳すこともできます。**機械補助は任意**で、求められません。

**任意: Argos Translate で土台** -- `en.json` から下書きするには `scripts/argos_translate.py`（整形・カラー出力、 `{count}` 等の保護）を使えます。

```bash
# 必要なら argostranslate を導入
pipx install argostranslate

# 翻訳スクリプトを実行
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "言語名"
```

機械下書きのあと、文法・文脈・トーンは LLM か人が確認（フォーマル/カジュアル等）。

`pnpm test -- tests/frontend/i18n.test.js --run` で `en.json` とのキー一致を検証。

その他のコードの変更は必要ありません。アプリ、言語セレクター、およびテストは、ビルド時に `meshchatx/src/frontend/locales/` ディレクトリからロケールを検出します。

## 寄付

寄付は任意です。このアプリを開発するための時間と労力に充てられます。

**寄付の方法:** [`donate.md`](../donate.md)（Monero、Ko-Fi、Buy Me a Coffee）。

## クレジット

- [Liam Cottle](https://github.com/liamcottle) - オリジナル Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron パーサー（JavaScript）
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## ライセンス

プロジェクト独自の部分は 0BSD です。
Reticulum MeshChat 由来の元の上流部分は MIT のままです。
全文と通知は [`../LICENSE`](../LICENSE) を参照してください。
