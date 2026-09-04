# SPDX-License-Identifier: 0BSD

"""aiohttp middleware factories for MeshChatX HTTP.

Factories take the live app instance and return middleware callables.
Order returned by register_all_routes / _define_routes must remain:
sqlite_unavailable, auth, mime_type, security, csrf, ip_allowlist, demo_mode.
"""

from __future__ import annotations

from urllib.parse import urlparse

from aiohttp import web
from aiohttp_session import get_session

from meshchatx.src.backend.app_security_settings import (
    get_trusted_proxy_cidrs,
    get_web_ui_ip_allowlist,
)
from meshchatx.src.backend.csrf import validate_csrf_header
from meshchatx.src.backend.database.sqlite_errors import sqlite_error_is_retryable
from meshchatx.src.backend.http.db_availability import (
    DB_TEMPORARILY_UNAVAILABLE,
    exception_looks_like_missing_database,
)
from meshchatx.src.backend.http.errors import http_unavailable
from meshchatx.src.backend.ip_allowlist import client_ip_allowed
from meshchatx.src.backend.privacy_mode import privacy_mode_enabled
from meshchatx.src.env_utils import env_bool
from meshchatx.src.path_utils import request_client_ip


def csrf_exempt_path(path: str) -> bool:
    return path == "/api/v1/auth/csrf"


def is_nomad_crash_tab_resource(path: str) -> bool:
    """Crash-tab HTML/JS is framed without allow-same-origin (opaque null Origin)."""
    if path == "/nomad-crash-tab.html":
        return True
    if path.startswith("/assets/") and "nomad-crash-tab" in path:
        return True
    return False


def is_opaque_frame_cors_resource(path: str) -> bool:
    """Static assets fetched by the sandboxed crash-tab (null Origin) need CORS.

    Vite splits the crash-tab entry across hashed /assets/ chunks that do not
    contain "nomad-crash-tab" in the filename (shared-async, rolldown-runtime,
    vendor-vue, Micron, fonts, CSS). Opaque-origin module scripts require ACAO.
    """
    if is_nomad_crash_tab_resource(path):
        return True
    if path.startswith("/vendor/micron-parser-go/"):
        return True
    if path.startswith("/assets/"):
        return True
    return False


