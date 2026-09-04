# SPDX-License-Identifier: 0BSD
"""HTTP routes: contacts."""

from __future__ import annotations

from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.errors import http_bad_request
from meshchatx.src.backend.http.meshchat_names import (  # noqa: F401
    LOGIN_PATH,
    LXMF,
    MAX_EXPORT_TILES,
    RNS,
    SETUP_PATH,
    TRANSPARENT_TILE,
    UTC,
    AsyncUtils,
    GeoValidationError,
    InterfaceConfigParser,
    InterfaceDiscovery,
    InterfaceEditor,
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
    MarkdownRenderer,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    OutboundHttpBlockedError,
    OverlayExportError,
    OverlaySourceParseError,
    PluginSecurityError,
    ReticulumMeshChat,
    RNProbeHandler,
    Telemeter,
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

CONTACTS_DEFAULT_LIMIT = 100
CONTACTS_MAX_LIMIT = 500


def parse_contacts_pagination(query, default_limit=CONTACTS_DEFAULT_LIMIT):
    """Parse limit/offset from a MultiDict-like query.

    Returns (limit, offset) with limit clamped to [1, CONTACTS_MAX_LIMIT]
    and offset >= 0. Returns None when limit or offset is not an integer.
    """
    try:
        limit = int(query.get("limit", default_limit))
        offset = int(query.get("offset", 0))
    except (TypeError, ValueError):
        return None
    if limit < 1:
        limit = 1
    elif limit > CONTACTS_MAX_LIMIT:
        limit = CONTACTS_MAX_LIMIT
    if offset < 0:
        offset = 0
    return limit, offset


def enrich_contact_row(app, row):
    """Copy a contacts DAO row and attach LXMF/LXST hashes plus icon when known.

    Enrichment failures for one peer must not fail the whole list.
    """
    d = dict(row)
    remote_identity_hash = d.get("remote_identity_hash")
    if not remote_identity_hash:
        return d
    try:
        lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
            remote_identity_hash,
        )
        tele_hash = app.get_lxst_telephony_hash_for_identity_hash(
            remote_identity_hash,
        )
        if lxmf_hash:
            d["remote_destination_hash"] = lxmf_hash
            try:
                icon = app.database.misc.get_user_icon(lxmf_hash)
            except Exception:
                icon = None
            if icon:
                d["remote_icon"] = dict(icon)
        if tele_hash:
            d["remote_telephony_hash"] = tele_hash
    except Exception:
        logger.debug(
            "Contact enrichment skipped for %s",
            remote_identity_hash,
            exc_info=True,
        )
    return d


