# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: lxmf_announce."""

from __future__ import annotations


# ruff: noqa: F821


def on_lxmf_announce_received(
    self,
    aspect,
    destination_hash,
    announced_identity,
    app_data,
    announce_packet_hash,
    context=None,
):
    """Handle lxmf.delivery announces (synchronous Reticulum callback)."""
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    ctx = context or app.current_context
    if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
        return

    # check if announced identity or its hash is missing
    if not announced_identity or not announced_identity.hash:
        logger.debug(
            "Dropping announce with missing identity or hash: %s",
            RNS.prettyhexrep(destination_hash),
        )
        return

    # check if source is blocked - drop announce and path if blocked
    identity_hash = announced_identity.hash.hex()
    if app.is_destination_blocked(identity_hash, context=ctx):
        logger.debug(
            "Dropping announce from blocked source: %s",
            identity_hash,
        )
        if hasattr(self, "reticulum") and app.reticulum:
            app.reticulum.drop_path(destination_hash)
        return

    if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
        return

    logger.debug(
        "Received an announce from %s for [lxmf.delivery]",
        RNS.prettyhexrep(destination_hash),
    )

    # track announce timestamp
    app._note_announce_timestamp()

    # upsert announce to database
    ctx.announce_manager.upsert_announce(
        app.reticulum,
        announced_identity,
        destination_hash,
        aspect,
        app_data,
        announce_packet_hash,
    )

    # find announce from database
    announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
    if not announce:
        return

    # send database announce to all websocket clients
    AsyncUtils.run_async(
        app.websocket_broadcast(
            json.dumps(
                {
                    "type": "announce",
                    "announce": app.convert_db_announce_to_dict(announce),
                },
            ),
        ),
    )

    # resend all failed messages that were intended for this destination
    if ctx.config.auto_resend_failed_messages_when_announce_received.get():
        try:
            path_ready = RNS.Transport.has_path(destination_hash)
        except Exception:
            path_ready = False
        if path_ready:
            AsyncUtils.run_async(
                app.resend_failed_messages_for_destination(
                    destination_hash.hex(),
                    context=ctx,
                ),
            )
