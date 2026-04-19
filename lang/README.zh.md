# Reticulum MeshChatX

[English](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [日本語](README.ja.md)

Liam Cottle 开发的 Reticulum MeshChat 的一个功能丰富的深度修改分支。

本项目独立于原始 Reticulum MeshChat 项目，与其无关联。

- 网站: [meshchatx.com](https://meshchatx.com)
- 源码: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- 官方镜像: [github.com/Quad4/MeshChatX](https://github.com/Quad4/MeshChatX) — 目前亦用于 Windows 与 macOS 构建。
- 发行版: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- 变更日志: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## 与 Reticulum MeshChat 的重要差异

- 使用 LXST
- 以原生 SQL 替代 Peewee ORM
- 以原生 `fetch` 替代 Axios
- 使用最新 Electron
- `.whl` 内置 Web 服务器与前端资源，便于多种部署方式
- i18n
- 使用 PNPM 与 Poetry 管理依赖

> [!WARNING]
> MeshChatX 不保证与旧版 Reticulum MeshChat 的数据兼容。迁移或测试前请备份数据。

> [!WARNING]
> 旧系统尚未完全支持。当前最低要求：Python `>=3.11`，Node `>=22`（Electron 使用 Node 22；CI 可使用更高版本）。

## 系统要求

- Python `>=3.11`（来自 `pyproject.toml`）
- Node.js `>=22`（来自 `package.json`）
- pnpm `10.32.1`（来自 `package.json`）
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
| RPM 包 (`.rpm`)       | 是       | 取决于 CI                    | Fedora/RHEL/openSUSE                |
| 从源码                | 本地构建 | 主机架构                     | 开发与自定义构建                    |

说明:

- 发布工作流明确构建 Linux `x64` 与 `arm64` 的 AppImage + DEB。
- RPM 亦会尝试构建，成功时上传。

## 快速开始: Docker

```bash
docker compose up -d
```

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
pip install "poetry==2.1.1"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

关于上述安装命令的说明：

- `pnpm install --frozen-lockfile` 禁止更新 `pnpm-lock.yaml`，若 lockfile 与 `package.json` 不一致则直接失败。这能阻止意外的上游版本被静默安装。
- `verify-store-integrity=true` 已在项目的 `.npmrc` 中设置；显式的 `pnpm config set` 行同时加固用户级配置。
- pnpm v10+ 默认禁用所有生命周期脚本（`preinstall`/`postinstall`）。仅 `package.json` 中 `pnpm.onlyBuiltDependencies` 列出的包允许执行安装脚本（当前为 `electron`、`electron-winstaller`、`esbuild`、`protobufjs`）。
- `poetry check --lock` 会在 `poetry.lock` 与 `pyproject.toml` 不同步时立即失败；随后的 `poetry install` 只会从 lock 文件解析依赖。
- 若需严格按 lock 文件安装 Poetry 依赖（不进行隐式刷新），用 `pip install "poetry==2.1.1"` 固定 Poetry 版本，与 CI 保持一致。

如果确有意愿更新依赖，请在独立提交中运行 `pnpm update` / `poetry update`，并在推送前审查生成的 lock 文件 diff。

## 在沙盒中运行（Linux）

若要在额外隔离文件系统的情况下运行原生 `meshchatx`（别名：`meshchat`），可使用 **Firejail** 或 **Bubblewrap**（`bwrap`），同时保留 Reticulum 与 Web 界面所需的网络访问。完整示例（pip/pipx、Poetry、USB 串口说明）见:

- [`docs/meshchatx_linux_sandbox.md`](../docs/meshchatx_linux_sandbox.md)

在提供已捆绑或已同步的 `meshchatx-docs` 时，应用内 **文档**（MeshChatX 文档）列表亦会显示同一页面。

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

## 架构支持

- Docker 镜像: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（提供构建脚本）
- macOS: 提供构建脚本（`arm64`、`universal`），适用于本地构建环境
- Android: 原生 APK — ABI `arm64-v8a`、`x86_64` 与 universal

## Android

MeshChatX 支持构建原生 Android APK（不仅限于 Termux）。

### 从源码构建 APK

在仓库根目录执行:

```bash
# 1) 构建 android/app/build.gradle 所需的 Chaquopy 轮子
bash scripts/build-android-wheels-local.sh

# 2) 构建两种 APK 变体
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

APK 输出（ABI 分包与 universal APK；见 `android/app/build.gradle` 中的 `splits { abi { ... } }`）:

调试（`android/app/build/outputs/apk/debug/`）:

- `app-arm64-v8a-debug.apk`（ARM64 设备）
- `app-x86_64-debug.apk`（x86_64 模拟器）
- `app-universal-debug.apk`（所有已打包 ABI 的单包）

发布（`android/app/build/outputs/apk/release/`）:

- `app-arm64-v8a-release-unsigned.apk`
- `app-x86_64-release-unsigned.apk`
- `app-universal-release-unsigned.apk`

说明:

- 若未配置签名，发布构建默认未签名。
- 若只需一种变体，可运行 `:app:assembleDebug` 或 `:app:assembleRelease`。
- Android 目标 ABI 为 `android/app/build.gradle` 中配置的 `arm64-v8a` 与 `x86_64`。

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
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | 自动/捆绑   | 前端文件目录（无捆绑资源安装时需要）                                                            |

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

## 版本

本仓库当前版本: `4.5.0`。

- JavaScript/Electron 版本以 `package.json` 为准。
- `meshchatx/src/version.py` 通过以下命令与 `package.json` 同步:

```bash
pnpm run version:sync
```

发布时请保持相关字段一致（`package.json`、`pyproject.toml`、`meshchatx/__init__.py`）。

## 安全

- [`SECURITY.md`](../SECURITY.md)
- 应用内置完整性检查与默认 HTTPS/WSS
- `.gitea/workflows/` 中的 CI 扫描工作流

## 添加语言

语言检测是自动的。在 `meshchatx/src/frontend/locales/` 下新增 JSON 文件（例如 `xx.json`），键与 `en.json` 一致，并在顶层设置 `_languageName` 作为语言选择器中的显示名称。可以复制 `en.json` 后完全人工翻译；**使用 Argos 等机器辅助生成是可选的**，并非必需。

**欢迎提交纠错与人工翻译。** 若修正现有语言文件或提交完整人工翻译，请通过合并请求或议题提交至[项目源码仓库](https://git.quad4.io/RNS-Things/MeshChatX)或 [GitHub 镜像](https://github.com/Sudo-Ivan/MeshChatX)。

**可选：Argos Translate 初稿** -- 若需要从 `en.json` 生成机器翻译初稿，可使用 `scripts/argos_translate.py`。它会处理格式并有助于保护插值变量（如 `{count}`）。

```bash
# 如果尚未安装，请安装 argostranslate
pip install argostranslate

# 运行翻译脚本
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "您的语言名称"
```

机器初稿之后，建议由 LLM 或人工审校语法、语境与语气（如正式与非正式）。

运行 `pnpm test -- tests/frontend/i18n.test.js --run` 验证与 `en.json` 的键一致性。

不需要其他代码更改。应用程序、语言选择器和测试在构建时从 `meshchatx/src/frontend/locales/` 目录发现所有语言环境。

## 致谢

- [Liam Cottle](https://github.com/liamcottle) - 原始 Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - Micron 解析器（JavaScript）
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## 许可证

项目自有部分采用 0BSD 许可。
源自 MeshChat 的原始上游部分继续采用 MIT 许可。
完整文本与声明请见 [`../LICENSE`](../LICENSE)。
