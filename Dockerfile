# Docker Build Stages:
# 1. build-frontend: Build static frontend assets using Node
# 2. builder: Install Python dependencies, build and collect backend files in a venv
# 3. final image: Copy venv, install runtime deps, set up container user and config

# ---- Global Build Args ----
ARG NODE_IMAGE=node:24-alpine
ARG NODE_HASH=sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf
ARG PYTHON_IMAGE=python:3.14.4-alpine3.23
ARG PYTHON_HASH=sha256:27ac3ba1699f7a526ad19bf0d35c12369b43d3439e08297a880398d97899c3d8

# ---- STAGE 1: Frontend Build ----
FROM ${NODE_IMAGE}@${NODE_HASH} AS build-frontend
WORKDIR /src
RUN apk add --no-cache git
COPY package.json pnpm-lock.yaml vite.config.js tailwind.config.js postcss.config.js ./
COPY meshchatx/src/frontend ./meshchatx/src/frontend
RUN npm install -g pnpm@10.32.1 && \
    pnpm config set verify-store-integrity true && \
    pnpm install --frozen-lockfile && \
    pnpm run build-frontend

# ---- STAGE 2: Python Builder ----

FROM ${PYTHON_IMAGE}@${PYTHON_HASH} AS builder
WORKDIR /build
RUN apk upgrade --no-cache && \
    apk add --no-cache gcc musl-dev linux-headers python3-dev libffi-dev openssl-dev git

# Install build tools in the system python
RUN pip install --no-cache-dir --upgrade "pip>=26.0" poetry setuptools wheel "jaraco.context>=6.1.0"

# Create the clean venv for our application dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install essential runtime tools in the venv
RUN pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0"

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry check --lock && \
    poetry install --no-root --only main --no-interaction --no-ansi && \
    rm -rf /root/.cache/pip /root/.cache/pypoetry

COPY meshchatx ./meshchatx
COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public

RUN pip install --no-cache-dir . && \
    python -c "import LXST.Filters; print('LXST Filters compiled successfully')" && \
    # Remove unnecessary files from the venv
    find /opt/venv -type d -name "tests" -exec rm -rf {} + && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + && \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + && \
    python -m compileall /opt/venv/lib/python3.14/site-packages

# ---- STAGE 3: Final Image ----
FROM ${PYTHON_IMAGE}@${PYTHON_HASH}

RUN apk upgrade --no-cache && \
    apk add --no-cache opusfile libffi espeak-ng su-exec && \
    python -m pip install --no-cache-dir --upgrade "pip>=26.0" "setuptools" "jaraco.context>=6.1.0" && \
    rm -rf /root/.cache/pip && \
    addgroup -g 1000 meshchat && adduser -u 1000 -G meshchat -S meshchat && \
    mkdir -p /config && chown meshchat:meshchat /config

COPY --from=builder --chown=meshchat:meshchat /opt/venv /opt/venv
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER meshchat

# Note: Podman defaults to OCI image layout, which drops HEALTHCHECK; use: podman build --format docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import ssl, urllib.request; urllib.request.urlopen('https://127.0.0.1:8000/api/v1/status', context=ssl._create_unverified_context())"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["meshchatx", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.meshchat", "--headless"]
