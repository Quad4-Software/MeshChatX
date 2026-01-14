ARG NODE_IMAGE=node:22-alpine
ARG NODE_HASH=sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf
ARG PYTHON_IMAGE=python:3.12.12-alpine3.23
ARG PYTHON_HASH=sha256:68d81cd281ee785f48cdadecb6130d05ec6957f1249814570dc90e5100d3b146

# Stage 1: Build Frontend
FROM ${NODE_IMAGE}@${NODE_HASH} AS build-frontend
WORKDIR /src
COPY package.json pnpm-lock.yaml vite.config.js tailwind.config.js postcss.config.js ./
COPY meshchatx/src/frontend ./meshchatx/src/frontend
RUN corepack enable && corepack prepare pnpm@latest --activate && \
    pnpm install --frozen-lockfile && \
    pnpm run build-frontend

# Stage 2: Build Backend & Virtual Environment
FROM ${PYTHON_IMAGE}@${PYTHON_HASH} AS builder
WORKDIR /build
# Install build dependencies for C-extensions
RUN apk add --no-cache gcc musl-dev linux-headers python3-dev libffi-dev openssl-dev git
# Setup venv and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir "pip>=25.3" poetry setuptools wheel "jaraco.context>=6.1.0" && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Copy source code and built frontend
COPY meshchatx ./meshchatx
COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public

# Install the package itself into the venv
RUN pip install . && \
    # Trigger LXST filter compilation while build tools are still present
    python -c "import LXST.Filters; print('LXST Filters compiled successfully')" && \
    python -m compileall /opt/venv/lib/python3.12/site-packages

# Stage 3: Final Runtime Image
FROM ${PYTHON_IMAGE}@${PYTHON_HASH}
WORKDIR /app
# Install runtime dependencies only
# We keep py3-setuptools because CFFI/LXST might need it at runtime on Python 3.12+
RUN apk add --no-cache ffmpeg opusfile libffi su-exec py3-setuptools espeak-ng && \
    python -m pip install --no-cache-dir --upgrade "pip>=25.3" "jaraco.context>=6.1.0" && \
    addgroup -g 1000 meshchat && adduser -u 1000 -G meshchat -S meshchat && \
    mkdir -p /config && chown meshchat:meshchat /config

# Copy the virtual environment from the build stage
COPY --from=builder --chown=meshchat:meshchat /opt/venv /opt/venv

# Set up environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the app using the installed 'meshchat' entrypoint
CMD ["sh", "-c", "chown -R meshchat:meshchat /config && exec su-exec meshchat meshchat --host=0.0.0.0 --reticulum-config-dir=/config/.reticulum --storage-dir=/config/.meshchat --headless"]