def build_nomad_crash_tab_csp() -> str:
    """CSP for /nomad-crash-tab.html only.

    Keeps Micron JS, Micron WASM (fetch + blob: wasm_exec inject), fonts, and
    inline styles. Drops map tiles, websocket, and other shell clearnet sources
    so CSS network paints cannot beacon even if style scrub misses.
    """
    return (
        "default-src 'none'; "
        "script-src 'self' 'wasm-unsafe-eval' blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "worker-src 'none'; "
        "media-src 'none'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )


def create_sqlite_unavailable_middleware(app):
    """Map uncaught SQLite / missing-DB races on /api to HTTP 503."""

    @web.middleware
    async def sqlite_unavailable_middleware(request, handler):
        try:
            return await handler(request)
        except Exception as exc:
            if not request.path.startswith("/api/"):
                raise
            if sqlite_error_is_retryable(exc) or exception_looks_like_missing_database(
                exc,
                app,
            ):
                return http_unavailable(DB_TEMPORARILY_UNAVAILABLE)
            raise

    return sqlite_unavailable_middleware


def create_ip_allowlist_middleware(app):
    @web.middleware
    async def ip_allowlist_middleware(request, handler):
        path = request.path
        if path == "/api/v1/status":
            return await handler(request)
        allowlist = get_web_ui_ip_allowlist(app.storage_dir)
        if allowlist:
            ip = request_client_ip(request, get_trusted_proxy_cidrs(app.storage_dir))
            if not client_ip_allowed(ip, allowlist):
                if path.startswith("/api/"):
                    return web.json_response(
                        {"error": "Forbidden: client IP not on allowlist"},
                        status=403,
                    )
                return web.Response(
                    text="Forbidden",
                    status=403,
                    headers={"Content-Type": "text/html"},
                )
        return await handler(request)

    return ip_allowlist_middleware


def create_csrf_middleware(app):
    @web.middleware
    async def csrf_middleware(request, handler):
        if env_bool("MESHCHAT_DISABLE_CSRF", False):
            return await handler(request)
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await handler(request)
        path = request.path
        if not path.startswith("/api/"):
            return await handler(request)
        if csrf_exempt_path(path):
            return await handler(request)
        try:
            session = await get_session(request)
        except Exception:
            return web.json_response(
                {"error": "Session required for CSRF validation"},
                status=403,
            )
        if not validate_csrf_header(request, session):
            return web.json_response(
                {"error": "Invalid or missing CSRF token"},
                status=403,
            )
        return await handler(request)

    return csrf_middleware


def create_auth_middleware(app):
    @web.middleware
    async def auth_middleware(request, handler):
        path = request.path

        # Health check for startup probes (Electron loading page, monitors).
        if path == "/api/v1/status":
            return await handler(request)

        # Allow CSRF bootstrap and auth status while the network stack starts so the
        # Vue shell can load and show an in-app waiting state.
        if path in (
            "/api/v1/auth/csrf",
            "/api/v1/auth/status",
            "/api/v1/auth/altcha/challenge",
        ):
            return await handler(request)

        # Serve the web UI shell and static files while an identity context is still
        # starting, so the browser can load assets and show in-app loading state.
        if not path.startswith("/api/"):
            if (
                path == "/"
                or path.startswith(
                    (
                        "/assets/",
                        "/favicons/",
                        "/reticulum-docs/",
                        "/meshchatx-docs/",
                    ),
                )
                or path in ("/manifest.json", "/service-worker.js")
                or path.endswith(
                    (
                        ".js",
                        ".css",
                        ".json",
                        ".wasm",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".ico",
                        ".svg",
                    ),
                )
            ):
                return await handler(request)

        if not app.current_context or not app.current_context.running:
            return web.json_response(
                {
                    "error": "Application is initializing or switching identity",
                    "status": "starting",
                    "stage": app._startup_stage,
                    "network_ready": False,
                },
                status=503,
            )

        if not app.auth_enabled:
            return await handler(request)

        # allow access to auth endpoints and setup page
        public_paths = [
            "/api/v1/status",
            "/api/v1/auth/csrf",
            "/api/v1/auth/setup",
            "/api/v1/auth/login",
            "/api/v1/auth/status",
            "/api/v1/auth/logout",
            "/api/v1/auth/altcha/challenge",
            "/manifest.json",
            "/service-worker.js",
        ]

        # Exact public API paths only. startswith would treat
        # /api/v1/status.json as public because it prefixes /api/v1/status.
        is_public = path in public_paths
        if path.startswith(("/reticulum-docs/", "/meshchatx-docs/")):
            is_public = True

        # Static UI files are public. API paths are not, even when they end
        # in .js/.json/.wasm (plugin assets live at /api/v1/plugins/.../asset/).
        if (
            path == "/"
            or path.startswith(
                ("/assets/", "/favicons/", "/reticulum-docs/", "/meshchatx-docs/"),
            )
            or (
                not path.startswith("/api/")
                and path.endswith(
                    (
                        ".js",
                        ".css",
                        ".json",
                        ".wasm",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".ico",
                        ".svg",
                    ),
                )
            )
        ):
            is_public = True

        if is_public:
            return await handler(request)

        # check authentication
        try:
            session = await get_session(request)
        except Exception as e:
            print(f"Session decryption failed: {e}")
            # If decryption fails, we must treat as unauthenticated
            if path.startswith("/api/"):
                return web.json_response(
                    {"error": "Session expired or invalid. Please login again."},
                    status=401,
                )
            return web.Response(
                text="Authentication required",
                status=401,
                headers={"Content-Type": "text/html"},
            )

        is_authenticated = session.get("authenticated", False)
        session_identity = session.get("identity_hash")

        # Check if authenticated AND matches current identity
        if not is_authenticated or session_identity != app.identity.hash.hex():
            if path.startswith("/api/"):
                return web.json_response(
                    {"error": "Authentication required"},
                    status=401,
                )
            return web.Response(
                text="Authentication required",
                status=401,
                headers={"Content-Type": "text/html"},
            )

        return await handler(request)

    return auth_middleware


def create_mime_type_middleware(app):
    @web.middleware
    async def mime_type_middleware(request, handler):
        response = await handler(request)
        if response is None:
            return None
        path = request.path
        if path.startswith("/api/"):
            return response
        if path.endswith((".js", ".mjs")):
            response.headers["Content-Type"] = "application/javascript; charset=utf-8"
        elif path.endswith(".css"):
            response.headers["Content-Type"] = "text/css; charset=utf-8"
        elif path.endswith(".json"):
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        elif path.endswith(".wasm"):
            response.headers["Content-Type"] = "application/wasm"
        elif path.endswith(".html"):
            response.headers["Content-Type"] = "text/html; charset=utf-8"
        elif path.endswith(".md"):
            response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        elif path.endswith(".txt"):
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
        elif path.endswith(".opus"):
            response.headers["Content-Type"] = "audio/opus"
        elif path.endswith(".ogg"):
            response.headers["Content-Type"] = "audio/ogg"
        elif path.endswith(".wav"):
            response.headers["Content-Type"] = "audio/wav"
        elif path.endswith(".mp3"):
            response.headers["Content-Type"] = "audio/mpeg"
        return response

    return mime_type_middleware


def create_security_middleware(app):
    @web.middleware
    async def security_middleware(request, handler):
        response = await handler(request)
        if response is None:
            return None
        # Add security headers to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Allow framing for docs, rnode flasher, and Nomad crash-tab renderer.
        if (
            request.path.startswith("/reticulum-docs/")
            or request.path.startswith("/rnode-flasher/")
            or is_nomad_crash_tab_resource(request.path)
        ):
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers["X-Frame-Options"] = "DENY"

        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Explicitly allow mic/camera, autoplay, speaker routing, and hardware
        # transports for this origin. Listing only mic/camera without bluetooth
        # /serial/usb has caused some Chromium and Brave builds to treat
        # hardware APIs as unavailable. Do not also send the legacy feature
        # policy header. Chromium ignores unrecognized tokens there and warns
        # when the same features appear on both headers.
        response.headers["Permissions-Policy"] = (
            "microphone=(self), camera=(self), autoplay=(self), speaker-selection=(self), "
            "bluetooth=(self), serial=(self), usb=(self)"
        )

        # CSP base configuration
        privacy_mode = privacy_mode_enabled(app.config)
        path = request.path

        # Crash-tab document: tight policy. Do not inherit shell tile/WS extras.
        if path == "/nomad-crash-tab.html":
            if is_opaque_frame_cors_resource(path):
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
            response.headers["Content-Security-Policy"] = build_nomad_crash_tab_csp()
            return response

        # IPv6 loopback with a port wildcard is not a valid CSP source
        # (ws://[::1]:* is ignored). Same-origin WS is covered by 'self'.
        connect_sources = [
            "'self'",
            "ws://localhost:*",
            "wss://localhost:*",
            "ws://127.0.0.1:*",
            "wss://127.0.0.1:*",
            "blob:",
        ]
        img_sources = [
            "'self'",
            "data:",
            "blob:",
        ]
        if not privacy_mode:
            connect_sources.extend(
                [
                    "https://*.tile.openstreetmap.org",
                    "https://tile.openstreetmap.org",
                    "https://nominatim.openstreetmap.org",
                    "https://*.cartocdn.com",
                    "https://tiles.openfreemap.org",
                    "https://*.openfreemap.org",
                ],
            )
            img_sources.extend(
                [
                    "https://*.tile.openstreetmap.org",
                    "https://tile.openstreetmap.org",
                    "https://*.cartocdn.com",
                    "https://tiles.openfreemap.org",
                    "https://*.openfreemap.org",
                ],
            )

        frame_sources = [
            "'self'",
        ]

        if path.startswith("/rnode-flasher/") or is_opaque_frame_cors_resource(path):
            # Crash-tab iframe is sandboxed without allow-same-origin so its
            # effective Origin is null. Module scripts and Micron WASM fetches
            # need CORS + CORP.
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        if path.startswith("/rnode-flasher/"):
            # Standalone RNode Flasher uses Vue in-DOM templates. The compileToFunction
            # relies on new Function(), which requires unsafe-eval.
            script_sources = [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'",
                "'wasm-unsafe-eval'",
                "blob:",
            ]
        elif path.startswith("/reticulum-docs/"):
            # blob: AudioWorklet addModule(blob:...) and similar dynamic scripts
            script_sources = [
                "'self'",
                "'unsafe-inline'",
                "'wasm-unsafe-eval'",
                "blob:",
            ]
        else:
            # wasm-unsafe-eval: Codec2 / sox Emscripten WASM, and blob: worklets from object URLs
            script_sources = ["'self'", "'wasm-unsafe-eval'", "blob:"]
        style_sources = ["'self'", "'unsafe-inline'"]

        if app.current_context and app.current_context.config and not privacy_mode:
            # Helper to add domain from URL
            def add_domain_from_url(url, target_list):
                if not url:
                    return None
                try:
                    parsed = urlparse(url)
                    if parsed.netloc:
                        domain = f"{parsed.scheme}://{parsed.netloc}"
                        if domain not in target_list:
                            target_list.append(domain)
                        return domain
                except Exception:
                    pass
                return None

            # Add configured Gitea base URL
            add_domain_from_url(
                app.current_context.config.gitea_base_url.get(),
                connect_sources,
            )

            # Add map tile server domain
            map_tile_url = app.current_context.config.map_tile_server_url.get()
            add_domain_from_url(map_tile_url, img_sources)
            add_domain_from_url(map_tile_url, connect_sources)

            # Add nominatim API domain
            nominatim_url = app.current_context.config.map_nominatim_api_url.get()
            add_domain_from_url(nominatim_url, connect_sources)

            # Add custom CSP sources from config
            def add_extra_sources(extra_str, target_list):
                if not extra_str:
                    return
                sources = [
                    s.strip()
                    for s in extra_str.replace("\n", ",").replace(";", ",").split(",")
                    if s.strip()
                ]
                for s in sources:
                    if s not in target_list:
                        target_list.append(s)

            add_extra_sources(
                app.current_context.config.csp_extra_connect_src.get(),
                connect_sources,
            )
            add_extra_sources(
                app.current_context.config.csp_extra_img_src.get(),
                img_sources,
            )
            add_extra_sources(
                app.current_context.config.csp_extra_frame_src.get(),
                frame_sources,
            )
            add_extra_sources(
                app.current_context.config.csp_extra_script_src.get(),
                script_sources,
            )
            add_extra_sources(
                app.current_context.config.csp_extra_style_src.get(),
                style_sources,
            )

        csp = (
            "default-src 'self'; "
            f"script-src {' '.join(script_sources)}; "
            f"style-src {' '.join(style_sources)}; "
            f"img-src {' '.join(img_sources)}; "
            + (
                "font-src 'self' data:; "
                if privacy_mode
                else "font-src 'self' data: https://tiles.openfreemap.org https://*.openfreemap.org; "
            )
            + f"connect-src {' '.join(connect_sources)}; "
            "media-src 'self' blob:; "
            "worker-src 'self' blob:; "
            f"frame-src {' '.join(frame_sources)}; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    return security_middleware
