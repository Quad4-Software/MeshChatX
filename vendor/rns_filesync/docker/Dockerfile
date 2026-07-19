# Multi-stage rootless runtime image for rns-filesync.
# Build: docker build -f docker/Dockerfile -t rns-filesync:1.0.0 .
# Run instructions: see docker/README.md

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-alpine AS builder

WORKDIR /build

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY pyproject.toml README.md LICENSE ./
COPY rns_filesync ./rns_filesync
COPY scripts ./scripts
COPY man ./man

RUN python -m pip install --no-cache-dir --upgrade pip build \
 && python scripts/bake_meta.py \
 && python -m build --wheel \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir dist/*.whl \
 && /opt/venv/bin/pip uninstall -y pip setuptools wheel \
 && find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

FROM python:${PYTHON_VERSION}-alpine AS runtime

RUN apk upgrade --no-cache \
 && adduser -D -u 1000 -h /home/filesync filesync \
 && mkdir -p /config /data /reticulum \
 && chown -R filesync:filesync /config /data /reticulum /home/filesync

COPY --from=builder /opt/venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH \
    HOME=/home/filesync \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER filesync
WORKDIR /home/filesync

VOLUME ["/config", "/data", "/reticulum"]

ENTRYPOINT ["rns-filesync"]
CMD ["--config", "/config", "--rnsconfig", "/reticulum", "-d", "/data", "--no-repl", "-q"]
