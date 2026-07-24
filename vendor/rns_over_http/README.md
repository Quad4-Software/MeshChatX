# RNS-over-HTTP

[Русский](README-RU.md)

A custom Reticulum interface that tunnels traffic over standard HTTP/S POST requests. This allows Reticulum to operate on networks where only web traffic is permitted, effectively bypassing firewalls, DPI, and other restrictions.

Packet boundaries on the wire use the same simplified HDLC framing as Reticulum's `PipeInterface`, so multiple packets can share one HTTP body without merging.

[Non-GitHub Mirror](https://lavaforge.org/Ivan/RNS-over-HTTP). Also available on the network `RNS-over-HTTP` node.

## Overview

RNS-over-HTTP creates a bidirectional transport layer using a simple client-server model:

-   **Server**: Runs on a machine with a public IP, listening for HTTP requests.
-   **Client**: Can be behind a firewall or NAT, only needing outbound internet access.

The client polls the server with HTTP POST requests, sending any outbound data in the request body and receiving inbound data in the response body. This makes the traffic appear as normal web activity.

## How It Works

The interface mimics a persistent connection using a long-polling-like mechanism:

1.  The client sends an HTTP POST request to the server, with any pending HDLC-framed packets in the request body.
2.  The server receives the request. It deframes inbound packets for Reticulum and immediately sends back any queued outbound packets (also HDLC-framed) in the HTTP response body.
3.  The client receives the response, deframes packets, and hands them to Reticulum.
4.  After a short, configurable polling interval, the client repeats the process.

This continuous cycle creates a reliable, albeit higher-latency, communication channel.

## Features

-   **Firewall & DPI Evasion**: Tunnels any traffic through standard HTTP/S ports (80/443).
-   **Bidirectional Communication**: Full-duplex data transfer.
-   **Pipe-compatible framing**: HDLC FLAG/ESC framing identical to `PipeInterface`.
-   **Simple setup**: Python, `httpx`, Hypercorn/aioquic for HTTP/2–3, and Reticulum (`rns`). Use Poetry in this repo for deps and tests.
-   **Reliable**: Automatic connection retry with exponential backoff.
-   **Flexible**: Supports custom MTU sizes and configurable polling intervals.
-   **Proxy-Friendly**: Works seamlessly behind reverse proxies like Caddy or Nginx.
-   **Connection reuse**: Keep-alive / multiplexed sessions by default, reducing handshake noise visible to DPI.
-   **HTTP/1.1, HTTP/2, and HTTP/3**: Choose the version that matches your path. Default stays HTTP/1.1 for cleartext and reverse-proxy backends.

## Getting Started

### Requirements

-   Python 3.10 or later
-   [Poetry](https://python-poetry.org/docs/#installation) (for a reproducible dev environment and tests)

### Installation

1.  **Install dependencies with Poetry** (from this repository root):
    ```bash
    poetry install
    ```

2.  **Install the custom interface for Reticulum:**
    Copy `HTTPInterface.py` into your Reticulum interfaces directory: `~/.reticulum/interfaces/`.

### Tests

```bash
# Unit, integration, and fuzz tests
poetry run pytest -m "not live"

# Full live Reticulum tests (two instances over HTTP + local shared-instance client)
poetry run pytest -m live
```

## Configuration

Add an interface entry to your Reticulum configuration file (`~/.reticulum/config`) on both the server and client machines. The config `type` must match the module basename (`HTTPInterface`).

### Server Configuration

The server listens for incoming connections from clients.

```ini
[[HTTP Server Interface]]
    type = HTTPInterface
    enabled = true
    mode = server
    listen_host = 0.0.0.0
    listen_port = 8080
    mtu = 4096
    check_user_agent = true
    user_agent = RNS-HTTP-Tunnel/1.0
```

### Client Configuration

The client connects to the server's public URL.

```ini
[[HTTP Client Interface]]
    type = HTTPInterface
    enabled = true
    mode = client
    server_url = http://your-server-ip-or-domain:8080/
    poll_interval = 0.1
    mtu = 4096
    user_agent = RNS-HTTP-Tunnel/1.0
```

## Configuration Options

### Common Options

-   `mtu`: Maximum Transmission Unit in bytes (default: `4096`).
-   `name`: Interface name for logging and identification.
-   `user_agent`: User-Agent string for HTTP requests and server checks (default: `RNS-HTTP-Tunnel/1.0`).

### Server Mode Options

-   `mode`: Must be set to `server`.
-   `listen_host`: Host to bind the HTTP server to (default: `0.0.0.0`).
-   `listen_port`: Port to listen on (default: `8080`).
-   `check_user_agent`: Whether to validate User-Agent headers (default: `true`).
-   `serve_html_page`: Serve an HTML page on GET `/` (default: `false`).
-   `html_file_path`: Path to the HTML file used when `serve_html_page` is enabled.

### Client Mode Options

-   `mode`: Must be set to `client`.
-   `server_url`: Full URL of the server to connect to (required for client mode).
-   `poll_interval`: Polling interval in seconds (default: `0.1`).
-   `pool_connections` / `pool_maxsize`: Keepalive pool sizing for HTTP/1.1 and HTTP/2 (default: `1`).

### HTTP Version and TLS

-   `http_version`: `1` (default), `2`, or `3`.
-   **HTTP/1.1**: cleartext `http://` or TLS. Best behind Caddy/nginx that already terminate HTTP/2 or HTTP/3.
-   **HTTP/2**: requires `https://` and server `tls_certfile` / `tls_keyfile`. Client uses `httpx` with ALPN `h2`.
-   **HTTP/3**: requires `https://` and the same TLS files. Server enables Hypercorn QUIC bind. Client keeps one aioquic QUIC session across polls.
-   `tls_verify`: client certificate verification (default: `true`). Set `false` only for lab/self-signed setups.
-   `tls_ca_certs`: optional CA bundle path for client verification.
-   `keepalive_timeout`: idle keepalive budget in seconds (default: `60`).

Example HTTP/2 server/client:

```ini
[[HTTP Server Interface]]
    type = HTTPInterface
    enabled = true
    mode = server
    http_version = 2
    listen_host = 0.0.0.0
    listen_port = 443
    tls_certfile = /path/to/fullchain.pem
    tls_keyfile = /path/to/privkey.pem

[[HTTP Client Interface]]
    type = HTTPInterface
    enabled = true
    mode = client
    http_version = 2
    server_url = https://your-server.example/
    tls_verify = true
```

## Reverse Proxy Setup (Caddy Example)

### Subdomain

```caddy
# Caddyfile for example.yourdomain.com
example.yourdomain.com {
    reverse_proxy 127.0.0.1:8080

    header {
        # Hide the server software version
        -Server
        # Prevent MIME-type sniffing
        X-Content-Type-Options nosniff
    }
}
```

### Main Domain

```caddy
yourdomain.com {
    reverse_proxy 127.0.0.1:8080

    header {
        # Hide the server software version
        -Server
        # Prevent MIME-type sniffing
        X-Content-Type-Options nosniff
    }
}
```

## Security Considerations

-   **Use HTTPS**: Helps bypass some firewalls and DPI that could potentially see reticulum data.
-   **User-Agent Check**: By default, the server validates the `User-Agent` header (`RNS-HTTP-Tunnel/1.0`). This provides basic protection against web crawlers and casual scanning. To mimic a common browser under sophisticated DPI, set a matching `user_agent` on both sides and keep `check_user_agent = true`, or set `check_user_agent = false` on the server.

## License

This project is licensed under the [MIT License](LICENSE).
