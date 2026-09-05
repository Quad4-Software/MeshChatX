# SPDX-License-Identifier: 0BSD

"""Shared imports for websocket_upgrade HTTP route slices."""

from __future__ import annotations

# ruff: noqa: F401

from __future__ import annotations

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
from meshchatx.src.backend.path_utils import path_response_window

from meshchatx.src.backend.websocket_config_guard import websocket_origin_allowed
from meshchatx.src.backend.websocket_runtime import (
    WS_RATE_ABUSE_STRIKES,
    WS_RATE_RETRY_AFTER_SEC,
    client_is_idle,
    get_client_bucket,
    init_client_runtime,
    message_rate_cost,
    send_ws_error,
    touch_client_activity,
    websocket_origin_policy_allows,
)


async def _reject_forbidden_ws_session(app, request):
    """Defense in depth: identity-bound session when password auth is on."""
    if not getattr(app, "auth_enabled", False):
        return None
    try:
        session = await get_session(request)
    except Exception:
        return web.json_response({"error": "Authentication required"}, status=401)
    identity_hash = None
    identity = getattr(app, "identity", None)
    if identity is not None and getattr(identity, "hash", None) is not None:
        identity_hash = identity.hash.hex()
    if not (
        session.get("authenticated", False)
        and identity_hash
        and session.get("identity_hash") == identity_hash
    ):
        return web.json_response({"error": "Authentication required"}, status=401)
    return None


def _reject_forbidden_ws_origin(app, request):
    listen_host = getattr(app, "listen_host", None)
    auth_enabled = bool(getattr(app, "auth_enabled", False))
    if websocket_origin_policy_allows(
        request,
        listen_host=listen_host,
        auth_enabled=auth_enabled,
        trusted_proxy_cidrs=get_trusted_proxy_cidrs(app.storage_dir),
        origin_allowed_fn=websocket_origin_allowed,
        is_loopback_fn=_is_loopback_bind_host,
    ):
        return None
    return web.json_response({"error": "Forbidden origin"}, status=403)


# Same ceiling as RNProbeHandler.MAX_TIMEOUT_S
PATH_PROBE_MIN_TIMEOUT_S = 1
PATH_PROBE_MAX_TIMEOUT_S = 600
PATH_WAIT_REQUIRES_POST_MESSAGE = (
    "Waiting for a path requires POST. GET /path is a snapshot only."
)


def parse_websocket_upgrade_timeout(raw, *, default=None):
    if raw is None or raw == "":
        raw = default
    if raw is None or raw == "":
        return None, None
    try:
        timeout_seconds = int(raw)
    except (TypeError, ValueError):
        return None, "Timeout must be an integer."
    if (
        timeout_seconds < PATH_PROBE_MIN_TIMEOUT_S
        or timeout_seconds > PATH_PROBE_MAX_TIMEOUT_S
    ):
        return None, (
            f"Timeout must be between {PATH_PROBE_MIN_TIMEOUT_S} and "
            f"{PATH_PROBE_MAX_TIMEOUT_S} seconds."
        )
    return timeout_seconds, None


async def read_websocket_upgrade_timeout_raw(request, default=None):
    query = getattr(request, "query", None) or {}
    if "timeout" in query:
        return query.get("timeout")
    method = str(getattr(request, "method", "GET") or "GET").upper()
    if method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict) and body.get("timeout") is not None:
            return body.get("timeout")
    return default


def lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex: str) -> bytes:
    """Return lxmf.delivery bytes for transport path and ping operations.

    The UI may pass an identity hash or an lxmf.delivery hash. Reticulum
    path tables are keyed by destination hash, not identity hash.
    """
    fallback = bytes.fromhex(destination_hash_hex)
    with contextlib.suppress(Exception):
        resolved_hex = app.get_lxmf_destination_hash_for_identity_hash(
            destination_hash_hex,
        )
        if isinstance(resolved_hex, str):
            stripped = resolved_hex.strip()
            if len(stripped) == 32:
                return bytes.fromhex(stripped)
    return fallback


def lxmf_delivery_hash_hex_for_path(app, destination_hash_hex: str) -> str:
    return lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex).hex()


def local_destination_hashes(app):
    hashes: set[str] = set()
    with contextlib.suppress(Exception):
        if app.current_context and app.current_context.identity:
            hashes.add(app.current_context.identity.hash.hex())
    with contextlib.suppress(Exception):
        if app.local_lxmf_destination is not None:
            hashes.add(app.local_lxmf_destination.hash.hex())
    with contextlib.suppress(Exception):
        if app.current_context and app.current_context.message_router:
            pdest = app.current_context.message_router.propagation_destination
            if pdest is not None and getattr(pdest, "hash", None):
                hashes.add(pdest.hash.hex())
    return hashes
