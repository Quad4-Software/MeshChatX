# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_lxmf."""

from __future__ import annotations

import base64
import json

import LXMF
import RNS

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.constants import WsInboundType
from meshchatx.src.backend.meshchat_utils import normalize_identity_storage_hash


async def handle_lxmf_forwarding_rules_get(app, client, data):
    rules = app.database.misc.get_forwarding_rules()
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "lxmf.forwarding.rules",
                    "rules": [
                        {
                            "id": rule["id"],
                            "name": rule.get("name") or "",
                            "identity_hash": rule["identity_hash"],
                            "forward_to_hash": rule["forward_to_hash"],
                            "source_filter_hash": rule["source_filter_hash"],
                            "is_active": bool(rule["is_active"]),
                        }
                        for rule in rules
                    ],
                },
            ),
        ),
    )


def _canonical_forwarding_dest_hash(raw) -> str | None:
    """32-char dest hash, or None. Empty optional filters become empty string."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    canonical = normalize_identity_storage_hash(text)
    return canonical or None


async def handle_lxmf_forwarding_rule_add(app, client, data):
    rule_data = data.get("rule")
    if not rule_data or "forward_to_hash" not in rule_data:
        print(
            "Missing rule data or forward_to_hash in lxmf.forwarding.rule.add",
        )
        return

    forward_to_hash = _canonical_forwarding_dest_hash(rule_data.get("forward_to_hash"))
    if not forward_to_hash:
        print("Invalid forward_to_hash in lxmf.forwarding.rule.add")
        return

    identity_raw = rule_data.get("identity_hash")
    identity_hash = _canonical_forwarding_dest_hash(identity_raw)
    if identity_raw not in (None, "") and identity_hash is None:
        print("Invalid identity_hash in lxmf.forwarding.rule.add")
        return
    if identity_hash == "":
        identity_hash = None

    source_raw = rule_data.get("source_filter_hash")
    source_filter_hash = _canonical_forwarding_dest_hash(source_raw)
    if source_raw not in (None, "") and source_filter_hash is None:
        print("Invalid source_filter_hash in lxmf.forwarding.rule.add")
        return
    if source_filter_hash == "":
        source_filter_hash = None

    app.database.misc.create_forwarding_rule(
        identity_hash=identity_hash,
        forward_to_hash=forward_to_hash,
        source_filter_hash=source_filter_hash,
        is_active=rule_data.get("is_active", True),
        name=rule_data.get("name"),
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {"type": WsInboundType.LXMF_FORWARDING_RULES_GET},
        ),
    )


async def handle_lxmf_forwarding_rule_delete(app, client, data):
    rule_id = data.get("id")
    if rule_id is not None:
        app.database.misc.delete_forwarding_rule(rule_id)
        # notify updated
        AsyncUtils.run_async(
            app.on_websocket_data_received(
                client,
                {"type": WsInboundType.LXMF_FORWARDING_RULES_GET},
            ),
        )


async def handle_lxmf_forwarding_rule_toggle(app, client, data):
    rule_id = data.get("id")
    if rule_id is not None:
        app.database.misc.toggle_forwarding_rule(rule_id)
        # notify updated
        AsyncUtils.run_async(
            app.on_websocket_data_received(
                client,
                {"type": WsInboundType.LXMF_FORWARDING_RULES_GET},
            ),
        )

    # handle ingesting an lxmf uri (paper message)


async def handle_lxm_ingest_uri(app, client, data):
    uri = data.get("uri")
    if not uri:
        return

    local_delivery_signal = "local_delivery_occurred"
    duplicate_signal = "duplicate_lxm"

    try:
        uri_raw = uri.strip()
        lu = uri_raw.lower()
        if lu.startswith("meshchatx://map") or lu.startswith("meshchat://map"):
            from urllib.parse import parse_qsl, urlparse

            parsed = urlparse(uri_raw)
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            try:
                lat = float(q.get("lat", "") or "")
                lon = float(q.get("lon", "") or "")
            except (TypeError, ValueError):
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.ingest_uri.result",
                                "status": "error",
                                "message": "Invalid map link: lat and lon must be numbers.",
                            },
                        ),
                    ),
                )
                return
            zraw = q.get("z") or q.get("zoom") or "10"
            try:
                zoom = int(float(zraw))
            except (TypeError, ValueError):
                zoom = 10
            zoom = max(0, min(22, zoom))
            layers = (q.get("layers") or "").strip()
            label = (q.get("label") or "").strip()
            mq = {
                "lat": lat,
                "lon": lon,
                "zoom": zoom,
            }
            if layers:
                mq["layers"] = layers
            if label:
                mq["label"] = label
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "success",
                            "message": "Opening map view.",
                            "ingest_type": "map_view",
                            "map_query": mq,
                        },
                    ),
                ),
            )
            return

        if uri_raw.lower().startswith(("meshchatx://", "meshchat://")):
            from urllib.parse import parse_qsl, unquote, urlparse

            _parsed = urlparse(uri_raw)
            _sch = (_parsed.scheme or "").lower()
            _host = (_parsed.netloc or "").lower()
            if _sch in ("meshchatx", "meshchat") and _host == "docs":
                _q = dict(parse_qsl(_parsed.query, keep_blank_values=True))
                rel = (_q.get("reticulum") or _q.get("path") or "").strip()
                if not rel and _parsed.path and _parsed.path != "/":
                    rel = unquote(_parsed.path.lstrip("/"))
                payload: dict = {
                    "type": "lxm.ingest_uri.result",
                    "status": "success",
                    "message": "Opening documentation.",
                    "ingest_type": "docs_view",
                }
                if rel:
                    payload["docs_query"] = {"reticulum": rel}
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(payload),
                    ),
                )
                return

            # Known hosts (map/docs) are handled above. Relay and app
            # deep links are frontend-routed. Anything else must not
            # fall through to LXMF ingest.
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "error",
                            "message": (
                                f"Unknown or unsupported meshchatx link host "
                                f"'{_host or '(empty)'}'. "
                                "Supported hosts include map, docs, relay, and app."
                            ),
                            "ingest_type": "unknown_meshchatx",
                            "host": _host,
                        },
                    ),
                ),
            )
            return

        # LXMA contact sharing URI:
        # lxma://<destination_hash_hex>:<public_key_hex>
        if uri_raw.lower().startswith("lxma://"):
            from meshchatx.src.backend.lxma_contact import bind_lxma_contact

            destination_hash_hex, identity = bind_lxma_contact(
                uri_raw,
                app._identity_from_public_key_bytes,
            )

            remote_identity_hash = identity.hash.hex()
            existing_contact = app.database.contacts.get_contact_by_identity_hash(
                remote_identity_hash,
            )
            contact_name = (
                existing_contact["name"]
                if existing_contact and existing_contact.get("name")
                else f"Contact {destination_hash_hex[:8]}"
            )

            app.database.contacts.add_contact(
                contact_name,
                remote_identity_hash,
                lxmf_address=destination_hash_hex,
            )
            app.sync_telephone_call_policy()

            # Persist pubkey so outbound LXMF works before any announce.
            try:
                RNS.Identity.remember(
                    None,
                    bytes.fromhex(destination_hash_hex),
                    identity.get_public_key(),
                    None,
                )
            except Exception as remember_exc:
                print(
                    f"LXMA remember failed for {destination_hash_hex}: "
                    f"{type(remember_exc).__name__}: {remember_exc!r}",
                )

            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxm.ingest_uri.result",
                            "status": "success",
                            "message": f"Contact imported from LXMA URI ({destination_hash_hex})",
                            "ingest_type": "lxma_contact",
                            "destination_hash": destination_hash_hex,
                        },
                    ),
                ),
            )
            return

        # ensure uri starts with lxmf:// or lxm://
        if not uri.lower().startswith(
            LXMF.LXMessage.URI_SCHEMA + "://",
        ) and not uri.lower().startswith("lxm://"):
            if ":" in uri and "//" not in uri:
                uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri
            else:
                uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri

        ingest_result = app.message_router.ingest_lxm_uri(
            uri,
            signal_local_delivery=local_delivery_signal,
            signal_duplicate=duplicate_signal,
        )

        if ingest_result is False:
            response = "The URI contained no decodable messages"
            status = "error"
        elif ingest_result == local_delivery_signal:
            response = "Message was decoded, decrypted successfully, and added to your conversation list."
            status = "success"
        elif ingest_result == duplicate_signal:
            response = "The decoded message has already been processed by the LXMF Router, and will not be ingested again."
            status = "info"
        else:
            response = "The decoded message was not addressed to your LXMF address, and has been discarded."
            status = "warning"

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.ingest_uri.result",
                        "status": status,
                        "message": response,
                    },
                ),
            ),
        )
    except Exception as e:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.ingest_uri.result",
                        "status": "error",
                        "message": f"Error ingesting message from URI: {e!s}",
                    },
                ),
            ),
        )

    # handle generating a paper message uri


async def handle_lxm_generate_paper_uri(app, client, data):
    destination_hash = data.get("destination_hash")
    content = data.get("content")
    title = data.get("title", "")

    if not destination_hash or not content:
        return

    try:
        destination_hash_bytes = bytes.fromhex(destination_hash)
        destination_identity = RNS.Identity.recall(destination_hash_bytes)

        if destination_identity is None:
            # try to find in database
            announce = app.database.announces.get_announce_by_hash(
                destination_hash,
            )
            if announce and announce.get("identity_public_key"):
                destination_identity = RNS.Identity.from_bytes(
                    base64.b64decode(announce["identity_public_key"]),
                )

        if destination_identity is None:
            raise Exception(
                "Recipient identity not found. Please wait for an announce or add them as a contact.",
            )

        lxmf_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        lxm = LXMF.LXMessage(
            lxmf_destination,
            app.local_lxmf_destination,
            content,
            title=title,
            desired_method=LXMF.LXMessage.PAPER,
        )

        # generate uri
        uri = lxm.as_uri()

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.generate_paper_uri.result",
                        "status": "success",
                        "uri": uri,
                    },
                ),
            ),
        )
    except Exception as e:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "lxm.generate_paper_uri.result",
                        "status": "error",
                        "message": f"Error generating paper message: {e!s}",
                    },
                ),
            ),
        )

    # handle getting keyboard shortcuts


HANDLERS = {
    WsInboundType.LXMF_FORWARDING_RULES_GET: handle_lxmf_forwarding_rules_get,
    WsInboundType.LXMF_FORWARDING_RULE_ADD: handle_lxmf_forwarding_rule_add,
    WsInboundType.LXMF_FORWARDING_RULE_DELETE: handle_lxmf_forwarding_rule_delete,
    WsInboundType.LXMF_FORWARDING_RULE_TOGGLE: handle_lxmf_forwarding_rule_toggle,
    WsInboundType.LXM_INGEST_URI: handle_lxm_ingest_uri,
    WsInboundType.LXM_GENERATE_PAPER_URI: handle_lxm_generate_paper_uri,
}
