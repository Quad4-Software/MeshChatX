# Build arguments
ARG NODE_VERSION=20
ARG NODE_ALPINE_SHA256=sha256:6a91081a440be0b57336fbc4ee87f3dab1a2fd6f80cdb355dcf960e13bda3b59
ARG PYTHON_VERSION=3.11
ARG PYTHON_ALPINE_SHA256=sha256:822ceb965f026bc47ee667e50a44309d2d81087780bbbf64f2005521781a3621

# Build the frontend
FROM node:${NODE_VERSION}-alpine@${NODE_ALPINE_SHA256} AS build-frontend

WORKDIR /src

# Copy required source files
COPY package.json vite.config.js ./
COPY pnpm-lock.yaml ./
COPY meshchatx ./meshchatx

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install NodeJS deps, exluding electron
RUN pnpm install --prod && \
  pnpm run build-frontend

# Main app build
FROM python:${PYTHON_VERSION}-alpine@${PYTHON_ALPINE_SHA256}

WORKDIR /app

# Install Python deps
COPY ./requirements.txt .
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        linux-headers \
        python3-dev && \
    pip install -r requirements.txt && \
    apk del .build-deps

# Copy prebuilt frontend
COPY --from=build-frontend /src/meshchatx/public meshchatx/public

# Copy other required source files
COPY meshchatx ./meshchatx
COPY pyproject.toml poetry.lock ./

CMD ["python", "-m", "meshchatx.meshchat", "--host=0.0.0.0", "--reticulum-config-dir=/config/.reticulum", "--storage-dir=/config/.meshchat", "--headless"]
