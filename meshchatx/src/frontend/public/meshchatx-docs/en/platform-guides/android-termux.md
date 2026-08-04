# Android with Termux

MeshChatX runs on Android through [Termux](https://termux.dev/). Release wheels ship the Python backend and built web UI, so you do not need Node on the phone for a normal install.

## Install from wheel

The wheel bundles server code and frontend assets.

### System packages

```
pkg upgrade
pkg install python
pkg install rust
pkg install binutils
pkg install build-essential
```

> Note: Python 3.11 or higher is required. Check with `python --version`.

### Wheel install

Download the latest wheel from the [releases page](https://github.com/Quad4-Software/MeshChatX/releases), then:

```
pip install reticulum_meshchatx-*-py3-none-any.whl
```

The wheel pulls Python dependencies automatically. Building `cryptography` can take several minutes on Android.

### Run

```
meshchatx
```

(`meshchat` is a compatibility alias for the same entry point.)

Open `http://localhost:8000` in the Android browser.

## Install from source

Use this path for development or when no wheel fits your setup.

### System packages

```
pkg upgrade
pkg install git
pkg install nodejs-lts
pkg install python
pkg install rust
pkg install binutils
pkg install build-essential
```

### pnpm

```
corepack enable
corepack prepare pnpm@latest --activate
```

### Clone and build

```
git clone https://github.com/Quad4-Software/MeshChatX.git
cd MeshChatX
pip install uv
uv sync --group dev
pnpm install
pnpm run build-frontend
uv build --wheel
pip install dist/*.whl
```

### Run

```
meshchatx
```

(`meshchat` is a compatibility alias for the same entry point.)

## Configuration notes

> Note: The default `AutoInterface` may not work on your Android device. Configure another interface such as `TCPClientInterface` in the settings.
