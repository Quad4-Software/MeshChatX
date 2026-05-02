FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN apt-get update && apt-get install -y make && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --with dev --no-interaction --no-root && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV SPHINXBUILD=sphinx-build

COPY source ./source
COPY Makefile ./

RUN make html

FROM busybox:latest

RUN adduser -D -s /bin/sh webuser || true

USER webuser

COPY --from=builder --chown=webuser:webuser /app/build/html /home/webuser/html

EXPOSE 8080

CMD ["httpd", "-f", "-v", "-p", "8080", "-h", "/home/webuser/html"]
