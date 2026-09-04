# Alpine MeshChatX image.
# Stages: frontend, python builder (deps + app overlay), runtime.
# VARIANT=standard|extra (extra adds i2pd and yggdrasil).
# LXST musl filterlib bake runs in scripts/docker/prepare-venv.sh.

ARG NODE_IMAGE=node:24-alpine
ARG NODE_HASH=sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf
ARG PYTHON_IMAGE=python:3.14.4-alpine3.23
ARG PYTHON_HASH=sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a
ARG VARIANT=standard
ARG OCI_DESCRIPTION="MeshChatX is an all-in-one Reticulum client."
ARG OCI_LICENSES="MIT AND 0BSD"

FROM --platform=linux/amd64 ${NODE_IMAGE}@${NODE_HASH} AS build-frontend
WORKDIR /src
RUN apk add --no-cache git python3 go
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml vite.config.js ./
COPY patches ./patches
COPY scripts/fetch-micron-wasm.mjs scripts/fetch-micron-wasm.mjs
COPY scripts/micron-wasm-resolve-bundled.mjs scripts/micron-wasm-resolve-bundled.mjs
COPY scripts/micron-parser-go-version.mjs scripts/micron-parser-go-version.mjs
COPY scripts/vite-dx.mjs scripts/vite-dx.mjs
COPY scripts/build-visualiser-wasm.mjs scripts/build-visualiser-wasm.mjs
COPY scripts/build-geo-wasm.mjs scripts/build-geo-wasm.mjs
COPY scripts/fetch-starter-mbtiles.mjs scripts/fetch-starter-mbtiles.mjs
COPY scripts/build-electron-shell-css.mjs scripts/build-electron-shell-css.mjs
COPY scripts/ensure-micron-parser-package.js scripts/ensure-micron-parser-package.js
COPY scripts/sync-meshchatx-docs.js scripts/sync-meshchatx-docs.js
COPY electron/loading.html electron/loading.html
COPY electron/crash.html electron/crash.html
COPY electron/assets/css/electron-shell.src.css electron/assets/css/electron-shell.src.css
COPY scripts/pip_rns_remotes.py scripts/pip_rns_remotes.py
COPY scripts/build/fetch_reticulum_manual.py scripts/build/fetch_reticulum_manual.py
COPY scripts/build/generate_service_worker.mjs scripts/build/generate_service_worker.mjs
COPY scripts/docker/build-frontend.sh scripts/docker/build-frontend.sh
COPY docs ./docs
COPY visualiser-wasm ./visualiser-wasm
COPY geo-wasm ./geo-wasm
COPY meshchatx/src/frontend ./meshchatx/src/frontend
ENV GOCACHE=/tmp/go-cache
ENV GOTMPDIR=/tmp/go-tmp
ENV STARTER_MBTILES_SKIP=1
RUN sh scripts/docker/build-frontend.sh

FROM ${PYTHON_IMAGE}@${PYTHON_HASH} AS builder
WORKDIR /build
COPY scripts/docker/builder-apk-alpine.sh scripts/docker/builder-apk-alpine.sh
COPY scripts/ci/github-install-uv.sh scripts/ci/priv.sh /tmp/ci/
RUN sh scripts/docker/builder-apk-alpine.sh \
    && UV_VERSION=0.11.15 sh /tmp/ci/github-install-uv.sh \
    && rm -rf /tmp/ci
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv pip install --no-cache "setuptools>=83.0.0" "wheel" "jaraco.context>=6.1.0"
COPY pyproject.toml uv.lock README.md CHANGELOG.md ./
COPY logo ./logo
COPY vendor ./vendor
COPY scripts/docker-bake-lxst-filterlib-musl.py ./scripts/docker-bake-lxst-filterlib-musl.py
COPY scripts/patch_lxst_pyogg_ogg_ctypes.py ./scripts/patch_lxst_pyogg_ogg_ctypes.py
COPY scripts/patch_lxst_codec2_optional.py ./scripts/patch_lxst_codec2_optional.py
COPY meshchatx/src/backend/lxst_pyogg_ctypes_compat.py ./meshchatx/src/backend/lxst_pyogg_ctypes_compat.py
COPY scripts/docker/prepare-venv.sh scripts/docker/prepare-venv.sh
COPY scripts/docker/build-app-overlay.sh scripts/docker/build-app-overlay.sh
RUN sh scripts/docker/prepare-venv.sh
COPY meshchatx ./meshchatx
COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public
RUN sh scripts/docker/build-app-overlay.sh

FROM ${PYTHON_IMAGE}@${PYTHON_HASH}
ARG VARIANT
ARG OCI_DESCRIPTION
ARG OCI_LICENSES
COPY scripts/docker/runtime-setup.sh /tmp/runtime-setup.sh
RUN sh /tmp/runtime-setup.sh "${VARIANT}" && rm /tmp/runtime-setup.sh
COPY --from=builder --chown=meshchat:meshchat /opt/venv-deps /opt/venv
COPY --from=builder --chown=meshchat:meshchat /opt/app-overlay/ /opt/venv/
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ARG OCI_REVISION=""
ARG OCI_VERSION=""
ARG OCI_CREATED=""

LABEL org.opencontainers.image.source="https://github.com/Quad4-Software/MeshChatX"
LABEL org.opencontainers.image.description="${OCI_DESCRIPTION}"
LABEL org.opencontainers.image.licenses="${OCI_LICENSES}"
LABEL org.opencontainers.image.authors="Quad4"
LABEL org.opencontainers.image.revision="${OCI_REVISION}"
LABEL org.opencontainers.image.version="${OCI_VERSION}"
LABEL org.opencontainers.image.created="${OCI_CREATED}"

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MESHCHAT_FORCE_WEB_AUDIO=1

USER meshchat

# Podman OCI layout drops HEALTHCHECK. Use: podman build --format docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import ssl, urllib.request; urllib.request.urlopen('https://127.0.0.1:8000/api/v1/status', context=ssl._create_unverified_context())"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["meshchatx", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.reticulum-meshchatx", "--headless"]
