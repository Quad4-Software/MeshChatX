# Reticulum MeshChatX

Liam Cottle 开发的 Reticulum MeshChat 的一个功能丰富的深度修改分支。

本项目独立于原始 Reticulum MeshChat 项目，与其无关联。

- 源码: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- 发行版: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- 变更日志: [`CHANGELOG.md`](../CHANGELOG.md)
- TODO: [`TODO.md`](../TODO.md)
- [English README](../README.md) | [Deutsch](README.de.md) | [Italiano](README.it.md) | [Русский](README.ru.md) | [日本語](README.ja.md)

## 重要说明

- 完整的 LXMF 支持是本项目的核心目标。
- 数据存储和迁移正逐步转向原生 SQL（替换旧的 Peewee ORM 路径）。

> [!WARNING]
> MeshChatX 不保证与旧版 Reticulum MeshChat 的数据兼容。迁移或测试前请备份数据。

> [!WARNING]
> 旧系统尚未完全支持。当前最低要求：Python `>=3.11`，Node `>=24`。

## 演示和截图

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

### 界面预览

![电话](../screenshots/phone.png)
![网络可视化](../screenshots/network-visualiser.png)
![存档](../screenshots/archives.png)
![身份管理](../screenshots/identities.png)

## 系统要求

- Python `>=3.11`（来自 `pyproject.toml`）
- Node.js `>=24`（来自 `package.json`）
- pnpm `10.30.0`（来自 `package.json`）
- Poetry（用于 `Taskfile.yml` 和 CI 工作流）

## Nix (flake.nix)

本仓库包含 Nix flake 文件 `flake.nix`。

### 进入开发环境

```bash
nix develop
```

### 构建默认 Nix 包

```bash
nix build .#default
```

### `nix develop` 中的典型工作流

```bash
task install
task lint:all
task test:all
task build:all
```

## 安装方式

| 方式                  | 包含前端 | 架构                         | 适用场景                            |
| --------------------- | -------- | ---------------------------- | ----------------------------------- |
| Docker 镜像           | 是       | `linux/amd64`, `linux/arm64` | Linux 服务器快速部署                |
| Python wheel (`.whl`) | 是       | 任何 Python 支持的架构       | 无需 Node 构建的无头/Web 服务器安装 |
| Linux AppImage        | 是       | `x64`, `arm64`               | 便携式桌面使用                      |
| Debian 包 (`.deb`)    | 是       | `x64`, `arm64`               | Debian/Ubuntu 安装                  |
| RPM 包 (`.rpm`)       | 是       | 取决于 CI                    | Fedora/RHEL/openSUSE                |
| 从源码                | 本地构建 | 主机架构                     | 开发和自定义构建                    |

说明:

- 发布工作流明确构建 Linux `x64` 和 `arm64` AppImage + DEB。
- RPM 也会尝试构建，成功时上传。

## 快速开始: Docker

```bash
docker compose up -d
```

默认 compose 文件映射:

- 主机 `127.0.0.1:8000` -> 容器端口 `8000`
- `./meshchat-config` -> `/config` 持久化存储

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

1. 下载 `ReticulumMeshChatX-v<版本>-linux-<架构>.rpm`（如发行版中存在）。
2. 安装:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

发行版 wheel 包含已构建的前端资源。

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchat --headless
```

也支持 `pipx`:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## 从源码运行（Web 服务器模式）

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

## 从源码构建桌面包

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

## 架构支持

- Docker: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64`（构建脚本可用）
- macOS: 构建脚本可用（`arm64`, `universal`）
- Android: 仓库中包含项目和 CI 工作流

## Android

- [`docs/meshchatx_on_android_with_termux.md`](../docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](../android/README.md)

## 配置

| 参数            | 环境变量               | 默认值      | 说明               |
| --------------- | ---------------------- | ----------- | ------------------ |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1` | Web 服务器绑定地址 |
| `--port`        | `MESHCHAT_PORT`        | `8000`      | Web 服务器端口     |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`     | 禁用 HTTPS         |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`     | 不自动打开浏览器   |
| `--auth`        | `MESHCHAT_AUTH`        | `false`     | 启用基本认证       |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage` | 数据目录           |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | 自动        | 前端文件目录       |

## 分支

| 分支     | 用途                                     |
| -------- | ---------------------------------------- |
| `master` | 稳定发布。仅限生产就绪代码。             |
| `dev`    | 活跃开发。可能包含不稳定或不完整的更改。 |

## 开发

```bash
task install
task lint:all
task test:all
task build:all
```

## 安全

- [`SECURITY.md`](../SECURITY.md)
- 内置完整性检查和 HTTPS/WSS 默认设置
- `.gitea/workflows/` 中的 CI 扫描工作流

## 致谢

- [Liam Cottle](https://github.com/liamcottle) - 原始 Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - JavaScript Micron 解析器
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
