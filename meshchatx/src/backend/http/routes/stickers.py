# SPDX-License-Identifier: 0BSD
"""HTTP routes: stickers."""

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


def register_stickers_routes(routes, app):

    @routes.get("/api/v1/stickers")
    async def stickers_list(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.stickers.list_for_identity(identity_hash)
        return web.json_response({"stickers": [dict(r) for r in rows]})

    @routes.post("/api/v1/stickers")
    async def stickers_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        image_b64 = data.get("image_bytes")
        if not isinstance(image_b64, str) or not image_b64.strip():
            return web.json_response({"error": "missing_image_bytes"}, status=400)
        try:
            raw = base64.b64decode(image_b64.strip(), validate=True)
        except (ValueError, TypeError):
            return web.json_response({"error": "invalid_base64"}, status=400)
        name = sanitize_sticker_name(data.get("name"))
        image_type = data.get("image_type")
        src = data.get("source_message_hash")
        src = src if isinstance(src, str) else None
        emoji = sanitize_sticker_emoji(data.get("emoji"))
        strict = bool(data.get("strict", False))
        pack_id_raw = data.get("pack_id")
        pack_id = None
        if pack_id_raw is not None:
            try:
                pack_id = int(pack_id_raw)
            except (TypeError, ValueError):
                return web.json_response({"error": "invalid_pack_id"}, status=400)
            pack_row = app.database.sticker_packs.get_row(pack_id, identity_hash)
            if pack_row is None:
                return web.json_response({"error": "pack_not_found"}, status=404)
        try:
            row = app.database.stickers.insert(
                identity_hash,
                name,
                image_type,
                raw,
                src,
                pack_id=pack_id,
                emoji=emoji,
                strict=strict,
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        if row is None:
            return web.json_response({"error": "duplicate_sticker"}, status=409)
        return web.json_response({"sticker": row})

    @routes.delete("/api/v1/stickers/{sticker_id}")
    async def stickers_delete(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        ok = app.database.stickers.delete(sticker_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "deleted"})

    @routes.patch("/api/v1/stickers/{sticker_id}")
    async def stickers_patch(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        applied = False
        if "name" in data:
            name = sanitize_sticker_name(data.get("name"))
            if not app.database.stickers.update_name(
                sticker_id,
                identity_hash,
                name,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if "emoji" in data:
            emoji = sanitize_sticker_emoji(data.get("emoji"))
            if not app.database.stickers.update_emoji(
                sticker_id,
                identity_hash,
                emoji,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if "pack_id" in data:
            pid_raw = data.get("pack_id")
            pid = None
            if pid_raw is not None:
                try:
                    pid = int(pid_raw)
                except (TypeError, ValueError):
                    return web.json_response(
                        {"error": "invalid_pack_id"},
                        status=400,
                    )
                if app.database.sticker_packs.get_row(pid, identity_hash) is None:
                    return web.json_response(
                        {"error": "pack_not_found"},
                        status=404,
                    )
            if not app.database.stickers.assign_to_pack(
                sticker_id,
                identity_hash,
                pid,
            ):
                return web.json_response({"error": "not_found"}, status=404)
            applied = True
        if not applied:
            return web.json_response({"error": "nothing_to_update"}, status=400)
        return web.json_response({"message": "updated"})

    @routes.get("/api/v1/stickers/{sticker_id}/image")
    async def stickers_get_image(request):
        identity_hash = app.identity.hash.hex()
        sticker_id = int(request.match_info.get("sticker_id", "0"))
        row = app.database.stickers.get_row(sticker_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        ct = mime_for_image_type(row["image_type"])
        return web.Response(body=row["image_blob"], content_type=ct)

    @routes.get("/api/v1/stickers/export")
    async def stickers_export(request):
        identity_hash = app.identity.hash.hex()
        payloads = app.database.stickers.export_payloads_for_identity(
            identity_hash,
        )
        doc = build_export_document(
            payloads,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/stickers/import")
    async def stickers_import(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        replace = bool(data.get("replace_duplicates", False))
        try:
            items = validate_export_document(data)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        result = app.database.stickers.import_payloads(
            identity_hash,
            items,
            replace_duplicates=replace,
        )
        return web.json_response(result)

    @routes.get("/api/v1/sticker-packs")
    async def sticker_packs_list(request):
        identity_hash = app.identity.hash.hex()
        packs = [
            dict(p)
            for p in app.database.sticker_packs.list_for_identity(
                identity_hash,
            )
        ]
        for p in packs:
            p["sticker_count"] = app.database.stickers.count_for_pack(
                p["id"],
                identity_hash,
            )
            stickers = app.database.stickers.list_for_pack(
                p["id"],
                identity_hash,
            )
            p["stickers"] = [dict(s) for s in stickers]
        return web.json_response({"packs": packs})

    @routes.post("/api/v1/sticker-packs")
    async def sticker_packs_create(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        try:
            pack = app.database.sticker_packs.insert(
                identity_hash,
                data.get("title"),
                short_name=data.get("short_name"),
                description=data.get("description"),
                pack_type=data.get("pack_type"),
                author=data.get("author"),
                is_strict=bool(data.get("is_strict", True)),
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response({"pack": pack})

    @routes.get("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_get(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return web.json_response({"error": "invalid_pack_id"}, status=400)
        row = app.database.sticker_packs.get_row(pack_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        stickers = app.database.stickers.list_for_pack(pack_id, identity_hash)
        return web.json_response(
            {
                "pack": dict(row),
                "stickers": [dict(s) for s in stickers],
            },
        )

    @routes.patch("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_patch(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return web.json_response({"error": "invalid_pack_id"}, status=400)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        kwargs = {}
        for key in ("title", "description", "pack_type"):
            if key in data:
                kwargs[key] = data.get(key)
        if "cover_sticker_id" in data:
            v = data.get("cover_sticker_id")
            kwargs["cover_sticker_id"] = int(v) if v is not None else None
        if not kwargs:
            return web.json_response({"error": "nothing_to_update"}, status=400)
        ok = app.database.sticker_packs.update(
            pack_id,
            identity_hash,
            **kwargs,
        )
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "updated"})

    @routes.post("/api/v1/sticker-packs/reorder")
    async def sticker_packs_reorder(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        ids = data.get("pack_ids")
        if not isinstance(ids, list):
            return web.json_response({"error": "missing_pack_ids"}, status=400)
        try:
            ids_int = [int(x) for x in ids]
        except (TypeError, ValueError):
            return web.json_response({"error": "invalid_pack_ids"}, status=400)
        updated = app.database.sticker_packs.reorder(identity_hash, ids_int)
        return web.json_response({"updated": updated})

    @routes.delete("/api/v1/sticker-packs/{pack_id}")
    async def sticker_packs_delete(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return web.json_response({"error": "invalid_pack_id"}, status=400)
        with_stickers = request.query.get("with_stickers", "false").lower() == "true"
        if with_stickers:
            ok = app.database.sticker_packs.delete_with_stickers(
                pack_id,
                identity_hash,
            )
        else:
            ok = app.database.sticker_packs.delete(pack_id, identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"message": "deleted"})

    @routes.get("/api/v1/sticker-packs/{pack_id}/export")
    async def sticker_packs_export(request):
        identity_hash = app.identity.hash.hex()
        try:
            pack_id = int(request.match_info.get("pack_id", "0"))
        except ValueError:
            return web.json_response({"error": "invalid_pack_id"}, status=400)
        row = app.database.sticker_packs.get_row(pack_id, identity_hash)
        if row is None:
            return web.json_response({"error": "not_found"}, status=404)
        stickers = app.database.stickers.export_payloads_for_pack(
            pack_id,
            identity_hash,
        )
        doc = sticker_pack_utils.build_pack_document(
            dict(row),
            stickers,
            datetime.now(UTC).isoformat(),
        )
        return web.json_response(doc)

    @routes.post("/api/v1/sticker-packs/install")
    async def sticker_packs_install(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        replace = bool(data.get("replace_duplicates", False))
        try:
            parsed = sticker_pack_utils.validate_pack_document(data)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        try:
            pack_row = app.database.sticker_packs.insert(
                identity_hash,
                parsed["pack"]["title"],
                short_name=parsed["pack"]["short_name"],
                description=parsed["pack"]["description"],
                pack_type=parsed["pack"]["pack_type"],
                author=parsed["pack"]["author"],
                is_strict=parsed["pack"]["is_strict"],
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        result = app.database.stickers.import_payloads(
            identity_hash,
            parsed["stickers"],
            replace_duplicates=replace,
            pack_id=pack_row["id"],
            strict=parsed["pack"]["is_strict"],
        )
        return web.json_response({"pack": pack_row, **result})
