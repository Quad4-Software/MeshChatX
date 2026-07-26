# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import secrets

from aiohttp import web
from aiohttp_session import setup as setup_session

from tests.backend.conftest import extend_meshchat_middlewares


def build_test_aio_app(app, *, https: bool = False):
    app.session_secret_key = secrets.token_urlsafe(32)
    app.listen_host = "127.0.0.1"
    app.listen_port = 8000
    app.use_https = https
    app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, app._encrypted_cookie_storage(https))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app
