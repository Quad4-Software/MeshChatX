ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine

LABEL org.opencontainers.image.source="https://git.quad4.io/LXMFy/LXMFy"
LABEL org.opencontainers.image.description="Easily create LXMF bots for the Reticulum Network with this extensible framework."
LABEL org.opencontainers.image.licenses="BSD-0-Clause"
LABEL org.opencontainers.image.authors="LXMFy"

WORKDIR /bot

RUN mkdir -p /root/.reticulum /bot/config

RUN apk add --no-cache curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root

COPY . /bot
RUN poetry install --only main

CMD ["lxmfy", "run", "echo"]
