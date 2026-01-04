ARG NODE_IMAGE=node:22-alpine
ARG NODE_HASH=sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf
ARG PYTHON_IMAGE=python:3.13-alpine
ARG PYTHON_HASH=sha256:e7e041128ffc3e3600509f508e44d34ab08ff432bdb62ec508d01dfc5ca459f7

FROM ${NODE_IMAGE}@${NODE_HASH} AS build-frontend

WORKDIR /src

COPY package.json vite.config.js tailwind.config.js postcss.config.js ./
COPY pnpm-lock.yaml ./
COPY meshchatx/src/frontend ./meshchatx/src/frontend

RUN corepack enable && corepack prepare pnpm@latest --activate

RUN pnpm install --frozen-lockfile && \
    pnpm run build-frontend

FROM ${PYTHON_IMAGE}@${PYTHON_HASH}

WORKDIR /app

RUN apk add --no-cache ffmpeg espeak-ng opusfile libffi-dev su-exec py3-setuptools && \
    addgroup -g 1000 meshchat && adduser -u 1000 -G meshchat -S meshchat && \
    mkdir -p /config && chown meshchat:meshchat /config

COPY pyproject.toml poetry.lock ./
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        linux-headers \
        python3-dev && \
    pip install --no-cache-dir poetry setuptools && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    # Trigger LXST filter compilation while build tools are still present
    # We use a more thorough approach to ensure compilation completes
    python -c "import LXST; import LXST.Filters" || true && \
    python -m compileall /usr/local/lib/python3.13/site-packages && \
    apk del .build-deps

COPY --chown=meshchat:meshchat meshchatx ./meshchatx
COPY --from=build-frontend --chown=meshchat:meshchat /src/meshchatx/public ./meshchatx/public

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["sh", "-c", "chown -R meshchat:meshchat /config && exec su-exec meshchat python -m meshchatx.meshchat --host=0.0.0.0 --reticulum-config-dir=/config/.reticulum --storage-dir=/config/.meshchat --headless"]
