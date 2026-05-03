# Docker Build Stages:
# 1. build-frontend: Build static frontend assets using Node
# 2. builder: Install Python dependencies, build and collect backend files in a venv
# 3. final image: Copy venv, install runtime deps, set up container user and config
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
RUN apk add --no-cache git
COPY package.json pnpm-lock.yaml vite.config.js ./
COPY patches ./patches
COPY scripts/fetch-micron-wasm.mjs scripts/fetch-micron-wasm.mjs
COPY scripts/micron-wasm-resolve-bundled.mjs scripts/micron-wasm-resolve-bundled.mjs
COPY scripts/micron-parser-go-version.mjs scripts/micron-parser-go-version.mjs
COPY meshchatx/src/frontend ./meshchatx/src/frontend
RUN npm install -g pnpm@10.33.0 && \
    pnpm config set verify-store-integrity true && \
    pnpm install --frozen-lockfile && \
    pnpm run build-frontend

# ---- STAGE 2: Python Builder ----

FROM ${PYTHON_IMAGE}@${PYTHON_HASH} AS builder
WORKDIR /build
RUN apk upgrade --no-cache && \
    apk add --no-cache gcc g++ musl-dev linux-headers python3-dev libffi-dev openssl-dev git

# Install build tools in the system python
RUN pip install --no-cache-dir --upgrade "pip>=26.0" poetry setuptools wheel "jaraco.context>=6.1.0"

# Create the clean venv for our application dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install essential runtime tools in the venv (cffi verify needs setuptools on Python 3.12+)
RUN pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0"

COPY pyproject.toml poetry.lock README.md ./
COPY vendor ./vendor
RUN poetry config virtualenvs.create false && \
    poetry check --lock && \
    poetry install --no-root --only main --no-interaction --no-ansi && \
    rm -rf /root/.cache/pip /root/.cache/pypoetry

COPY meshchatx ./meshchatx
COPY scripts/docker-bake-lxst-filterlib-musl.py ./scripts/docker-bake-lxst-filterlib-musl.py
COPY scripts/patch_lxst_pyogg_ogg_ctypes.py ./scripts/patch_lxst_pyogg_ogg_ctypes.py
COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public

RUN pip install --no-cache-dir . && \
    python scripts/patch_lxst_pyogg_ogg_ctypes.py && \
    python scripts/docker-bake-lxst-filterlib-musl.py && \
    find /opt/venv -type d -name "tests" -exec rm -rf {} + && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + && \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + && \
    python -m compileall /opt/venv/lib/python3.14/site-packages

# ---- STAGE 3: Final Image ----
FROM ${PYTHON_IMAGE}@${PYTHON_HASH}

ARG OCI_REVISION=""
ARG OCI_VERSION=""
ARG OCI_CREATED=""

RUN apk upgrade --no-cache && \
    apk add --no-cache opusfile libffi espeak-ng su-exec && \
    python -m pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0" && \
    rm -rf /root/.cache/pip && \
    addgroup -g 1000 meshchat && adduser -u 1000 -G meshchat -S meshchat && \
    mkdir -p /config && chown meshchat:meshchat /config

COPY --from=builder --chown=meshchat:meshchat /opt/venv /opt/venv
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

LABEL org.opencontainers.image.source="https://git.quad4.io/RNS-Things/MeshChatX"
LABEL org.opencontainers.image.description="MeshChatX is a all in one Reticulum client."
LABEL org.opencontainers.image.licenses="MIT AND 0BSD"
LABEL org.opencontainers.image.authors="Quad4"
LABEL org.opencontainers.image.revision="${OCI_REVISION}"
LABEL org.opencontainers.image.version="${OCI_VERSION}"
LABEL org.opencontainers.image.created="${OCI_CREATED}"

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER meshchat

# Note: Podman defaults to OCI image layout, which drops HEALTHCHECK; use: podman build --format docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import ssl, urllib.request; urllib.request.urlopen('https://127.0.0.1:8000/api/v1/status', context=ssl._create_unverified_context())"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["meshchatx", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.reticulum-meshchatx", "--headless"]
