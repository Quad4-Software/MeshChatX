FROM node:22-alpine@sha256:0340fa682d72068edf603c305bfbc10e23219fb0e40df58d9ea4d6f33a9798bf AS build-frontend

WORKDIR /src

COPY package.json vite.config.js tailwind.config.js postcss.config.js ./
COPY pnpm-lock.yaml ./
COPY meshchatx/src/frontend ./meshchatx/src/frontend

RUN corepack enable && corepack prepare pnpm@latest --activate

RUN pnpm install --frozen-lockfile && \
    pnpm run build-frontend

FROM python:3.13-alpine@sha256:e7e041128ffc3e3600509f508e44d34ab08ff432bdb62ec508d01dfc5ca459f7

WORKDIR /app

RUN apk add --no-cache ffmpeg espeak-ng opusfile libffi-dev

COPY pyproject.toml poetry.lock ./
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        linux-headers \
        python3-dev && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    apk del .build-deps

COPY meshchatx ./meshchatx

COPY --from=build-frontend /src/meshchatx/public ./meshchatx/public

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "meshchatx.meshchat", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.meshchat", "--headless"]
