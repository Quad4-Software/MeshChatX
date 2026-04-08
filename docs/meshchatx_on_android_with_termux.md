# MeshChatX on Android

It's possible to run MeshChatX on Android using [Termux](https://termux.dev/). Installation is now much simpler since the wheel package includes both the server and pre-built web assets.

## Method 1: Install from Wheel (Recommended)

This is the easiest method - the wheel includes everything you need.

### Install System Dependencies

```
pkg upgrade
pkg install python
pkg install rust
pkg install binutils
pkg install build-essential
```

> Note: Python 3.11 or higher is required. Check with `python --version`.

### Download and Install Wheel

Download the latest wheel from the [releases page](https://git.quad4.io/RNS-Things/MeshChatX/releases), then:

```
pip install reticulum_meshchatx-*-py3-none-any.whl
```

The wheel will automatically install all Python dependencies. Building `cryptography` may take a while on Android.

### Run MeshChatX

```
meshchatx
```

(`meshchat` is a compatibility alias for the same entry point.)

Then open your Android web browser and navigate to `http://localhost:8000`

## Method 2: Install from Source

If you need to build from source (for development or if no wheel is available for your architecture):

### Install System Dependencies

```
pkg upgrade
pkg install git
pkg install nodejs-lts
pkg install python
pkg install rust
pkg install binutils
pkg install build-essential
```

### Install pnpm

```
corepack enable
corepack prepare pnpm@latest --activate
```

### Clone and Build

```
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
pip install poetry
poetry install
pnpm install
pnpm run build-frontend
poetry build -f wheel
pip install dist/*.whl
```

### Run MeshChatX

```
meshchatx
```

(`meshchat` is a compatibility alias for the same entry point.)

## Configuration Notes

> Note: The default `AutoInterface` may not work on your Android device. You will need to configure another interface such as `TCPClientInterface` in the settings.
