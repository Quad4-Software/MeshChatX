# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone."""

from __future__ import annotations


from meshchatx.src.backend.http.meshchat_names import (  # noqa: F401
    GeoValidationError,
    OutboundHttpBlockedError,
    OverlayExportError,
    OverlaySourceParseError,
    PluginSecurityError,
    AsyncUtils,
    InterfaceConfigParser,
    InterfaceDiscovery,
    InterfaceEditor,
    LOGIN_PATH,
    LXMF,
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
    MAX_EXPORT_TILES,
    MarkdownRenderer,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    RNProbeHandler,
    RNS,
    ReticulumMeshChat,
    SETUP_PATH,
    TRANSPARENT_TILE,
    Telemeter,
    UTC,
    WSMsgType,
    _is_chaquopy_android,
    _is_loopback_bind_host,
    _request_client_ip,
    aiohttp,
    app_version,
    assert_migration_context_paths,
    asyncio,
    base64,
    bcrypt,
    binascii,
    build_blocklist_export_document,
    build_export_document,
    build_messages_export_bundle,
    cache_stats,
    cancel_inbound_deliveries,
    cast,
    compute_lxmf_conversation_unread_from_latest_row,
    configparser,
    contextlib,
    convert_db_favourite_to_dict,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
    convert_propagation_node_state_to_string,
    copy,
    datetime,
    describe_port_conflict,
    detect_image_format_from_magic,
    ensure_outbound_http_allowed,
    ensure_session_csrf_token,
    filter_announced_dicts_by_search_query,
    fresh_storage_at_target,
    get_cached_active_link,
    get_file_path,
    get_session,
    get_trusted_proxy_cidrs,
    gif_utils,
    i2p_support,
    import_messages_export_bundle,
    io,
    is_mbtiles_filename,
    is_path_within_dir,
    is_port_in_use,
    is_user_facing_lxmf_payload,
    json,
    list_host_network_interfaces,
    list_inbound_deliveries,
    list_ports,
    load_app_security_settings,
    logger,
    logging,
    lxmf_sidebar_preview_for_conversation_latest_row,
    memory_log_handler,
    message_fields_have_attachments,
    migrate_legacy_to_target,
    mime_for_image_type,
    normalize_identity_storage_hash,
    normalize_lxmf_sieve_filters,
    normalize_message_blocklist,
    os,
    parse_bool_query_param,
    parse_import_document,
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_sieve_filters_json,
    parse_lxmf_stamp_cost,
    parse_message_blocklist_json,
    parse_nomadnetwork_node_display_name,
    platform,
    privacy_mode_enabled,
    psutil,
    purge_messages_before_cutoff,
    re,
    resolve_message_age_cutoff,
    reticulum_pathfinding,
    rotate_session_csrf_token,
    rrc_protocol,
    safe_path_under_dir,
    sanitize_sticker_emoji,
    sanitize_sticker_name,
    sanitize_websocket_config_update,
    save_app_security_settings,
    secrets,
    shutil,
    sqlite3,
    sticker_pack_utils,
    sys,
    tempfile,
    threading,
    time,
    traceback,
    user_agent_hash,
    validate_export_document,
    web,
    websocket_type_requires_auth,
    zipfile,
)


