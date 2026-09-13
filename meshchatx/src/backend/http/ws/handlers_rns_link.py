# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_rns_link."""

from __future__ import annotations

import asyncio

from meshchatx.src.backend.constants import WsInboundType


async def handle_rns_link_open(app, client, data):
    app._track_rns_link_task(
        client,
        asyncio.create_task(app._handle_rns_link_open(client, data)),
    )


async def handle_rns_link_identify(app, client, data):
    await app._handle_rns_link_identify(client, data)


async def handle_rns_link_request(app, client, data):
    app._track_rns_link_task(
        client,
        asyncio.create_task(app._handle_rns_link_request(client, data)),
    )


async def handle_rns_link_send(app, client, data):
    await app._handle_rns_link_send(client, data)


async def handle_rns_link_close(app, client, data):
    await app._handle_rns_link_close(client, data)


HANDLERS = {
    WsInboundType.RNS_LINK_OPEN: handle_rns_link_open,
    WsInboundType.RNS_LINK_IDENTIFY: handle_rns_link_identify,
    WsInboundType.RNS_LINK_REQUEST: handle_rns_link_request,
    WsInboundType.RNS_LINK_SEND: handle_rns_link_send,
    WsInboundType.RNS_LINK_CLOSE: handle_rns_link_close,
}
