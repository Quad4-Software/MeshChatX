FROM python:3.13-alpine@sha256:79e7a9b9ff1cbceff819f856fb374477792a5967759d94df266de7b7b4120e6f

LABEL org.opencontainers.image.source="https://github.com/Quad4-Software/LXMFy"
LABEL org.opencontainers.image.description="Easily create LXMF bots for the Reticulum Network with this extensible framework."
LABEL org.opencontainers.image.licenses="BSD-0-Clause"
LABEL org.opencontainers.image.authors="LXMFy"

WORKDIR /bot

RUN mkdir -p /root/.reticulum /bot/config

COPY docker/requirements-poetry.txt /tmp/requirements-poetry.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-poetry.txt

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root

COPY . /bot
RUN poetry install --only main

CMD ["lxmfy", "run", "echo"]
