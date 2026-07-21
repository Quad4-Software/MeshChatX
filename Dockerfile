# Docker Build Stages:
# 1. build-frontend: Build static frontend assets using Node
# 2. builder: Install third-party deps into /opt/venv-deps, then app overlay
# 3. final image: runtime pkgs, deps layer, thin app overlay (better update pulls)
#
# LXST wheels ship glibc-tagged filterlib extensions only. On Alpine/musl, cffi
# compiles at build time; scripts/docker-bake-lxst-filterlib-musl.py copies the
# artifact to the import name LXST.filterlib so runtime does not need gcc.

# ---- Global Build Args ----
ARG NODE_IMAGE=node:24-alpine
ARG NODE_HASH=sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf
ARG PYTHON_IMAGE=python:3.14.4-alpine3.23
ARG PYTHON_HASH=sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a

# ---- STAGE 1: Frontend Build ----
FROM --platform=linux/amd64 ${NODE_IMAGE}@${NODE_HASH} AS build-frontend
WORKDIR /src
# go is required to compile visualiser-wasm
RUN apk add --no-cache git python3 go
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml vite.config.js ./
COPY patches ./patches
COPY scripts/fetch-micron-wasm.mjs scripts/fetch-micron-wasm.mjs
COPY scripts/micron-wasm-resolve-bundled.mjs scripts/micron-wasm-resolve-bundled.mjs
COPY scripts/micron-parser-go-version.mjs scripts/micron-parser-go-version.mjs
COPY scripts/build-visualiser-wasm.mjs scripts/build-visualiser-wasm.mjs
COPY scripts/sync-meshchatx-docs.js scripts/sync-meshchatx-docs.js
COPY scripts/pip_rns_remotes.py scripts/pip_rns_remotes.py
COPY scripts/build/fetch_reticulum_manual.py scripts/build/fetch_reticulum_manual.py
COPY docs ./docs
COPY visualiser-wasm ./visualiser-wasm
COPY meshchatx/src/frontend ./meshchatx/src/frontend
ENV GOCACHE=/tmp/go-cache
ENV GOTMPDIR=/tmp/go-tmp
RUN mkdir -p /tmp/go-cache /tmp/go-tmp && \
    npm install -g pnpm@11.1.2 && \
    pnpm config set verify-store-integrity true && \
    pnpm install --frozen-lockfile && \
    MESHCHATX_REQUIRE_VISUALISER_WASM=1 pnpm run build-frontend && \
    test -s meshchatx/src/frontend/public/vendor/visualiser-wasm/visualiser.wasm && \
    test -s meshchatx/src/frontend/public/vendor/visualiser-wasm/wasm_exec.js && \
    test -s meshchatx/src/frontend/public/vendor/micron-parser-go/micron-parser-go.wasm && \
    test -s meshchatx/src/frontend/public/vendor/micron-parser-go/wasm_exec.js && \
    pnpm run build-docs

# ---- STAGE 2: Python Builder ----

FROM ${PYTHON_IMAGE}@${PYTHON_HASH} AS builder
WORKDIR /build
RUN apk upgrade --no-cache && \
    apk add --no-cache gcc g++ musl-dev linux-headers python3-dev libffi-dev openssl-dev git

# Install build tools in the system python
RUN pip install --no-cache-dir --upgrade "pip>=26.0" uv setuptools wheel "jaraco.context>=6.1.0"

# Create the clean venv for our application dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Install essential runtime tools in the venv (cffi verify needs setuptools on Python 3.12+)
RUN pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0"

