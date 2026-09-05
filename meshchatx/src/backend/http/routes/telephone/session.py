# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone session."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_session_routes(routes, app):

    # serve telephone status
    @routes.get("/api/v1/telephone/status")
    async def telephone_status(request):
        # make sure telephone is enabled
        if app.telephone_manager.telephone is None:
            missed_calls_unread_count = 0
            if app.database is not None:
                with contextlib.suppress(Exception):
                    missed_calls_unread_count = (
                        app.database.misc.get_unread_notification_count_by_type(
                            "telephone_missed_call",
                        )
                    )
            return web.json_response(
                {
                    "enabled": False,
                    "message": "Telephone is disabled",
                    "missed_calls_unread_count": missed_calls_unread_count,
                },
            )

        # get active call info
        active_call = None
        telephone_active_call = app.telephone_manager.telephone.active_call
        if telephone_active_call is not None:
            # Filter ringing inbound calls that policy must not surface
            is_ringing = app.telephone_manager.telephone.call_status == 4
            if telephone_active_call.is_incoming and is_ringing:
                remote_identity = telephone_active_call.get_remote_identity()
                caller_hash = remote_identity.hash.hex() if remote_identity else None
                if not caller_hash or app.incoming_call_is_policy_filtered(
                    caller_hash,
                ):
                    telephone_active_call = None

        if telephone_active_call is not None:
            remote_identity = telephone_active_call.get_remote_identity()
            if remote_identity is None:
                telephone_active_call = None

        if telephone_active_call is not None:
            # remote_identity is already fetched and checked for None above
            remote_hash = remote_identity.hash.hex()
            remote_destination_hash = RNS.Destination.hash(
                remote_identity,
                "lxmf",
                "delivery",
            ).hex()
            remote_telephony_hash = app.get_lxst_telephony_hash_for_identity_hash(
                remote_hash,
            )
            remote_name = None
            if app.telephone_manager.get_name_for_identity_hash:
                remote_name = app.telephone_manager.get_name_for_identity_hash(
                    remote_hash,
                )

            # get lxmf destination hash to look up icon
            lxmf_destination_hash = RNS.Destination.hash(
                remote_identity,
                "lxmf",
                "delivery",
            ).hex()

            remote_icon = app.database.misc.get_user_icon(lxmf_destination_hash)

            # Check if contact and get custom image
            contact = app._resolve_contact_for_hash(remote_hash)
            custom_image = contact["custom_image"] if contact else None

            active_call = {
                "hash": telephone_active_call.hash.hex(),
                "remote_identity_hash": remote_hash,
                "remote_destination_hash": remote_destination_hash,
                "remote_identity_name": remote_name,
                "remote_icon": dict(remote_icon) if remote_icon else None,
                "custom_image": custom_image,
                "is_incoming": telephone_active_call.is_incoming,
                "status": app.telephone_manager.telephone.call_status,
                "remote_telephony_hash": remote_telephony_hash,
                "audio_profile_id": app.telephone_manager.telephone.transmit_codec.profile
                if hasattr(
                    app.telephone_manager.telephone.transmit_codec,
                    "profile",
                )
                else None,
                "call_mode_id": app.telephone_manager.get_active_mode_id(),
                "is_half_duplex": app.telephone_manager.is_half_duplex(),
                "is_ptt_active": bool(app.telephone_manager.ptt_active),
                "is_transmit_squelched": app.telephone_manager.is_transmit_squelched(),
                "is_mic_muted": app.telephone_manager.transmit_muted,
                "is_speaker_muted": app.telephone_manager.receive_muted,
                "is_recording": app.telephone_manager.is_recording,
                "is_voicemail": app.voicemail_manager.is_recording,
                "call_start_time": app.telephone_manager.call_start_time,
                "is_contact": contact is not None,
                "tx_bytes": 0,
                "rx_bytes": 0,
                "tx_packets": 0,
                "rx_packets": 0,
                "tx_bps": 0,
                "rx_bps": 0,
                "path_hops": None,
                "path_interface": None,
            }
            from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

            mode_id = active_call["call_mode_id"]
            with contextlib.suppress(Exception):
                active_call["call_mode_name"] = lxst_modes.mode_name(mode_id)
                active_call["call_mode_abbrev"] = lxst_modes.mode_abbreviation(mode_id)
            link = getattr(app.telephone_manager, "call_stats", {}).get("link")
            if link:
                active_call["tx_bytes"] = getattr(link, "txbytes", 0)
                active_call["rx_bytes"] = getattr(link, "rxbytes", 0)
                active_call["tx_packets"] = getattr(link, "tx", 0)
                active_call["rx_packets"] = getattr(link, "rx", 0)
                started_at = getattr(app.telephone_manager, "call_stats", {}).get(
                    "started_at",
                )
                if not started_at:
                    started_at = app.telephone_manager.call_start_time
                elapsed = (
                    max(0.001, time.time() - float(started_at)) if started_at else 0.0
                )
                if elapsed > 0:
                    active_call["tx_bps"] = int(
                        (active_call["tx_bytes"] * 8) / elapsed,
                    )
                    active_call["rx_bps"] = int(
                        (active_call["rx_bytes"] * 8) / elapsed,
                    )
                # Best-effort direct link metadata fallback.
                if active_call["path_hops"] is None:
                    for hop_attr in ["hops", "hop_count", "path_hops"]:
                        hops_val = getattr(link, hop_attr, None)
                        if isinstance(hops_val, int):
                            active_call["path_hops"] = hops_val
                            break
                if not active_call["path_interface"]:
                    for iface_attr in ["attached_interface", "interface", "ifac"]:
                        iface_val = getattr(link, iface_attr, None)
                        if isinstance(iface_val, str) and iface_val.strip():
                            active_call["path_interface"] = iface_val.strip()
                            break
                        iface_name = (
                            getattr(iface_val, "name", None) if iface_val else None
                        )
                        if isinstance(iface_name, str) and iface_name.strip():
                            active_call["path_interface"] = iface_name.strip()
                            break

            # Try multiple destination hashes. Depending on LXST state, the
            # active call hash is not always the route-resolvable destination.
            for candidate_hex in [
                remote_telephony_hash,
                remote_hash,
                active_call["hash"],
                remote_destination_hash,
            ]:
                if not candidate_hex:
                    continue
                try:
                    candidate_hash = bytes.fromhex(candidate_hex)
                except Exception:
                    continue
                try:
                    if not RNS.Transport.has_path(candidate_hash):
                        continue
                    active_call["path_hops"] = RNS.Transport.hops_to(candidate_hash)
                    if hasattr(app, "reticulum") and app.reticulum:
                        active_call["path_interface"] = (
                            app.reticulum.get_next_hop_if_name(
                                candidate_hash,
                            )
                        )
                    break
                except Exception:
                    continue

        initiation_target_hash = app.telephone_manager.initiation_target_hash
        initiation_target_name = None
        if initiation_target_hash:
            try:
                contact = app._resolve_contact_for_hash(initiation_target_hash)
                if contact:
                    initiation_target_name = contact["name"]
            except Exception:
                pass

        return web.json_response(
            {
                "enabled": True,
                "is_busy": app.telephone_manager.telephone.busy,
                "call_status": app.telephone_manager.telephone.call_status,
                "active_call": active_call,
                "is_mic_muted": app.telephone_manager.transmit_muted,
                "is_speaker_muted": app.telephone_manager.receive_muted,
                "preferred_call_mode_id": app.telephone_manager.resolve_call_mode_id(
                    app.telephone_manager.preferred_mode_id,
                ),
                "missed_calls_unread_count": app.database.misc.get_unread_notification_count_by_type(
                    "telephone_missed_call",
                ),
                "voicemail": {
                    "is_recording": app.voicemail_manager.is_recording,
                    "unread_count": app.database.voicemails.get_unread_count(),
                    "latest_id": app.database.voicemails.get_latest_voicemail_id(),
                },
                "initiation_status": app.telephone_manager.initiation_status,
                "initiation_target_hash": initiation_target_hash,
                "initiation_target_name": initiation_target_name,
                # Silence web audio during voicemail
                "web_audio": {
                    "enabled": (
                        getattr(
                            app.config.telephone_web_audio_enabled,
                            "get",
                            lambda: False,
                        )()
                        or app.web_audio_required()
                    )
                    and not bool(
                        getattr(app.voicemail_manager, "is_recording", False),
                    ),
                    "required": app.web_audio_required(),
                    "allow_fallback": getattr(
                        app.config.telephone_web_audio_allow_fallback,
                        "get",
                        lambda: True,
                    )()
                    and not app.web_audio_required(),
                    "has_client": bool(
                        getattr(app.web_audio_bridge, "clients", []),
                    ),
                    "frame_ms": getattr(
                        app.telephone_manager.telephone,
                        "target_frame_time_ms",
                        None,
                    ),
                    "diagnostics": app.web_audio_bridge.get_diagnostics()
                    if hasattr(app.web_audio_bridge, "get_diagnostics")
                    else None,
                },
            },
        )

    @routes.post("/api/v1/telephone/missed-calls/mark-viewed")
    async def telephone_missed_calls_mark_viewed(request):
        not_ready = app._require_identity_context_ready()
        if not_ready is not None:
            return not_ready
        await asyncio.to_thread(
            app.database.misc.dismiss_unviewed_notifications,
            "telephone_missed_call",
        )
        return web.json_response({"message": "ok"})

    # answer incoming telephone call

    # answer incoming telephone call
    @routes.post("/api/v1/telephone/answer")
    async def telephone_answer(request):
        # get incoming caller identity
        active_call = app.telephone_manager.telephone.active_call
        if not active_call:
            return web.json_response({"message": "No active call"}, status=404)

        caller_identity = active_call.get_remote_identity()
        if not caller_identity:
            return web.json_response(
                {"message": "Caller identity not found"},
                status=404,
            )

        caller_hash = caller_identity.hash.hex()
        if app.is_destination_blocked(caller_hash):
            app.telephone_manager.request_hangup()
            return web.json_response(
                {"message": "Caller is banished"},
                status=403,
            )

        # answer call
        await asyncio.to_thread(
            app.telephone_manager.telephone.answer,
            caller_identity,
        )

        return web.json_response(
            {
                "message": "Answering call...",
            },
        )

    # hangup active telephone call

    # hangup active telephone call
    @routes.post("/api/v1/telephone/hangup")
    async def telephone_hangup(request):
        app.telephone_manager.request_hangup()

        return web.json_response(
            {
                "message": "Hanging up call...",
            },
        )

    # send active call to voicemail

    # send active call to voicemail
    @routes.post("/api/v1/telephone/send-to-voicemail")
    async def telephone_send_to_voicemail(request):
        active_call = app.telephone_manager.telephone.active_call
        if not active_call:
            return web.json_response({"message": "No active call"}, status=404)

        caller_identity = active_call.get_remote_identity()
        if not caller_identity:
            return web.json_response({"message": "No remote identity"}, status=400)

        if app.is_destination_blocked(caller_identity.hash.hex()):
            app.telephone_manager.request_hangup()
            return web.json_response(
                {"message": "Caller is banished"},
                status=403,
            )

        # trigger voicemail session
        await asyncio.to_thread(
            app.voicemail_manager.start_voicemail_session,
            caller_identity,
        )

        return web.json_response(
            {
                "message": "Call sent to voicemail",
            },
        )

    # mute/unmute transmit

    # mute/unmute transmit
    @routes.post("/api/v1/telephone/mute-transmit")
    async def telephone_mute_transmit(request):
        await asyncio.to_thread(app.telephone_manager.mute_transmit)
        return web.json_response({"message": "Microphone muted"})

    @routes.post("/api/v1/telephone/unmute-transmit")
    async def telephone_unmute_transmit(request):
        await asyncio.to_thread(app.telephone_manager.unmute_transmit)
        return web.json_response({"message": "Microphone unmuted"})

    # mute/unmute receive

    # mute/unmute receive
    @routes.post("/api/v1/telephone/mute-receive")
    async def telephone_mute_receive(request):
        await asyncio.to_thread(app.telephone_manager.mute_receive)
        return web.json_response({"message": "Speaker muted"})

    @routes.post("/api/v1/telephone/unmute-receive")
    async def telephone_unmute_receive(request):
        await asyncio.to_thread(app.telephone_manager.unmute_receive)
        return web.json_response({"message": "Speaker unmuted"})

    @routes.get("/api/v1/telephone/call-modes")
    async def telephone_call_modes(request):
        from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

        half = lxst_modes.mode_half_duplex()
        modes = [
            {
                "id": mode_id,
                "name": lxst_modes.mode_name(mode_id),
                "abbrev": lxst_modes.mode_abbreviation(mode_id),
                "is_half_duplex": mode_id == half,
            }
            for mode_id in lxst_modes.available_modes()
        ]
        return web.json_response(
            {
                "default_call_mode_id": lxst_modes.default_mode(),
                "call_modes": modes,
            },
        )

    @routes.post("/api/v1/telephone/switch-call-mode/{mode_id}")
    async def telephone_switch_call_mode(request):
        mode_id = request.match_info.get("mode_id")
        try:
            if app.telephone_manager.telephone is None:
                return web.json_response(
                    {"message": "Telephone not initialized"},
                    status=400,
                )
            resolved = await asyncio.to_thread(
                app.telephone_manager.apply_preferred_mode,
                int(mode_id),
            )
            app.config.telephone_call_mode_id.set(resolved)
            from meshchatx.src.backend import lxst_profiles_compat as lxst_modes

            return web.json_response(
                {
                    "message": f"Switched to mode {resolved}",
                    "mode_id": resolved,
                    "mode_name": lxst_modes.mode_name(resolved),
                    "is_half_duplex": resolved == lxst_modes.mode_half_duplex(),
                    "is_ptt_active": bool(app.telephone_manager.ptt_active),
                },
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/telephone/ptt")
    async def telephone_ptt(request):
        if app.telephone_manager.telephone is None:
            return web.json_response(
                {"message": "Telephone not initialized"},
                status=400,
            )
        try:
            data = await request.json()
        except Exception:
            data = {}
        active = bool(data.get("active", False)) if isinstance(data, dict) else False
        ok = await asyncio.to_thread(app.telephone_manager.set_ptt_active, active)
        if not ok and active:
            return web.json_response(
                {
                    "message": "PTT requires an established half-duplex call",
                    "is_ptt_active": bool(app.telephone_manager.ptt_active),
                    "is_half_duplex": app.telephone_manager.is_half_duplex(),
                },
                status=400,
            )
        return web.json_response(
            {
                "message": "ok",
                "is_ptt_active": bool(app.telephone_manager.ptt_active),
                "is_half_duplex": app.telephone_manager.is_half_duplex(),
                "is_transmit_squelched": app.telephone_manager.is_transmit_squelched(),
            },
        )

    # get call history

    # switch audio profile
    @routes.post("/api/v1/telephone/switch-audio-profile/{profile_id}")
    async def telephone_switch_audio_profile(request):
        profile_id = request.match_info.get("profile_id")
        try:
            if app.telephone_manager.telephone is None:
                return web.json_response(
                    {"message": "Telephone not initialized"},
                    status=400,
                )

            resolved = await asyncio.to_thread(
                app.telephone_manager.apply_preferred_profile,
                int(profile_id),
            )
            app.config.telephone_audio_profile_id.set(resolved)
            requested = int(profile_id)
            return web.json_response(
                {
                    "message": f"Switched to profile {resolved}",
                    "profile_id": resolved,
                    "requested_profile_id": requested,
                    "remapped": requested != resolved,
                },
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # Codec2 / audio backend readiness (Android packaging + LXST)

    # Codec2 / audio backend readiness (Android packaging + LXST)
    @routes.get("/api/v1/telephone/codec2/status")
    async def telephone_codec2_status(request):
        from meshchatx import android_codec2

        def _status():
            probe_ok, probe_error = android_codec2.probe_pycodec2()
            lxst_ok = app.telephone_manager.codec2_available()
            available = bool(probe_ok and lxst_ok)
            return {
                "codec2_available": available,
                "preload_error": android_codec2.codec2_preload_error(),
                "probe_error": None if probe_ok else probe_error,
                "platform": (
                    "android" if android_codec2._is_chaquopy_android() else "desktop"
                ),
                "preferred_profile_id": app.telephone_manager.preferred_profile_id,
                "resolved_profile_id": app.telephone_manager.resolve_audio_profile_id(),
            }

        payload = await asyncio.to_thread(_status)
        return web.json_response(payload)

    # initiate a telephone call
    # initiate outgoing telephone call

    # initiate a telephone call
    # initiate outgoing telephone call
    @routes.post("/api/v1/telephone/call/{identity_hash}")
    async def telephone_call(request):
        # make sure telephone enabled
        if app.telephone_manager.telephone is None:
            return web.json_response(
                {
                    "message": "Telephone has been disabled.",
                },
                status=503,
            )

        # check if busy, but ignore stale busy when no active call
        is_busy = app.telephone_manager.telephone.busy
        if is_busy and not app.telephone_manager.telephone.active_call:
            # If there's no active call and we're not currently initiating,
            # we shouldn't be busy.
            if not app.telephone_manager.initiation_status:
                is_busy = False

        if is_busy or app.telephone_manager.initiation_status:
            return web.json_response(
                {
                    "message": "Telephone is busy",
                },
                status=400,
            )

        # get path params
        identity_hash_hex = request.match_info.get("identity_hash", "")
        from meshchatx.src.backend.call_timeout import clamp_call_timeout_seconds

        timeout_seconds = clamp_call_timeout_seconds(
            request.query.get("timeout", 15),
        )

        try:
            # convert hash to bytes
            identity_hash_bytes = bytes.fromhex(identity_hash_hex)
        except Exception:
            return web.json_response(
                {
                    "message": "Invalid identity hash",
                },
                status=400,
            )

        if app.is_destination_blocked(identity_hash_hex):
            return web.json_response(
                {
                    "message": "Cannot call a banished identity",
                },
                status=403,
            )

        # initiate call in background to be non-blocking for the UI
        async def _initiate():
            try:
                await app.telephone_manager.initiate(
                    identity_hash_bytes,
                    timeout_seconds=timeout_seconds,
                )
            except Exception as e:
                print(f"Failed to initiate call to {identity_hash_hex}: {e}")

        asyncio.create_task(_initiate())

        return web.json_response(
            {
                "message": "Call initiation started",
            },
        )

    # serve list of available audio profiles

    # serve list of available audio profiles
    @routes.get("/api/v1/telephone/audio-profiles")
    async def telephone_audio_profiles(request):
        from LXST.Primitives.Telephony import Profiles

        from meshchatx import android_codec2

        def _profiles():
            probe_ok, _probe_err = android_codec2.probe_pycodec2()
            codec2_ok = bool(probe_ok and app.telephone_manager.codec2_available())
            codec2_ids = {
                Profiles.BANDWIDTH_ULTRA_LOW,
                Profiles.BANDWIDTH_VERY_LOW,
                Profiles.BANDWIDTH_LOW,
            }
            audio_profiles = []
            for profile_id in Profiles.available_profiles():
                entry = {
                    "id": profile_id,
                    "name": Profiles.profile_name(profile_id),
                    "available": True,
                }
                if profile_id in codec2_ids and not codec2_ok:
                    entry["available"] = False
                    entry["unavailable_reason"] = "codec2"
                audio_profiles.append(entry)
            return {
                "default_audio_profile_id": app.telephone_manager.resolve_audio_profile_id(
                    Profiles.DEFAULT_PROFILE,
                ),
                "codec2_available": codec2_ok,
                "audio_profiles": audio_profiles,
            }

        payload = await asyncio.to_thread(_profiles)
        return web.json_response(payload)

    # voicemail status