def register_contacts_routes(routes, app):
    # contacts routes
    @routes.get("/api/v1/telephone/contacts")
    async def telephone_contacts_get(request):
        pagination = parse_contacts_pagination(request.query)
        if pagination is None:
            return http_bad_request("limit and offset must be integers")
        limit, offset = pagination
        search = request.query.get("search")

        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable

        try:
            contacts_rows = app.database.contacts.get_contacts(
                search=search,
                limit=limit,
                offset=offset,
            )
            total_count = app.database.contacts.get_contacts_count(search=search)
            contacts = [enrich_contact_row(app, row) for row in contacts_rows]
            return web.json_response(
                {"contacts": contacts, "total_count": total_count},
            )
        except Exception as e:
            logger.exception("telephone_contacts_get failed")
            return http_for_database_exception(e)

    @routes.post("/api/v1/telephone/contacts")
    async def telephone_contacts_post(request):
        data = await request.json()
        name = data.get("name")
        remote_identity_hash = data.get("remote_identity_hash")
        lxmf_address = data.get("lxmf_address")
        lxst_address = data.get("lxst_address")
        preferred_ringtone_id = data.get("preferred_ringtone_id")
        custom_image = data.get("custom_image")
        is_telemetry_trusted = data.get("is_telemetry_trusted", 0)

        if not name:
            return web.json_response(
                {"message": "Name is required"},
                status=400,
            )

        # Normalize: chat UI often posts an LXMF destination hash as
        # remote_identity_hash. Prefer the real identity hash when known so
        # incoming-call policy (identity hash) matches saved contacts.
        provided_hash = remote_identity_hash
        lookup_hash = remote_identity_hash or lxmf_address or lxst_address
        if lookup_hash:
            announce = app.database.announces.get_announce_by_hash(lookup_hash)
            if announce and announce.get("identity_hash"):
                remote_identity_hash = announce.get("identity_hash")
                if not lxmf_address and announce.get("aspect") == "lxmf.delivery":
                    lxmf_address = announce.get("destination_hash") or lookup_hash
                if not lxst_address and announce.get("aspect") == "lxst.telephony":
                    lxst_address = announce.get("destination_hash") or lookup_hash
            else:
                ident = app.recall_identity(lookup_hash)
                if ident:
                    remote_identity_hash = ident.hash.hex()

        if not remote_identity_hash:
            remote_identity_hash = lxmf_address or lxst_address or provided_hash
        if not remote_identity_hash:
            return web.json_response(
                {"message": "Identity hash is required or could not be derived"},
                status=400,
            )

        # If the client only supplied a destination hash, keep it on the
        # matching address field so lookups by either form succeed.
        if provided_hash and provided_hash != remote_identity_hash:
            if not lxmf_address:
                lxmf_announce = app.database.announces.get_announce_by_hash(
                    provided_hash,
                )
                if lxmf_announce and lxmf_announce.get("aspect") == "lxmf.delivery":
                    lxmf_address = provided_hash
                elif not lxst_address:
                    lxst_announce = app.database.announces.get_announce_by_hash(
                        provided_hash,
                    )
                    if (
                        lxst_announce
                        and lxst_announce.get("aspect") == "lxst.telephony"
                    ):
                        lxst_address = provided_hash
                    else:
                        # Default: treat unknown destination-shaped hashes as LXMF
                        lxmf_address = lxmf_address or provided_hash

        if not lxmf_address:
            try:
                lxmf_address = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
            except Exception:
                pass
        if not lxst_address:
            try:
                lxst_address = app.get_lxst_telephony_hash_for_identity_hash(
                    remote_identity_hash,
                )
            except Exception:
                pass

        app.database.contacts.add_contact(
            name,
            remote_identity_hash,
            lxmf_address=lxmf_address,
            lxst_address=lxst_address,
            preferred_ringtone_id=preferred_ringtone_id,
            custom_image=custom_image,
            is_telemetry_trusted=is_telemetry_trusted,
        )
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact added"})

    @routes.patch("/api/v1/telephone/contacts/{id}")
    async def telephone_contacts_patch(request):
        contact_id = int(request.match_info["id"])
        data = await request.json()
        name = data.get("name")
        remote_identity_hash = data.get("remote_identity_hash")
        lxmf_address = data.get("lxmf_address")
        lxst_address = data.get("lxst_address")
        preferred_ringtone_id = data.get("preferred_ringtone_id")
        custom_image = data.get("custom_image")
        clear_image = data.get("clear_image", False)
        is_telemetry_trusted = data.get("is_telemetry_trusted")

        app.database.contacts.update_contact(
            contact_id,
            name=name,
            remote_identity_hash=remote_identity_hash,
            lxmf_address=lxmf_address,
            lxst_address=lxst_address,
            preferred_ringtone_id=preferred_ringtone_id,
            custom_image=custom_image,
            clear_image=clear_image,
            is_telemetry_trusted=is_telemetry_trusted,
        )
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact updated"})

    @routes.delete("/api/v1/telephone/contacts/{id}")
    async def telephone_contacts_delete(request):
        contact_id = int(request.match_info["id"])
        app.database.contacts.delete_contact(contact_id)
        app.sync_telephone_call_policy()
        return web.json_response({"message": "Contact deleted"})

    @routes.get("/api/v1/telephone/contacts/check/{identity_hash}")
    async def telephone_contacts_check(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        identity_hash = request.match_info["identity_hash"]
        try:
            contact = app._resolve_contact_for_hash(identity_hash)
            return web.json_response(
                {
                    "is_contact": contact is not None,
                    "contact": dict(contact) if contact else None,
                },
            )
        except Exception as e:
            logger.exception("telephone_contacts_check failed")
            return http_for_database_exception(e)

    @routes.get("/api/v1/telephone/contacts/export")
    async def telephone_contacts_export(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            rows = app.database.contacts.get_contacts(limit=10000, offset=0)
            hashes = [
                r["remote_identity_hash"] for r in rows if r.get("remote_identity_hash")
            ]
            icons = {}
            if hashes:
                icon_rows = app.database.misc.get_user_icons(hashes)
                for ir in icon_rows:
                    icons[ir["destination_hash"]] = dict(ir)
            export_data = []
            for row in rows:
                d = dict(row)
                d.pop("id", None)
                h = d.get("remote_identity_hash")
                if h and h in icons:
                    d["lxmf_icon"] = icons[h]
                export_data.append(d)
            return web.json_response({"contacts": export_data})
        except Exception as e:
            retryable = http_for_database_exception(e)
            if retryable.status == 503:
                return retryable
            return web.json_response(
                {"message": f"Failed to export contacts: {e!s}"},
                status=500,
            )

    @routes.post("/api/v1/telephone/contacts/import")
    async def telephone_contacts_import(request):
        try:
            data = await request.json()
            contacts = data.get("contacts", [])
            if not isinstance(contacts, list):
                return web.json_response(
                    {"message": "Invalid import format: contacts must be an array"},
                    status=400,
                )
            from meshchatx.src.backend.message_export_bundle import import_contacts_list

            added, skipped = import_contacts_list(app.database, contacts)
            app.sync_telephone_call_policy()
            return web.json_response(
                {"message": "Import complete", "added": added, "skipped": skipped},
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to import contacts: {e!s}"},
                status=500,
            )

    # announce