COPY pyproject.toml uv.lock README.md CHANGELOG.md ./
COPY logo ./logo
COPY vendor ./vendor
COPY scripts/docker-bake-lxst-filterlib-musl.py ./scripts/docker-bake-lxst-filterlib-musl.py
COPY scripts/patch_lxst_pyogg_ogg_ctypes.py ./scripts/patch_lxst_pyogg_ogg_ctypes.py
COPY scripts/patch_lxst_codec2_optional.py ./scripts/patch_lxst_codec2_optional.py
# Third-party deps layer: stable across app-only updates when uv.lock is unchanged.
# --inexact keeps setuptools/jaraco.context already in the venv (cffi bake needs them).
RUN uv sync --no-group dev --no-install-project --inexact && \
    rm -rf /root/.cache/pip /root/.cache/uv && \
    pip install --no-cache-dir --upgrade "setuptools" "jaraco.context>=6.1.0" && \
    python scripts/patch_lxst_pyogg_ogg_ctypes.py && \
    python scripts/patch_lxst_codec2_optional.py && \
    python scripts/docker-bake-lxst-filterlib-musl.py && \
    rm -rf /opt/venv/lib/python*/site-packages/LXST/Platforms/android && \
    find /opt/venv -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf {} + && \
    python -m compileall -q /opt/venv/lib/python3.14/site-packages && \
    cp -a /opt/venv /opt/venv-deps

COPY meshchatx ./meshchatx
COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public

# App overlay: meshchatx + vendored packages + console scripts (changes often).
RUN pip install --no-cache-dir . && \
    PYVER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" && \
    SP="/opt/venv/lib/python${PYVER}/site-packages" && \
    OUT="/opt/app-overlay" && \
    mkdir -p "${OUT}/lib/python${PYVER}/site-packages" "${OUT}/bin" && \
    for pkg in meshchatx lxmfy rns_filesync; do \
      cp -a "${SP}/${pkg}" "${OUT}/lib/python${PYVER}/site-packages/"; \
    done && \
    cp -a "${SP}"/reticulum_meshchatx*.dist-info "${OUT}/lib/python${PYVER}/site-packages/" && \
    for cmd in meshchat meshchatx meshchatx-repository-http lxmfy rns-filesync; do \
      cp -a "/opt/venv/bin/${cmd}" "${OUT}/bin/"; \
    done && \
    find "${OUT}" -type d -name __pycache__ -prune -exec rm -rf {} + && \
    python -m compileall -q "${OUT}/lib/python${PYVER}/site-packages"

# ---- STAGE 3: Final Image ----
# Layer order matters for update pulls: base runtime, third-party venv, thin app overlay.
FROM ${PYTHON_IMAGE}@${PYTHON_HASH}

RUN apk upgrade --no-cache && \
    apk add --no-cache opusfile libffi espeak-ng su-exec && \
    python -m pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0" && \
    rm -rf /root/.cache/pip && \
    addgroup -g 1000 meshchat && adduser -u 1000 -G meshchat -S meshchat && \
    mkdir -p /config && chown meshchat:meshchat /config

COPY --from=builder --chown=meshchat:meshchat /opt/venv-deps /opt/venv
COPY --from=builder --chown=meshchat:meshchat /opt/app-overlay/ /opt/venv/
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Declare after COPY so per-build OCI values do not invalidate runtime or venv layers.
ARG OCI_REVISION=""
ARG OCI_VERSION=""
ARG OCI_CREATED=""

LABEL org.opencontainers.image.source="https://github.com/Quad4-Software/MeshChatX"
LABEL org.opencontainers.image.description="MeshChatX is a all in one Reticulum client."
LABEL org.opencontainers.image.licenses="MIT AND 0BSD"
LABEL org.opencontainers.image.authors="Quad4"
LABEL org.opencontainers.image.revision="${OCI_REVISION}"
LABEL org.opencontainers.image.version="${OCI_VERSION}"
LABEL org.opencontainers.image.created="${OCI_CREATED}"

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# No PulseAudio in the image: LXST LineSource/LineSink cannot open host devices.
ENV MESHCHAT_FORCE_WEB_AUDIO=1

USER meshchat

# Note: Podman defaults to OCI image layout, which drops HEALTHCHECK; use: podman build --format docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import ssl, urllib.request; urllib.request.urlopen('https://127.0.0.1:8000/api/v1/status', context=ssl._create_unverified_context())"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["meshchatx", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.reticulum-meshchatx", "--headless"]
