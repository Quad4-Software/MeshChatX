# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: _handle_rns_link_request."""

from __future__ import annotations

import base64
from typing import Any

# ruff: noqa: F821


async def handle_rns_link_request(app: Any, client, data):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k in mc.__dict__.items():
        if not _k[0].startswith("__"):
            globals()[_k[0]] = _k[1]

    request_id = data.get("request_id")
    dest_hash, aspect, err = app._rns_link_parse_dest_aspect(data)
    if err:
        await app._rns_link_send(
            client,
            {
                "type": "rns.link.request",
                "request_id": request_id,
                "status": "failure",
                "failure_reason": err,
            },
        )
        return
    path = data.get("path")
    if not path:
        await app._rns_link_send(
            client,
            {
                "type": "rns.link.request",
                "request_id": request_id,
                "status": "failure",
                "failure_reason": "missing_path",
            },
        )
        return
    # data_b64 is msgpack-encoded request payload. Decode to a native value
    # so RNS.Link.request embeds it in the wire envelope correctly.
    data_b64 = data.get("data_b64")
    try:
        body_bytes = base64.b64decode(data_b64, validate=True) if data_b64 else None
    except Exception:
        await app._rns_link_send(
            client,
            {
                "type": "rns.link.request",
                "request_id": request_id,
                "status": "failure",
                "failure_reason": "invalid_data_b64",
            },
        )
        return
    if body_bytes is None or len(body_bytes) == 0:
        link_request_data = None
    else:
        try:
            from RNS.vendor import umsgpack

            link_request_data = umsgpack.unpackb(body_bytes)
        except Exception as e:
            await app._rns_link_send(
                client,
                {
                    "type": "rns.link.request",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": f"data_msgpack_decode_failed: {e}",
                },
            )
            return
    timeout = data.get("timeout")

    def on_phase(phase):
        AsyncUtils.run_async(
            app._rns_link_send(
                client,
                {
                    "type": "rns.link.request",
                    "request_id": request_id,
                    "status": "phase",
                    "phase": phase,
                    "destination_hash": dest_hash.hex(),
                    "aspect": aspect,
                },
            ),
        )

    link, _identified, failure_reason = await app.rns_link_manager.open_link(
        dest_hash,
        aspect,
        auto_identify=False,
        on_phase=on_phase,
    )
    if link is None:
        await app._rns_link_send(
            client,
            {
                "type": "rns.link.request",
                "request_id": request_id,
                "status": "failure",
                "failure_reason": failure_reason or "unknown",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )
        return

    def on_response(request_receipt):
        app._rns_request_receipts.pop((client, request_id), None)
        raw = request_receipt.response
        from RNS.vendor import umsgpack

        try:
            if hasattr(raw, "read") and not isinstance(raw, (bytes, bytearray)):
                raw_to_pack = raw.read()
            else:
                raw_to_pack = raw
            body_b64 = base64.b64encode(umsgpack.packb(raw_to_pack)).decode("ascii")
        except Exception as e:
            print(f"[rns.link.request] msgpack encode failed: {e}")
            body_b64 = ""
        AsyncUtils.run_async(
            app._rns_link_send(
                client,
                {
                    "type": "rns.link.request",
                    "request_id": request_id,
                    "status": "success",
                    "body_b64": body_b64,
                    "destination_hash": dest_hash.hex(),
                    "aspect": aspect,
                },
            ),
        )

    def on_failed(_receipt=None):
        app._rns_request_receipts.pop((client, request_id), None)
        AsyncUtils.run_async(
            app._rns_link_send(
                client,
                {
                    "type": "rns.link.request",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": "request_failed",
                    "destination_hash": dest_hash.hex(),
                    "aspect": aspect,
                },
            ),
        )

    def on_progress(receipt):
        AsyncUtils.run_async(
            app._rns_link_send(
                client,
                {
                    "type": "rns.link.request",
                    "request_id": request_id,
                    "status": "progress",
                    "progress": receipt.progress,
                    "destination_hash": dest_hash.hex(),
                    "aspect": aspect,
                },
            ),
        )

    try:
        receipt = app.rns_link_manager.request(
            dest_hash,
            aspect,
            path,
            link_request_data,
            response_callback=on_response,
            failed_callback=on_failed,
            progress_callback=on_progress,
            timeout=timeout,
        )
        app._rns_request_receipts[(client, request_id)] = receipt
    except Exception as e:
        await app._rns_link_send(
            client,
            {
                "type": "rns.link.request",
                "request_id": request_id,
                "status": "failure",
                "failure_reason": f"request_dispatch_failed: {e}",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )
