# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [日本語](README.ja.md)

Liam Cottle 开发的 Reticulum MeshChat 的一个功能丰富的深度修改分支。

本项目独立于原始 Reticulum MeshChat 项目，与其无关联。

- 网站: [meshchatx.com](https://meshchatx.com)
- 源码: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- 官方 GitHub 镜像: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- 发行版: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- 变更日志: [`CHANGELOG.md`](../CHANGELOG.md)

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`
NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## 与 Reticulum MeshChat 的重要差异

- 通话使用 LXST
- 以原生 SQL 替代 Peewee ORM
- 以原生 `fetch` 替代 Axios
- 使用 Electron 41.x（内置 Node 24 运行时）
- `.whl` 内置 Web 服务器与前端资源，便于多种部署方式
- i18n
- 使用 PNPM 与 Poetry 管理依赖

> [!WARNING]
> MeshChatX 不保证与旧版 Reticulum MeshChat 的数据兼容。迁移或测试前请备份数据。

> [!WARNING]
> 旧系统尚不支持。当前基线为 Python `>=3.11` 与 Node `>=24`（Electron 41 与 Node 24 一致；`package.json` 的 `engines` 与 CI 同一基线）。

## 系统要求

- Python `>=3.11`（来自 `pyproject.toml`）
- Node.js `>=24`（来自 `package.json` 的 `engines`）
- pnpm `10.33.0`（来自 `package.json` 的 `packageManager`）
- Poetry（用于 `Taskfile.yml` 与 CI 工作流）

```bash
task install
task lint:all
task test:all
task build:all
```

## 安装方式

请按运行环境与打包形式选择。

| 方式                  | 包含前端 | 架构                         | 适用场景                            |
| --------------------- | -------- | ---------------------------- | ----------------------------------- |
| Docker 镜像           | 是       | `linux/amd64`, `linux/arm64` | Linux 服务器快速部署                |
| Python wheel (`.whl`) | 是       | 任何 Python 支持的架构       | 无需 Node 构建的无头/Web 服务器安装 |
| Linux AppImage        | 是       | `x64`, `arm64`               | 便携式桌面使用                      |
| Debian 包 (`.deb`)    | 是       | `x64`, `arm64`               | Debian/Ubuntu 安装                  |
| RPM 包 (`.rpm`)       | 是       | 取决于发布所用 CI 运行环境   | Fedora/RHEL/openSUSE                |
| 从源码                | 本地构建 | 主机架构                     | 开发与自定义构建                    |

说明:

- GitHub Actions 构建带标签的发行版：Windows 与 macOS 见 `.github/workflows/build-release.yml`，Linux wheel/AppImage/deb/rpm 见 `.github/workflows/build-linux-release.yml`，容器镜像见 `.github/workflows/docker.yml`。
- Linux `x64` 与 `arm64` 的 AppImage + DEB 在 GitHub 上构建；RPM 会尝试构建，产出则上传。

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

若倾向 Docker Hub，可将镜像换为 `quad4io/meshchatx:latest`。

默认 compose 文件映射:

- 主机 `127.0.0.1:8000` -> 容器端口 `8000`
- `./meshchat-config` -> `/config` 持久化

如遇权限问题:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

## 从发行版安装

### 1) Linux AppImage (x64/arm64)

1. 从发行版下载 `ReticulumMeshChatX-v<版本>-linux-<架构>.AppImage`。
2. 赋予执行权限并运行:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. 下载 `ReticulumMeshChatX-v<版本>-linux-<架构>.deb`。
2. 安装:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) RPM 系统

1. 若发行版中存在，下载 `ReticulumMeshChatX-v<版本>-linux-<架构>.rpm`。
2. 安装:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

发行版 wheel 包含已构建的前端资源。

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

亦支持 `pipx`:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## 从源码运行（Web 服务器模式）

在开发或需要本地定制构建时使用。

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

关于上述安装命令的说明：

- `pnpm install --frozen-lockfile` 禁止更新 `pnpm-lock.yaml`，若 lockfile 与 `package.json` 不一致则直接失败。这能阻止意外的上游版本被静默安装。
- `verify-store-integrity=true` 已在项目的 `.npmrc` 中设置；显式的 `pnpm config set` 行同时加固用户级配置。
- pnpm v10+ 默认禁用所有生命周期脚本（`preinstall`/`postinstall`）。仅 `package.json` 中 `pnpm.onlyBuiltDependencies` 列出的包允许执行安装脚本（当前为 `electron`、`electron-winstaller`、`esbuild`）。
- `poetry check --lock` 会在 `poetry.lock` 与 `pyproject.toml` 不同步时立即失败；随后的 `poetry install` 只会从 lock 文件解析依赖。
- 若需严格按 lock 文件安装 Poetry 依赖（不进行隐式刷新），用 `pip install "poetry==2.3.4"` 固定 Poetry 版本，与 CI 保持一致。

如果确有意愿更新依赖，请在独立提交中运行 `pnpm update` / `poetry update`，并在推送前审查生成的 lock 文件 diff。

## 在沙盒中运行（Linux）

若要在额外隔离文件系统的情况下运行原生 `meshchatx`（别名：`meshchat`），可使用 **Firejail** 或 **Bubblewrap**（`bwrap`），同时保留 Reticulum 与 Web 界面所需的网络访问。完整示例（pip/pipx、Poetry、USB 串口说明）见:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

从已捆绑或已同步的 `meshchatx-docs` 文件提供服务时，应用内 **文档** 列表（MeshChatX 文档）亦会显示同一页面。

## Linux 桌面：绘文字字体

绘文字选择器使用系统字体（Electron/Chromium）渲染标准 Unicode 绘文字。若显示为空白方框（“豆腐块”），请安装彩色绘文字字体包并重启应用。

| 发行版（示例）             | 软件包                                                                |
| -------------------------- | --------------------------------------------------------------------- |
| Arch Linux、Artix、Manjaro | `noto-fonts-emoji`（`sudo pacman -S noto-fonts-emoji`）               |
| Debian、Ubuntu             | `fonts-noto-color-emoji`（`sudo apt install fonts-noto-color-emoji`） |
| Fedora                     | `google-noto-emoji-color-fonts`                                       |

安装后若仍异常，可运行 `fc-cache -fv`。可选：最小安装可再装 `noto-fonts` 以覆盖更多符号。

## 从源码构建桌面包

脚本定义于 `package.json` 与 `Taskfile.yml`。

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

或通过 Task:

```bash
task dist:fe:rpm
```

## 容器构建（wheel、AppImage、deb、rpm）

`Dockerfile.build` 执行与 CI 相同的步骤（Poetry、pnpm、`task`、APT 等）。面向 **linux/amd64**（NodeSource amd64 压缩包、Task amd64 二进制）。默认目标为全部；可用 build 参数覆盖。

`MESHCHATX_BUILD_TARGETS` 可选：`all`（默认）、`wheel` 或 `electron`（x64 与 arm64 的 AppImage + deb、尽力构建 RPM、不含 wheel）。

构建：

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

仅 wheel：

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

将完成镜像中的 `/artifacts` 拷到本机：

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## 架构支持

- Docker 镜像: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（提供构建脚本）
- macOS: 提供构建脚本（`arm64`、`universal`），适用于本地构建环境
- Android: 原生 APK — ABI `arm64-v8a`、`x86_64`、`armeabi-v7a`（32 位 ARM），以及 universal

## Android

MeshChatX 支持构建原生 Android APK（不仅限于 Termux）。

### 从源码构建 APK

在仓库根目录执行:

```bash
# 1) 构建 android/app/build.gradle 所需的 Chaquopy 轮子
bash scripts/build-android-wheels-local.sh

# 2) 构建 universal APK（每次运行各一 debug + 一 release；见 android/README.md）
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

**单一** Android 变体。Gradle 将完整 `meshchatx/` 树同步到 `app/src/main/python/meshchatx/`，含离线仓库 wheel 包。**ABI 打包：** `universal`（默认）或 `split`（见 `android/app/build.gradle`）。

**`-PmeshchatxAbiPackaging=universal`**（默认）下，每种构建类型各一个包含所有已选 ABI 的 APK：

- 调试：`android/app/build/outputs/apk/debug/app-debug.apk`
- 发布：`android/app/build/outputs/apk/release/app-release-unsigned.apk`

**`-PmeshchatxAbiPackaging=split`** 且 `-PmeshchatxAbis` 含多个 ABI 时，Gradle 可能按 ABI 分别产出 APK，见 [`android/README.md`](../android/README.md)。

说明:

- 发布产物默认未签名，除非配置签名（`scripts/sign-android-apks.sh`）。
- Android 目标 ABI 以 `android/app/build.gradle` 为准（含启用时的 `armeabi-v7a`）。为 `armeabi-v7a` 构建 wheel 需本机 `ANDROID_HOME` 上有 Android SDK（见 `android/README.md`）。
- 覆盖 ABI：`-PmeshchatxAbis` 或 `MESHCHATX_ABIS`。打包：`-PmeshchatxAbiPackaging=universal|split` 或 `MESHCHATX_ABI_PACKAGING`。
- 若仓库根存在 `dist/reticulum_meshchatx-*.whl`（例如 `python -m build --wheel -o dist .`），刷新内置仓库时优先于 PyPI 使用该 MeshChatX wheel。CI 在 Android Gradle 步骤前会构建该 wheel。

更多文档:

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## 配置

| 参数                       | 环境变量                                 | 默认值      | 说明                                                                                            |
| -------------------------- | ---------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1` | Web 服务器绑定地址                                                                              |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`      | Web 服务器端口                                                                                  |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`     | 禁用 HTTPS                                                                                      |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | （无）      | PEM 证书与私钥路径；需同时设置。覆盖身份下 `ssl/` 目录中自动生成的证书。                        |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | （无）      | Reticulum（RNS）日志级别：`none`、`critical`、`error` 等或数值。同时设置时 CLI 优先于环境变量。 |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`     | 不自动打开浏览器                                                                                |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`     | 启用基本认证                                                                                    |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage` | 数据目录                                                                                        |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | 自动/捆绑   | 前端文件目录（源码安装且未捆绑资源时需要）                                                      |

## 分支

| 分支     | 用途                                     |
| -------- | ---------------------------------------- |
| `master` | 稳定发布。仅限生产就绪代码。             |
| `dev`    | 活跃开发。可能包含不稳定或不完整的更改。 |

## 开发

`Taskfile.yml` 中的常用任务:

```bash
task install
task lint:all
task test:all
task build:all
```

`Makefile` 快捷方式:

| 命令           | 说明                        |
| -------------- | --------------------------- |
| `make install` | 安装 pnpm 与 poetry 依赖    |
| `make run`     | 通过 poetry 运行 MeshChatX  |
| `make build`   | 构建前端                    |
| `make lint`    | 运行 eslint 与 ruff         |
| `make test`    | 运行前端与后端测试          |
| `make clean`   | 移除构建产物与 node_modules |

## 版本管理

本仓库当前版本: `4.6.0`。

- 发布版本号**只**改 **`package.json` 的 `version`**。
- 运行 **`pnpm run version:sync`**（在 **`pnpm run build`** 开头也会执行）可将该版本同步到 **`pyproject.toml`**、**`meshchatx/src/version.py`**、**`THIRD_PARTY_NOTICES.txt`**（产品行）、**README** / **lang/README.\*** 中的“当前版本”行、**`docs/meshchatx_on_raspberry_pi.md`** 的 pipx 示例，以及 **`packaging/arch/PKGBUILD`** 的辅助字段。
- **`meshchatx.__version__`** 从 **`meshchatx/src/version.py`** 读取且不导入 **`meshchatx.src`**，因此普通 `import meshchatx` 仍很轻量。
- **变更日志**在发版时仍由人工维护。

## 安全

- [`SECURITY.md`](../SECURITY.md)
- [`LEGAL.md`](../LEGAL.md)
- 应用运行时内置完整性检查与默认 HTTPS/WSS。
- CI 与发行构建在 GitHub Actions。

## 添加语言

作者流程：ArgosTranslate，再到本地 LLM（Qwen 3 + Gemma 4）。

之后欢迎通过 LXMF 或其他方式提交修正。

语言环境为自动发现。在 `meshchatx/src/frontend/locales/` 添加新文件（如 `xx.json`），键与 `en.json` 相同，并设顶层 `_languageName` 作为选择器标签。可复制 `en.json` 全手工翻译；**机器辅助生成（可选）**从不要求。

**可选：Argos Translate 起步** -- 若需从 `en.json` 生成初稿，可使用 `scripts/argos_translate.py`（处理格式、彩色输出，并保护如 `{count}` 的插值变量）。

```bash
# 若尚未安装 argostranslate
pipx install argostranslate

# 运行翻译脚本
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "您的语言名称"
```

任何机器辅助之后，请用 LLM 或人工核对语法、语境与语气（如正式/非正式）。

运行 `pnpm test -- tests/frontend/i18n.test.js --run` 校验与 `en.json` 的键一致。

不需要其他代码更改。应用程序、语言选择器和测试在构建时从 `meshchatx/src/frontend/locales/` 目录发现所有语言环境。

## 致谢

- [Liam Cottle](https://github.com/liamcottle) - 原始 Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron 解析器（JavaScript）
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## 许可证

项目自有部分采用 0BSD 许可。
源自 Reticulum MeshChat 的原始上游部分继续采用 MIT 许可。
完整文本与声明请见 [`../LICENSE`](../LICENSE)。
