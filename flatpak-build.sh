#!/bin/bash
set -e

export HOME=/tmp/build
export XDG_CONFIG_HOME=/tmp/build/.config
export XDG_DATA_HOME=/tmp/build/.local/share
mkdir -p /tmp/build/.config /tmp/build/.local/share

NODE_PATHS=(
    "/usr/lib/sdk/node20/bin"
    "/usr/lib/sdk/node20/root/usr/bin"
    "/usr/lib/sdk/node/bin"
    "/usr/lib/sdk/node/root/usr/bin"
)

NODE_BIN=""
NPM_BIN=""

for path in "${NODE_PATHS[@]}"; do
    if [ -f "$path/node" ] && [ -f "$path/npm" ]; then
        NODE_BIN="$path/node"
        NPM_BIN="$path/npm"
        export PATH="$path:$PATH"
        break
    fi
done

if [ -z "$NODE_BIN" ] || [ -z "$NPM_BIN" ]; then
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        NODE_BIN=$(command -v node)
        NPM_BIN=$(command -v npm)
    else
        echo "Error: Node.js binaries not found. Checking common locations..."
        find /usr/lib/sdk -name node -type f 2>/dev/null | head -1
        find /usr/lib/sdk -name npm -type f 2>/dev/null | head -1
        exit 1
    fi
fi

echo "Using Node.js: $NODE_BIN"
echo "Using npm: $NPM_BIN"

PNPM_VERSION="10.0.0"
NPM_PREFIX="$HOME/.local"
mkdir -p "$NPM_PREFIX"

export npm_config_prefix="$NPM_PREFIX"
$NPM_BIN config set prefix "$NPM_PREFIX"

echo "Installing pnpm via npm to $NPM_PREFIX..."
$NPM_BIN install -g pnpm@${PNPM_VERSION} || exit 1

export PATH="$NPM_PREFIX/bin:$PATH"

python3 scripts/sync_version.py

pnpm install --frozen-lockfile
pnpm run build

mkdir -p /tmp/electron-install
cd /tmp/electron-install
pnpm init
pnpm add electron@39.2.7
cd -

pip3 install poetry
poetry install --no-dev
poetry run python cx_setup.py build

mkdir -p /app/bin /app/lib/reticulum-meshchatx /app/share/applications /app/share/icons/hicolor/512x512/apps

cp -r electron /app/lib/reticulum-meshchatx/
cp -r build/exe /app/lib/reticulum-meshchatx/
mkdir -p /app/lib/reticulum-meshchatx/electron-bin
cp -r /tmp/electron-install/node_modules/electron/* /app/lib/reticulum-meshchatx/electron-bin/
cp logo/logo.png /app/share/icons/hicolor/512x512/apps/com.sudoivan.reticulummeshchat.png

cat > /app/share/applications/com.sudoivan.reticulummeshchat.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Reticulum MeshChatX
Comment=A simple mesh network communications app powered by the Reticulum Network Stack
Exec=reticulum-meshchatx
Icon=com.sudoivan.reticulummeshchat
Categories=Network;InstantMessaging;
StartupNotify=true
EOF

cat > /app/bin/reticulum-meshchatx <<'EOF'
#!/bin/sh
export ELECTRON_IS_DEV=0
export APP_PATH=/app/lib/reticulum-meshchatx/electron
export EXE_PATH=/app/lib/reticulum-meshchatx/build/exe/ReticulumMeshChatX
ELECTRON_BIN=/app/lib/reticulum-meshchatx/electron-bin/dist/electron
if [ ! -f "$ELECTRON_BIN" ]; then
    ELECTRON_BIN=$(find /app/lib/reticulum-meshchatx/electron-bin -name electron -type f 2>/dev/null | head -1)
fi
cd /app/lib/reticulum-meshchatx/electron
exec "$ELECTRON_BIN" . "$@"
EOF

chmod +x /app/bin/reticulum-meshchatx

