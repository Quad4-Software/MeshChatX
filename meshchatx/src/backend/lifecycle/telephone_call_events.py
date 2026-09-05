# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: telephone_call_events."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def on_incoming_telephone_call(app: Any, caller_identity: RNS.Identity, context=None):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    ctx = context or app.current_context
    if not ctx:
        return

    # Reject all calls if telephony is disabled
    if not ctx.config.telephone_enabled.get():
        telephone = getattr(ctx.telephone_manager, "telephone", None)
        if telephone:
            threading.Timer(
                0.5,
                lambda t=telephone: t.hangup(),
            ).start()
        return

    if ctx.telephone_manager and ctx.telephone_manager.initiation_status:
        # Outgoing dial owns the line. Reject the inbound caller so they are
        # not left ringing while we ignore the callback locally.
        print(
            "on_incoming_telephone_call: Rejecting as we are currently initiating an outgoing call.",
        )
        telephone = getattr(ctx.telephone_manager, "telephone", None)
        if telephone:
            threading.Timer(
                0.5,
                lambda t=telephone: t.hangup(),
            ).start()
        return

    caller_hash = caller_identity.hash.hex()

    # Check if caller is blocked
    if app.is_destination_blocked(caller_hash, context=ctx):
        print(f"Rejecting incoming call from blocked source: {caller_hash}")
        telephone = getattr(ctx.telephone_manager, "telephone", None)
        if telephone:
            # Use a small delay to avoid deadlocking with LXST call_handler_lock
            threading.Timer(
                0.5,
                lambda t=telephone: t.hangup(),
            ).start()
        return

    # Check for Do Not Disturb
    if ctx.config.do_not_disturb_enabled.get():
        print(f"Rejecting incoming call due to Do Not Disturb: {caller_hash}")
        telephone = getattr(ctx.telephone_manager, "telephone", None)
        if telephone:
            # Use a small delay to ensure LXST state is ready for hangup
            threading.Timer(
                0.5,
                lambda t=telephone: t.hangup(),
            ).start()
        return

    # Check if only allowing calls from contacts, or blocking all from strangers
    if (
        ctx.config.telephone_allow_calls_from_contacts_only.get()
        or ctx.config.block_all_from_strangers.get()
    ):
        if not app._is_contact(caller_hash, context=ctx):
            print(f"Rejecting incoming call from non-contact: {caller_hash}")
            telephone = getattr(ctx.telephone_manager, "telephone", None)
            if telephone:
                threading.Timer(
                    0.5,
                    lambda t=telephone: t.hangup(),
                ).start()
            return

    # Trigger voicemail handling
    ctx.voicemail_manager.handle_incoming_call(caller_identity)

    print(f"on_incoming_telephone_call: {caller_identity.hash.hex()}")
    ch = caller_identity.hash.hex()
    caller_name = (app.get_name_for_identity_hash(ch) or "").strip() or "Mesh"
    is_contact = app._is_contact(ch, context=ctx)
    AsyncUtils.run_async(
        app.websocket_broadcast(
            json.dumps(
                {
                    "type": "telephone_ringing",
                    "remote_identity_hash": ch,
                    "remote_identity_name": caller_name,
                    "is_contact": is_contact,
                },
            ),
        ),
    )


def on_telephone_call_ended(app: Any, caller_identity: RNS.Identity, context=None):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    ctx = context or app.current_context
    if not ctx:
        return
    # Stop voicemail recording if active
    ctx.voicemail_manager.stop_recording()

    print(
        f"on_telephone_call_ended: {caller_identity.hash.hex() if caller_identity else 'Unknown'}",
    )
    try:
        app.web_audio_bridge.on_call_ended()
    except Exception as e:
        logging.exception(f"Error in web_audio_bridge.on_call_ended: {e}")

    # Record call history
    if caller_identity:
        remote_identity_hash = caller_identity.hash.hex()
        remote_identity_name = app.get_name_for_identity_hash(remote_identity_hash)

        is_incoming = ctx.telephone_manager.call_is_incoming
        status_code = ctx.telephone_manager.call_status_at_end

        status_map = {
            0: "Busy",
            1: "Rejected",
            2: "Calling",
            3: "Available",
            4: "Ringing",
            5: "Connecting",
            6: "Completed",
        }
        status_text = status_map.get(status_code, f"Status {status_code}")

        duration = 0
        if ctx.telephone_manager.call_start_time:
            duration = int(time.time() - ctx.telephone_manager.call_start_time)

        ctx.database.telephone.add_call_history(
            remote_identity_hash=remote_identity_hash,
            remote_identity_name=remote_identity_name,
            is_incoming=is_incoming,
            status=status_text,
            duration_seconds=duration,
            timestamp=time.time(),
        )

        # Trigger missed call notification if it was an incoming call that ended without being established
        if is_incoming and not ctx.telephone_manager.call_was_established:
            if not app.is_destination_blocked(remote_identity_hash, context=ctx):
                ctx.database.misc.add_notification(
                    notification_type="telephone_missed_call",
                    remote_hash=remote_identity_hash,
                    title="Missed Call",
                    content=f"You missed a call from {remote_identity_name or remote_identity_hash}",
                )

                if not app.incoming_call_is_policy_filtered(
                    remote_identity_hash,
                    context=ctx,
                ):
                    AsyncUtils.run_async(
                        app.websocket_broadcast(
                            json.dumps(
                                {
                                    "type": "telephone_missed_call",
                                    "remote_identity_hash": remote_identity_hash,
                                    "remote_identity_name": remote_identity_name,
                                    "timestamp": time.time(),
                                },
                            ),
                        ),
                    )

    AsyncUtils.run_async(
        app.websocket_broadcast(
            json.dumps(
                {
                    "type": "telephone_call_ended",
                },
            ),
        ),
    )