def register_telephone_routes(routes, app):

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
            # Filter out incoming calls if DND or contacts-only is active and call is ringing
            is_ringing = app.telephone_manager.telephone.call_status == 4
            if telephone_active_call.is_incoming and is_ringing:
                if app.config.do_not_disturb_enabled.get():
                    # Don't report active call if DND is on and it's ringing
                    telephone_active_call = None
                elif (
                    app.config.telephone_allow_calls_from_contacts_only.get()
                    or app.config.block_all_from_strangers.get()
                ):
                    remote_identity = telephone_active_call.get_remote_identity()
                    if remote_identity:
                        caller_hash = remote_identity.hash.hex()
                        if not app._is_contact(caller_hash):
                            # Don't report active call if contacts-only is on and caller is not a contact
                            telephone_active_call = None
                    else:
                        # Don't report active call if we cannot identify the caller
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
            from LXST.Primitives.Telephony import Profiles

            mode_id = active_call["call_mode_id"]
            with contextlib.suppress(Exception):
                active_call["call_mode_name"] = Profiles.mode_name(mode_id)
                active_call["call_mode_abbrev"] = Profiles.mode_abbrevation(mode_id)
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
        from LXST.Primitives.Telephony import Profiles

        modes = [
            {
                "id": mode_id,
                "name": Profiles.mode_name(mode_id),
                "abbrev": Profiles.mode_abbrevation(mode_id),
                "is_half_duplex": mode_id == Profiles.MODE_HALF_DUPLEX,
            }
            for mode_id in Profiles.available_modes()
        ]
        return web.json_response(
            {
                "default_call_mode_id": Profiles.DEFAULT_MODE,
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
            from LXST.Primitives.Telephony import Profiles

            return web.json_response(
                {
                    "message": f"Switched to mode {resolved}",
                    "mode_id": resolved,
                    "mode_name": Profiles.mode_name(resolved),
                    "is_half_duplex": resolved == Profiles.MODE_HALF_DUPLEX,
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

    # get call history
    @routes.get("/api/v1/telephone/history")
    async def telephone_history(request):
        limit = int(request.query.get("limit", 10))
        offset = int(request.query.get("offset", 0))
        search = request.query.get("search", None)
        history = app.database.telephone.get_call_history(
            search=search,
            limit=limit,
            offset=offset,
        )

        call_history = []
        for row in history:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
                # try to resolve name if unknown or missing
                if (
                    not d.get("remote_identity_name")
                    or d.get("remote_identity_name") == "Unknown"
                ):
                    resolved_name = app.get_name_for_identity_hash(
                        remote_identity_hash,
                    )
                    if resolved_name:
                        d["remote_identity_name"] = resolved_name

                lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
                tele_hash = app.get_lxst_telephony_hash_for_identity_hash(
                    remote_identity_hash,
                )
                if lxmf_hash:
                    d["remote_destination_hash"] = lxmf_hash
                    icon = app.database.misc.get_user_icon(lxmf_hash)
                    if icon:
                        d["remote_icon"] = dict(icon)
                if tele_hash:
                    d["remote_telephony_hash"] = tele_hash

                contact = app._resolve_contact_for_hash(remote_identity_hash)
                d["is_contact"] = contact is not None
                if contact:
                    d["contact_image"] = contact.get("custom_image")
            call_history.append(d)

        return web.json_response(
            {
                "call_history": call_history,
            },
        )

    # clear call history

    # clear call history
    @routes.delete("/api/v1/telephone/history")
    async def telephone_history_clear(request):
        app.database.telephone.clear_call_history()
        return web.json_response({"message": "ok"})

    # switch audio profile

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

    # voicemail status
    @routes.get("/api/v1/telephone/voicemail/status")
    async def telephone_voicemail_status(request):
        greeting_path = os.path.join(
            app.voicemail_manager.greetings_dir,
            "greeting.opus",
        )
        return web.json_response(
            {
                "has_espeak": app.voicemail_manager.has_espeak,
                "is_recording": app.voicemail_manager.is_recording,
                "is_greeting_recording": app.voicemail_manager.is_greeting_recording,
                "has_greeting": os.path.exists(greeting_path),
            },
        )

    # start recording greeting from mic

    # start recording greeting from mic
    @routes.post("/api/v1/telephone/voicemail/greeting/record/start")
    async def telephone_voicemail_greeting_record_start(request):
        app.voicemail_manager.start_greeting_recording()
        return web.json_response({"message": "Started recording greeting"})

    # stop recording greeting from mic

    # stop recording greeting from mic
    @routes.post("/api/v1/telephone/voicemail/greeting/record/stop")
    async def telephone_voicemail_greeting_record_stop(request):
        app.voicemail_manager.stop_greeting_recording()
        return web.json_response({"message": "Stopped recording greeting"})

    # list voicemails

    # list voicemails
    @routes.get("/api/v1/telephone/voicemails")
    async def telephone_voicemails(request):
        search = request.query.get("search")
        limit = int(request.query.get("limit", 50))
        offset = int(request.query.get("offset", 0))
        voicemails_rows = app.database.voicemails.get_voicemails(
            search=search,
            limit=limit,
            offset=offset,
        )

        voicemails = []
        for row in voicemails_rows:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
                lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
                tele_hash = app.get_lxst_telephony_hash_for_identity_hash(
                    remote_identity_hash,
                )
                if lxmf_hash:
                    d["remote_destination_hash"] = lxmf_hash
                    icon = app.database.misc.get_user_icon(lxmf_hash)
                    if icon:
                        d["remote_icon"] = dict(icon)
                if tele_hash:
                    d["remote_telephony_hash"] = tele_hash
            voicemails.append(d)

        return web.json_response(
            {
                "voicemails": voicemails,
                "unread_count": app.database.voicemails.get_unread_count(),
            },
        )

    # mark voicemail as read

    # mark voicemail as read
    @routes.post("/api/v1/telephone/voicemails/{id}/read")
    async def telephone_voicemail_mark_read(request):
        voicemail_id = request.match_info.get("id")
        app.database.voicemails.mark_as_read(voicemail_id)
        return web.json_response({"message": "Voicemail marked as read"})

    # delete voicemail

    # delete voicemail
    @routes.delete("/api/v1/telephone/voicemails/{id}")
    async def telephone_voicemail_delete(request):
        voicemail_id = request.match_info.get("id")
        voicemail = app.database.voicemails.get_voicemail(voicemail_id)
        if voicemail:
            filepath = safe_path_under_dir(
                app.voicemail_manager.recordings_dir,
                voicemail["filename"],
            )
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            app.database.voicemails.delete_voicemail(voicemail_id)
            return web.json_response({"message": "Voicemail deleted"})
        return web.json_response({"message": "Voicemail not found"}, status=404)

    # serve greeting audio

    # serve greeting audio
    @routes.get("/api/v1/telephone/voicemail/greeting/audio")
    async def telephone_voicemail_greeting_audio(request):
        filepath = os.path.join(
            app.voicemail_manager.greetings_dir,
            "greeting.opus",
        )
        if os.path.exists(filepath):
            return web.FileResponse(
                filepath,
                headers={"Content-Type": "audio/opus"},
            )
        return web.json_response(
            {"message": "Greeting audio not found"},
            status=404,
        )

    # serve voicemail audio

    # serve voicemail audio
    @routes.get("/api/v1/telephone/voicemails/{id}/audio")
    async def telephone_voicemail_audio(request):
        voicemail_id = request.match_info.get("id")
        try:
            voicemail_id = int(voicemail_id)
        except (ValueError, TypeError):
            return web.json_response(
                {"message": "Invalid voicemail ID"},
                status=400,
            )

        if not app.voicemail_manager:
            return web.json_response(
                {"message": "Voicemail manager not available"},
                status=503,
            )

        voicemail = app.database.voicemails.get_voicemail(voicemail_id)
        if voicemail:
            filepath = safe_path_under_dir(
                app.voicemail_manager.recordings_dir,
                voicemail["filename"],
            )
            if filepath and os.path.exists(filepath):
                # Browsers might need a proper content type for .opus files
                return web.FileResponse(
                    filepath,
                    headers={"Content-Type": "audio/opus"},
                )
            RNS.log(
                f"Voicemail: Recording file missing for ID {voicemail_id}: {filepath}",
                RNS.LOG_ERROR,
            )
        return web.json_response(
            {"message": "Voicemail audio not found"},
            status=404,
        )

    # list call recordings

    # list call recordings
    @routes.get("/api/v1/telephone/recordings")
    async def telephone_recordings(request):
        search = request.query.get("search", None)
        limit = int(request.query.get("limit", 10))
        offset = int(request.query.get("offset", 0))
        recordings_rows = app.database.telephone.get_call_recordings(
            search=search,
            limit=limit,
            offset=offset,
        )
        recordings = []
        for row in recordings_rows:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
                lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
                if lxmf_hash:
                    icon = app.database.misc.get_user_icon(lxmf_hash)
                    if icon:
                        d["remote_icon"] = dict(icon)
            recordings.append(d)

        return web.json_response({"recordings": recordings})

    # serve call recording audio

    # serve call recording audio
    @routes.get("/api/v1/telephone/recordings/{id}/audio/{side}")
    async def telephone_recording_audio(request):
        recording_id = request.match_info.get("id")
        try:
            recording_id = int(recording_id)
        except (ValueError, TypeError):
            return web.json_response(
                {"message": "Invalid recording ID"},
                status=400,
            )

        side = request.match_info.get("side")  # rx or tx
        recording = app.database.telephone.get_call_recording(recording_id)
        if recording:
            filename = recording[f"filename_{side}"]
            if not filename:
                return web.json_response(
                    {"message": f"No {side} recording found"},
                    status=404,
                )

            filepath = safe_path_under_dir(
                app.telephone_manager.recordings_dir,
                filename,
            )
            if filepath and os.path.exists(filepath):
                return web.FileResponse(
                    filepath,
                    headers={"Content-Type": "audio/opus"},
                )

        return web.json_response({"message": "Recording not found"}, status=404)

    # delete call recording

    # delete call recording
    @routes.delete("/api/v1/telephone/recordings/{id}")
    async def telephone_recording_delete(request):
        recording_id = request.match_info.get("id")
        recording = app.database.telephone.get_call_recording(recording_id)
        if recording:
            for side in ["rx", "tx"]:
                filename = recording[f"filename_{side}"]
                if filename:
                    filepath = safe_path_under_dir(
                        app.telephone_manager.recordings_dir,
                        filename,
                    )
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
            app.database.telephone.delete_call_recording(recording_id)
        return web.json_response({"message": "ok"})

    # generate greeting

    # generate greeting
    @routes.post("/api/v1/telephone/voicemail/generate-greeting")
    async def telephone_voicemail_generate_greeting(request):
        try:
            text = app.config.voicemail_greeting.get()
            path = await asyncio.to_thread(
                app.voicemail_manager.generate_greeting,
                text,
            )
            return web.json_response(
                {"message": "Greeting generated", "path": path},
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # upload greeting

    # upload greeting
    @routes.post("/api/v1/telephone/voicemail/greeting/upload")
    async def telephone_voicemail_greeting_upload(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response(
                    {"message": "File field required"},
                    status=400,
                )

            filename = field.filename
            extension = os.path.splitext(filename)[1].lower()
            if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                return web.json_response(
                    {"message": f"Unsupported file type: {extension}"},
                    status=400,
                )

            # Save temp file
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                temp_path = f.name
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            try:
                # Convert to greeting
                path = await asyncio.to_thread(
                    app.voicemail_manager.convert_to_greeting,
                    temp_path,
                )
                return web.json_response(
                    {"message": "Greeting uploaded and converted", "path": path},
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # delete greeting

    # delete greeting
    @routes.delete("/api/v1/telephone/voicemail/greeting")
    async def telephone_voicemail_greeting_delete(request):
        try:
            app.voicemail_manager.remove_greeting()
            return web.json_response({"message": "Greeting deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # ringtone routes

    # ringtone routes
    @routes.get("/api/v1/telephone/ringtones")
    async def telephone_ringtones_get(request):
        ringtones = app.database.ringtones.get_all()
        return web.json_response(
            [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "display_name": r["display_name"],
                    "is_primary": bool(r["is_primary"]),
                    "created_at": r["created_at"],
                }
                for r in ringtones
            ],
        )

    @routes.get("/api/v1/telephone/ringtones/status")
    async def telephone_ringtone_status(request):
        try:
            caller_hash = request.query.get("caller_hash")

            ringtone_id = None

            # 1. check contact preferred ringtone
            if caller_hash:
                contact = app.database.contacts.get_contact_by_identity_hash(
                    caller_hash,
                )
                if contact and contact.get("preferred_ringtone_id"):
                    ringtone_id = contact["preferred_ringtone_id"]

            # 2. check global preferred for non-contacts
            if ringtone_id is None:
                preferred_id = app.config.ringtone_preferred_id.get()
                if preferred_id:
                    ringtone_id = preferred_id

            # 3. fallback to primary
            if ringtone_id is None:
                primary = app.database.ringtones.get_primary()
                if primary:
                    ringtone_id = primary["id"]

            # 4. handle random if selected (-1)
            if ringtone_id == -1:
                import random

                ringtones = app.database.ringtones.get_all()
                if ringtones:
                    ringtone_id = random.choice(ringtones)["id"]
                else:
                    ringtone_id = None

            has_custom = ringtone_id is not None
            ringtone = (
                app.database.ringtones.get_by_id(ringtone_id) if has_custom else None
            )

            return web.json_response(
                {
                    "has_custom_ringtone": has_custom and ringtone is not None,
                    "enabled": app.config.custom_ringtone_enabled.get(),
                    "filename": ringtone["filename"] if ringtone else None,
                    "id": ringtone_id if ringtone_id != -1 else None,
                    "volume": app.config.ringtone_volume.get() / 100.0,
                },
            )
        except Exception as e:
            logger.error(f"Error in telephone_ringtone_status: {e}")
            return web.json_response(
                {
                    "has_custom_ringtone": False,
                    "enabled": app.config.custom_ringtone_enabled.get(),
                    "filename": None,
                    "id": None,
                    "volume": app.config.ringtone_volume.get() / 100.0,
                },
            )

    @routes.get("/api/v1/telephone/ringtones/{id}/audio")
    async def telephone_ringtone_audio(request):
        ringtone_id = int(request.match_info["id"])
        ringtone = app.database.ringtones.get_by_id(ringtone_id)
        if not ringtone:
            return web.json_response({"message": "Ringtone not found"}, status=404)

        download = request.query.get("download") == "1"

        filepath = app.ringtone_manager.get_ringtone_path(
            ringtone["storage_filename"],
        )
        if filepath and os.path.exists(filepath):
            if download:
                safe_name = os.path.basename(
                    str(ringtone.get("filename") or "ringtone.opus"),
                )
                safe_name = (
                    safe_name.replace('"', "").replace("\r", "").replace("\n", "")
                    or "ringtone.opus"
                )
                return web.FileResponse(
                    filepath,
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_name}"',
                    },
                )
            return web.FileResponse(filepath)
        return web.json_response(
            {"message": "Ringtone audio file not found"},
            status=404,
        )

    @routes.post("/api/v1/telephone/ringtones/upload")
    async def telephone_ringtone_upload(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response(
                    {"message": "File field required"},
                    status=400,
                )

            filename = field.filename
            extension = os.path.splitext(filename)[1].lower()
            if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                return web.json_response(
                    {"message": f"Unsupported file type: {extension}"},
                    status=400,
                )

            # Save temp file
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                temp_path = f.name
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            try:
                # Convert to ringtone
                storage_filename = await asyncio.to_thread(
                    app.ringtone_manager.convert_to_ringtone,
                    temp_path,
                )

                # Add to database
                ringtone_id = app.database.ringtones.add(
                    filename=filename,
                    storage_filename=storage_filename,
                )

                return web.json_response(
                    {
                        "message": "Ringtone uploaded and converted",
                        "id": ringtone_id,
                        "filename": filename,
                        "storage_filename": storage_filename,
                    },
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/telephone/ringtones/{id}")
    async def telephone_ringtone_patch(request):
        try:
            ringtone_id = int(request.match_info["id"])
            data = await request.json()

            display_name = data.get("display_name")
            is_primary = 1 if data.get("is_primary") else None

            app.database.ringtones.update(
                ringtone_id,
                display_name=display_name,
                is_primary=is_primary,
            )

            return web.json_response({"message": "Ringtone updated"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.delete("/api/v1/telephone/ringtones/{id}")
    async def telephone_ringtone_delete(request):
        try:
            ringtone_id = int(request.match_info["id"])
            ringtone = app.database.ringtones.get_by_id(ringtone_id)
            if ringtone:
                app.ringtone_manager.remove_ringtone(ringtone["storage_filename"])
                app.database.ringtones.delete(ringtone_id)
            return web.json_response({"message": "Ringtone deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # notification sound routes

    # notification sound routes
    @routes.get("/api/v1/notification-sounds")
    async def notification_sounds_get(request):
        sounds = app.database.notification_sounds.get_all()
        return web.json_response(
            [
                {
                    "id": s["id"],
                    "filename": s["filename"],
                    "display_name": s["display_name"],
                    "is_primary": bool(s["is_primary"]),
                    "created_at": s["created_at"],
                }
                for s in sounds
            ],
        )

    @routes.get("/api/v1/notification-sounds/status")
    async def notification_sound_status(request):
        try:
            sound_id = None

            preferred_id = app.config.notification_sound_preferred_id.get()
            if preferred_id and preferred_id > 0:
                sound_id = preferred_id

            if sound_id is None:
                primary = app.database.notification_sounds.get_primary()
                if primary:
                    sound_id = primary["id"]

            has_sound = sound_id is not None
            sound = (
                app.database.notification_sounds.get_by_id(sound_id)
                if sound_id
                else None
            )

            return web.json_response(
                {
                    "has_sound": has_sound and sound is not None,
                    "enabled": app.config.notification_sound_enabled.get(),
                    "filename": sound["filename"] if sound else None,
                    "id": sound_id,
                    "volume": app.config.notification_sound_volume.get() / 100.0,
                },
            )
        except Exception as e:
            logger.error(f"Error in notification_sound_status: {e}")
            return web.json_response(
                {
                    "has_sound": False,
                    "enabled": app.config.notification_sound_enabled.get(),
                    "filename": None,
                    "id": None,
                    "volume": app.config.notification_sound_volume.get() / 100.0,
                },
            )

    @routes.get("/api/v1/notification-sounds/{id}/audio")
    async def notification_sound_audio(request):
        sound_id = int(request.match_info["id"])
        sound = app.database.notification_sounds.get_by_id(sound_id)
        if not sound:
            return web.Response(status=404)

        if not app.notification_sound_manager:
            return web.Response(status=503)

        filepath = app.notification_sound_manager.get_ringtone_path(
            sound["storage_filename"],
        )
        if not filepath or not os.path.exists(filepath):
            return web.Response(status=404)

        safe_name = os.path.basename(str(sound.get("filename") or "sound.opus"))
        safe_name = (
            safe_name.replace('"', "").replace("\r", "").replace("\n", "")
            or "sound.opus"
        )
        return web.FileResponse(
            filepath,
            headers={
                "Content-Type": "audio/ogg",
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )

    @routes.post("/api/v1/notification-sounds/upload")
    async def notification_sound_upload(request):
        if not app.notification_sound_manager:
            return web.json_response(
                {"message": "Notification sound manager unavailable"},
                status=503,
            )
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return web.json_response(
                    {"message": "File field required"},
                    status=400,
                )

            filename = field.filename
            extension = os.path.splitext(filename)[1].lower()
            if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                return web.json_response(
                    {"message": f"Unsupported file type: {extension}"},
                    status=400,
                )

            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                temp_path = f.name
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            try:
                storage_filename = await asyncio.to_thread(
                    app.notification_sound_manager.convert_to_ringtone,
                    temp_path,
                )

                sound_id = app.database.notification_sounds.add(
                    filename=filename,
                    storage_filename=storage_filename,
                )

                return web.json_response(
                    {
                        "message": "Notification sound uploaded and converted",
                        "id": sound_id,
                        "filename": filename,
                        "storage_filename": storage_filename,
                    },
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/notification-sounds/{id}")
    async def notification_sound_patch(request):
        try:
            sound_id = int(request.match_info["id"])
            data = await request.json()

            display_name = data.get("display_name")
            is_primary = 1 if data.get("is_primary") else None

            app.database.notification_sounds.update(
                sound_id,
                display_name=display_name,
                is_primary=is_primary,
            )

            return web.json_response({"message": "Notification sound updated"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.delete("/api/v1/notification-sounds/{id}")
    async def notification_sound_delete(request):
        try:
            sound_id = int(request.match_info["id"])
            sound = app.database.notification_sounds.get_by_id(sound_id)
            if sound:
                if app.notification_sound_manager:
                    app.notification_sound_manager.remove_ringtone(
                        sound["storage_filename"],
                    )
                app.database.notification_sounds.delete(sound_id)
            return web.json_response({"message": "Notification sound deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # contacts routes
