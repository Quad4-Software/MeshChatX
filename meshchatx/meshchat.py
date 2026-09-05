#!/usr/bin/env python
# SPDX-License-Identifier: 0BSD AND MIT

import argparse
import asyncio
import atexit
import base64
import binascii
import configparser
import contextlib
import copy
import fnmatch
import gc
import hashlib
import importlib
import importlib.metadata
import io
import json
import logging
import os
import platform
import re
import runpy
import secrets
import shutil
import signal
import socket
import sqlite3
import ssl
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
import zipfile
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import urlparse

import aiohttp
import bcrypt
import LXMF

# meshchatx/__init__ already ensures pyogg ctypes aliases. Import LXST after
# that package init so plain pip installs do not crash without the Docker patch.
import LXST
import psutil
import RNS
from aiohttp import WSCloseCode, WSMessage, WSMsgType, web
from aiohttp_session import get_session
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from RNS.Discovery import InterfaceDiscovery
from serial.tools import list_ports

from meshchatx.android_push_bridge import (
    _get_android_external_files_dir,
    _is_chaquopy_android,
)
from meshchatx.src.backend import (
    gif_utils,
    i2p_support,
    reticulum_pathfinding,
    sticker_pack_utils,
)
from meshchatx.src.backend.active_sessions import (
    ActiveSessionTracker,
    should_warn_multi_session,
)
from meshchatx.src.backend.altcha_auth import altcha_enabled_from_env
from meshchatx.src.backend.announce_manager import (
    filter_announced_dicts_by_search_query,
)
from meshchatx.src.backend.app_security_settings import (
    get_trusted_proxy_cidrs,
    get_web_ui_ip_allowlist,
    load_app_security_settings,
    save_app_security_settings,
)
from meshchatx.src.backend.appcontainer_sandbox import (
    appcontainer_auto_enabled,
    appcontainer_disabled_by_env,
    appcontainer_requested,
    appcontainer_supported,
    apply_windows_process_mitigations,
    is_appcontainer_child,
)
from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.auth_page_hint import auth_page_hint_from_env
from meshchatx.src.backend.auto_resend_guard import (
    AUTO_RESEND_COOLDOWN_SECONDS,
    MAX_AUTO_RESEND_ATTEMPTS,
    RECENT_SAME_CONTENT_SECONDS,
    AutoResendCoordinator,
    cooldown_until,
    fields_have_attachments,
    fields_with_auto_resend_count,
    next_attempt_count,
    parse_fields_dict,
    should_skip_for_budget,
)
from meshchatx.src.backend.colour_utils import ColourUtils
from meshchatx.src.backend.csrf import (
    ensure_session_csrf_token,
    rotate_session_csrf_token,
    validate_csrf_header,
)
from meshchatx.src.backend.database.access_attempts import (
    LOGIN_PATH,
    MAX_FAILED_BEFORE_LOCKOUT,
    MAX_TRUSTED_LOGIN_PER_WINDOW,
    MAX_UNTRUSTED_LOGIN_PER_WINDOW,
    SETUP_PATH,
    WINDOW_LOCKOUT_S,
    WINDOW_RATE_TRUSTED_S,
    WINDOW_RATE_UNTRUSTED_S,
    user_agent_hash,
)
from meshchatx.src.backend.demo_mode import (
    auth_bypass_from_env,
    demo_auth_password_from_env,
)
from meshchatx.src.backend.identity_context import IdentityContext
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.interface_editor import InterfaceEditor
from meshchatx.src.backend.interface_port_check import (
    describe_port_conflict,
    is_port_in_use,
)
from meshchatx.src.backend.ip_allowlist import client_ip_allowed
from meshchatx.src.backend.landlock_sandbox import (
    apply_landlock_sandbox,
    extra_read_roots_from_app,
    landlock_auto_enabled,
    landlock_disabled_by_env,
    landlock_kernel_supported,
    landlock_requested,
)
from meshchatx.src.backend.rns_filesync_handler import (
    collect_external_filesync_rw_roots,
)
from meshchatx.src.backend.legacy_migrator import (
    assert_migration_context_paths,
    fresh_storage_at_target,
    migrate_legacy_to_target,
    resolve_startup_storage,
)
from meshchatx.src.backend.local_message_retention import (
    purge_messages_before_cutoff,
    resolve_message_age_cutoff,
)
from meshchatx.src.backend.lxmf_message_fields import (
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
)
from meshchatx.src.backend.lxmf_sieve import (
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
    parse_lxmf_sieve_filters_json,
)
from meshchatx.src.backend.lxmf_utils import (
    FIELD_REACTION,
    FIELD_REPLY_QUOTE,
    FIELD_REPLY_TO,
    LXMF_APP_EXTENSIONS_FIELD,
    build_lxmf_reaction_field,
    compute_lxmf_conversation_unread_from_latest_row,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_lxmf_method_to_string,
    convert_lxmf_state_to_string,
    extract_sideband_command_entries,
    is_lxmf_outbound_progress_terminal,
    is_user_facing_lxmf_payload,
    lxmf_is_reaction_only_delivery,
    lxmf_sidebar_preview_for_conversation_latest_row,
)
from meshchatx.src.backend.map_geo_validator import GeoValidationError
from meshchatx.src.backend.map_manager import (
    MAX_EXPORT_TILES,
    TRANSPARENT_TILE,
    is_mbtiles_filename,
)
from meshchatx.src.backend.map_overlay_export import OverlayExportError
from meshchatx.src.backend.map_overlay_manager import (
    CONFIG_CLAMPS,
    clamp_overlay_config_value,
)
from meshchatx.src.backend.map_overlay_sources import OverlaySourceParseError
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer
from meshchatx.src.backend.memory_pressure import (
    MemoryPressureManager,
    cache_stats,
    prune_announce_timestamps,
    prune_lxmf_incoming_timestamps,
)
from meshchatx.src.backend.meshchat_utils import (
    cancel_inbound_deliveries,
    convert_db_favourite_to_dict,
    convert_propagation_node_state_to_string,
    has_attachments,
    hex_identifier_to_bytes,
    interval_action_due,
    list_inbound_deliveries,
    message_fields_have_attachments,
    normalize_hex_identifier,
    normalize_identity_storage_hash,
    parse_bool_query_param,
    lxmf_signature_validated,
    normalize_lxmf_destination_hash,
    parse_lxmf_audio_field_value,
    parse_lxmf_display_name,
    parse_lxmf_file_attachments_field_value,
    parse_lxmf_icon_appearance,
    parse_lxmf_image_field_value,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    parse_nomadnetwork_node_display_name,
    propagation_sync_idle_like,
    propagation_sync_is_terminal,
)
from meshchatx.src.backend.message_blocklist import (
    build_export_document as build_blocklist_export_document,
)
from meshchatx.src.backend.message_blocklist import (
    first_matching_blocklist_entry,
    normalize_message_blocklist,
    parse_import_document,
    parse_message_blocklist_json,
)
from meshchatx.src.backend.message_export_bundle import (
    build_messages_export_bundle,
    import_messages_export_bundle,
)
from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    clear_all_nomadnet_cached_links,
    drop_cached_link,
    get_cached_active_link,
    nomad_link_identity_kwargs,
)
from meshchatx.src.backend.nomadnet_utils import (
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
)
from meshchatx.src.backend.page_node_manager import PageNodeManager
from meshchatx.src.backend.persistent_log_handler import PersistentLogHandler
from meshchatx.src.backend.plugin_guard import PluginSecurityError
from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.privacy_mode import (
    OutboundHttpBlockedError,
    ensure_outbound_http_allowed,
    privacy_mode_enabled,
)
from meshchatx.src.backend.recovery import (
    CrashRecovery,
    HealthMonitor,
    evaluate_startup_memory,
    format_memory_log_line,
)
from meshchatx.src.backend.reticulum_config_guard import (
    ensure_safe_reticulum_runtime_flags,
    repair_unparseable_reticulum_config,
    reticulum_config_has_required_sections,
)
from meshchatx.src.backend.rnprobe_handler import RNProbeHandler
from meshchatx.src.backend.rns_link_manager import (
    RnsLinkManager,
    clear_all_cached_links,
)
from meshchatx.src.backend.rns_ratchet_persist import (
    install_bounded_ratchet_persist,
    raise_nofile_soft_limit,
)
from meshchatx.src.backend.rns_startup_recovery import (
    create_reticulum_with_recovery,
    install_rns_panic_containment,
)
from meshchatx.src.backend.rrc import protocol as rrc_protocol
from meshchatx.src.backend.safe_rotating_file_handler import SafeRotatingFileHandler
from meshchatx.src.backend.seccomp_sandbox import (
    apply_seccomp_sandbox,
    seccomp_auto_enabled,
    seccomp_disabled_by_env,
    seccomp_kernel_supported,
    seccomp_requested,
)
from meshchatx.src.backend.sideband_commands import SidebandCommands
from meshchatx.src.backend.sideband_plugin_loader import SidebandPluginLoader
from meshchatx.src.backend.sticker_utils import (
    build_export_document,
    detect_image_format_from_magic,
    mime_for_image_type,
    sanitize_sticker_emoji,
    sanitize_sticker_name,
    validate_export_document,
)
from meshchatx.src.backend.telemetry_utils import Telemeter, _valid_number
from meshchatx.src.backend.web_audio_bridge import WebAudioBridge
from meshchatx.src.backend.websocket_config_guard import (
    sanitize_websocket_config_update,
    websocket_type_requires_auth,
)
from meshchatx.src.env_utils import env_bool
from meshchatx.src.path_utils import (
    get_file_path,
    is_path_within_dir,
    resolve_log_dir,
    resolve_meshchat_data_roots,
    safe_path_under_dir,
)
from meshchatx.src.path_utils import (
    request_client_ip as _request_client_ip,
)
from meshchatx.src.ssl_self_signed import generate_ssl_certificate
from meshchatx.src.version import __version__ as app_version


def _truncated_hash32_hex_ok(value: str | None) -> bool:
    """32 lowercase hex chars (Reticulum truncated hash) without relying on live RNS constants."""
    return bool(normalize_identity_storage_hash(value))


# Global log handler
memory_log_handler = PersistentLogHandler()
log_dir = resolve_log_dir()
handlers = [memory_log_handler]

if log_dir:
    file_handler = SafeRotatingFileHandler(
        os.path.join(log_dir, "meshchatx.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handlers.append(file_handler)
else:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(level=logging.INFO, handlers=handlers)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logger = logging.getLogger("meshchatx")


def _parse_rns_loglevel_value(raw: str | None) -> int | None:
    if not raw or not str(raw).strip():
        return None
    raw = str(raw).strip().lower()
    named = {
        "none": RNS.LOG_NONE,
        "critical": RNS.LOG_CRITICAL,
        "error": RNS.LOG_ERROR,
        "warning": RNS.LOG_WARNING,
        "notice": RNS.LOG_NOTICE,
        "verbose": RNS.LOG_VERBOSE,
        "debug": RNS.LOG_DEBUG,
        "extreme": RNS.LOG_EXTREME,
    }
    if raw in named:
        return named[raw]
    try:
        return int(raw)
    except ValueError:
        return None


def _resolve_rns_loglevel(cli_override: str | None) -> int | None:
    if cli_override is not None and str(cli_override).strip():
        return _parse_rns_loglevel_value(cli_override)
    return _parse_rns_loglevel_value(os.environ.get("MESHCHAT_RNS_LOG_LEVEL"))


_rns_bridge_logger = logging.getLogger("meshchatx.rns")


def _rns_log_to_python_logging(logstring: str) -> None:
    """Forward already-formatted RNS log lines into the MeshChatX logger."""
    try:
        _rns_bridge_logger.info("%s", logstring)
    except Exception:
        pass


def _resolve_rns_logdest():
    """Choose RNS log destination.

    When a writable log_dir exists, default to a callback into Python logging
    so RNS output shares SafeRotatingFileHandler and does not flood Docker
    stdout. Set MESHCHAT_RNS_LOG_DEST=stdout to keep the RNS console default.
    """
    raw = (os.environ.get("MESHCHAT_RNS_LOG_DEST") or "").strip().lower()
    if raw in ("stdout", "console", "stderr"):
        return None
    if raw in ("", "logging", "callback", "file") and log_dir:
        return _rns_log_to_python_logging
    return None


def _restore_rns_console_logging_after_reticulum_init(app) -> None:
    """Undo shutdown side effects from RNS.Reticulum.exit_handler.

    That handler sets RNS.loglevel to LOG_NONE and points sys.stdout /
    sys.stderr at os.devnull. Without this, hot reload appears to stop all
    announce traffic logging even though interfaces are up.

    When no CLI or MESHCHAT_RNS_LOG_LEVEL value applies and the level is still
    LOG_NONE after reading config, fall back to LOG_WARNING so notices are
    visible. Explicit none in the environment remains respected.
    """
    try:
        if hasattr(sys, "__stdout__"):
            sys.stdout = sys.__stdout__
        if hasattr(sys, "__stderr__"):
            sys.stderr = sys.__stderr__
    except Exception:
        pass
    resolved = _resolve_rns_loglevel(getattr(app, "_rns_loglevel_cli", None))
    if resolved is None and RNS.loglevel == RNS.LOG_NONE:
        RNS.loglevel = RNS.LOG_WARNING


def _create_reticulum_instance(
    config_dir: str,
    loglevel: int | None = None,
    logdest=None,
):
    """Construct RNS.Reticulum even when called off the main thread.

    Reticulum registers SIGINT/SIGTERM handlers in __init__. Python only allows
    signal.signal on the main thread, so deferred network setup must skip that
    registration when running in a background worker and install handlers later.

    On failure, progressively disables risky interfaces (I2P, unsupported RNode,
    AutoInterface, etc.) and retries so Android/desktop can recover without
    wiping app data or the whole .reticulum tree. RNS.panic is contained
    so it cannot os._exit the MeshChatX process.
    """
    kwargs = {}
    if loglevel is not None:
        kwargs["loglevel"] = loglevel
    resolved_logdest = logdest if logdest is not None else _resolve_rns_logdest()
    if resolved_logdest is not None:
        kwargs["logdest"] = resolved_logdest

    def _construct():
        if threading.current_thread() is threading.main_thread():
            return RNS.Reticulum(config_dir, **kwargs)

        real_signal = signal.signal

        def _signal_allow_non_main(signum, handler):
            try:
                return real_signal(signum, handler)
            except ValueError:
                return signal.getsignal(signum)

        signal.signal = _signal_allow_non_main
        try:
            return RNS.Reticulum(config_dir, **kwargs)
        finally:
            signal.signal = real_signal

    return create_reticulum_with_recovery(
        config_dir,
        construct=_construct,
    )


def _install_reticulum_signal_handlers() -> bool:
    """Install MeshChat SIGINT/SIGTERM handlers (flush DB, then GracefulExit).

    Must run on the main thread. Replaces raw RNS handlers that used to call
    RNS.exit / os._exit and skip SQLite WAL checkpoint.
    """
    from meshchatx.src.backend.lifecycle.signal_shutdown import (
        install_meshchat_signal_handlers,
    )

    return install_meshchat_signal_handlers()


def list_host_network_interfaces():
    """Enumerate kernel network interfaces on the host running MeshChat.

    Uses psutil (Linux, macOS, Windows). Fails soft on restricted environments
    (e.g. some Android sandboxes) and returns ([], error).

    Reticulum's device field on server-style interfaces is a *single* interface
    name, or omitted when binding only via listen_ip.
    """
    try:
        raw = psutil.net_if_addrs()
    except Exception as exc:
        logging.debug("list_host_network_interfaces: net_if_addrs failed: %s", exc)
        return [], str(exc)
    out: list[dict[str, object]] = []
    for name in sorted(raw.keys(), key=lambda n: str(n).lower()):
        addrs: list[str] = []
        for addr in raw[name]:
            if addr.family == socket.AF_INET:
                addrs.append(addr.address)
            elif addr.family == socket.AF_INET6:
                if addr.address.startswith("fe80:"):
                    continue
                addrs.append(addr.address)
        out.append({"name": name, "addresses": addrs})
    return out, None


def _is_loopback_bind_host(host: str | None) -> bool:
    h = (host or "").strip().lower()
    # Unset or empty means the default loopback bind has not been overridden.
    if not h:
        return True
    return h in ("127.0.0.1", "localhost", "::1", "[::1]")


def _csrf_exempt_path(path: str) -> bool:
    return path == "/api/v1/auth/csrf"


# Live-name anchors for backend.http (meshchat_names / LiveMeshchatName).
_HTTP_LIVE_NAME_ANCHORS = (
    binascii,
    build_blocklist_export_document,
    io,
    platform,
    sqlite3,
    tempfile,
    zipfile,
    cast,
    urlparse,
    aiohttp,
    bcrypt,
    WSMessage,
    WSMsgType,
    InterfaceDiscovery,
    list_ports,
    gif_utils,
    sticker_pack_utils,
    filter_announced_dicts_by_search_query,
    get_web_ui_ip_allowlist,
    load_app_security_settings,
    save_app_security_settings,
    ensure_session_csrf_token,
    rotate_session_csrf_token,
    validate_csrf_header,
    LOGIN_PATH,
    SETUP_PATH,
    InterfaceConfigParser,
    describe_port_conflict,
    is_port_in_use,
    client_ip_allowed,
    assert_migration_context_paths,
    fresh_storage_at_target,
    migrate_legacy_to_target,
    normalize_lxmf_sieve_filters,
    compute_lxmf_conversation_unread_from_latest_row,
    convert_db_lxmf_message_to_dict,
    is_user_facing_lxmf_payload,
    lxmf_sidebar_preview_for_conversation_latest_row,
    GeoValidationError,
    MAX_EXPORT_TILES,
    TRANSPARENT_TILE,
    is_mbtiles_filename,
    OverlayExportError,
    OverlaySourceParseError,
    MarkdownRenderer,
    cache_stats,
    cancel_inbound_deliveries,
    convert_db_favourite_to_dict,
    convert_propagation_node_state_to_string,
    parse_bool_query_param,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    build_export_document,
    normalize_message_blocklist,
    parse_import_document,
    purge_messages_before_cutoff,
    resolve_message_age_cutoff,
    build_messages_export_bundle,
    import_messages_export_bundle,
    NomadnetFileDownloader,
    get_cached_active_link,
    drop_cached_link,
    nomad_link_identity_kwargs,
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
    PluginSecurityError,
    OutboundHttpBlockedError,
    privacy_mode_enabled,
    RNProbeHandler,
    detect_image_format_from_magic,
    mime_for_image_type,
    sanitize_sticker_emoji,
    sanitize_sticker_name,
    validate_export_document,
    sanitize_websocket_config_update,
    websocket_type_requires_auth,
    safe_path_under_dir,
)


class ReticulumMeshChat:
    DEFAULT_AUTOCONNECT_DISCOVERED_INTERFACES = 3

    def __init__(
        self,
        identity: RNS.Identity,
        storage_dir,
        reticulum_config_dir,
        auto_recover: bool = False,
        identity_file_path: str | None = None,
        auth_enabled: bool = False,
        public_dir: str | None = None,
        emergency: bool = False,
        gitea_base_url: str | None = None,
        ssl_cert_path: str | None = None,
        ssl_key_path: str | None = None,
        rns_loglevel: str | None = None,
        migration_context: dict | None = None,
        memory_diag_enabled: bool = False,
        plugins_enabled: bool = True,
        defer_network_setup: bool = False,
        headless: bool = False,
        demo_mode: bool = False,
        altcha_enabled: bool = False,
    ):
        self.running = True
        self.plugins_enabled = plugins_enabled
        self.demo_mode = bool(demo_mode)
        self.altcha_enabled = bool(altcha_enabled)
        self.auth_page_hint = auth_page_hint_from_env()
        self._memory_diag_enabled = memory_diag_enabled
        self._mem_diag = None
        self._headless = bool(headless)
        self.migration_context = (
            migration_context if migration_context is not None else {}
        )
        self.reticulum_config_dir = self._normalize_reticulum_config_dir(
            reticulum_config_dir,
        )
        self.storage_dir = storage_dir or os.path.join("storage")
        skip_storage_lock = os.environ.get(
            "MESHCHAT_SKIP_STORAGE_LOCK",
            "",
        ).lower() in (
            "1",
            "true",
            "yes",
        )
        self._storage_lock = None
        if not skip_storage_lock:
            # Serializes startup, schema migration, and runtime for one storage_dir.
            from meshchatx.src.backend.storage_lock import StorageLock, StorageLockError

            self._storage_lock = StorageLock(self.storage_dir)
            try:
                self._storage_lock.acquire()
            except StorageLockError as exc:
                print(str(exc))
                raise SystemExit(1) from exc
        self.ssl_cert_path = ssl_cert_path
        self.ssl_key_path = ssl_key_path
        self.identity_file_path = identity_file_path
        self.auto_recover = auto_recover
        self.emergency = emergency
        self.auth_enabled_initial = auth_enabled
        self.public_dir_override = public_dir
        self.gitea_base_url_override = gitea_base_url
        self._rns_loglevel_cli = rns_loglevel
        self.websocket_clients: list[web.WebSocketResponse] = []
        # Cap UI /ws clients so a reconnect storm cannot exhaust process FDs.
        self.max_websocket_clients = 64
        # Cap after Nomad chunking: whole-file frames only for small payloads.
        self.websocket_max_msg_size = 16 * 1024 * 1024

        self.active_sessions = ActiveSessionTracker()
        self._websocket_broadcast_lock = asyncio.Lock()
        from meshchatx.src.backend.websocket_runtime import (
            BroadcastSeqState,
            CoalesceBuffer,
            WsRuntimeCounters,
        )

        self.ws_counters = WsRuntimeCounters()
        self.ws_seq_state = BroadcastSeqState()
        self._ws_coalesce = CoalesceBuffer(self._websocket_broadcast_coalesced)
        self._identity_hotswap_lock = asyncio.Lock()
        self.listen_host: str | None = None
        self.listen_port: int | None = None
        self.use_https: bool = True
        self.landlock_active: bool = False
        self.appcontainer_active: bool = False
        self.seccomp_active: bool = False
        self._pending_identity = identity
        self._network_setup_lock = threading.Lock()
        self._network_ready_event = threading.Event()
        self._network_setup_thread: threading.Thread | None = None
        self._startup_stage = "ready" if not defer_network_setup else "http"
        self._startup_error: str | None = None
        self._network_ready = not defer_network_setup
        self._network_degraded = False
        # HTTP can serve the shell immediately while RNS/identity finish.
        self._ui_ready = True
        self._rns_recovery_actions: list[str] = []
        self._reticulum_secondary_started = False

        # track announce timestamps for rate calculation (pruned to 1 hour / cap)
        self.announce_timestamps = []

        # track incoming lxmf message timestamps for flood protection
        self._lxmf_incoming_timestamps = []
        self._flood_protection_current_cost = None
        self._flood_protection_last_bump_time = 0

        # track download speeds for nomadnetwork files
        self.download_speeds = []

        # track active downloads
        self.active_downloads = {}
        self.download_id_counter = 0

        self.identity_manager = IdentityManager(self.storage_dir, identity_file_path)
        self.page_node_manager = PageNodeManager(
            self.storage_dir,
            on_announce=self._register_local_page_node_announce,
        )
        self.plugin_manager = PluginManager(self.storage_dir, app=self)
        from meshchatx.src.backend.bug_report_manager import BugReportManager

        self.bug_report_manager = BugReportManager(self)
        self.sideband_plugin_loader = SidebandPluginLoader(self)
        self._sideband_telemetry_thread = None
        self._sideband_telemetry_running = False

        # Multi-identity support
        self.contexts: dict[str, IdentityContext] = {}
        self.current_context: IdentityContext | None = None
        self._propagation_sync_metrics: dict[str, dict] = {}
        self._auto_resend_coordinator = AutoResendCoordinator()

        from meshchatx.src.backend.lifecycle.signal_shutdown import (
            register_shutdown_app,
        )

        register_shutdown_app(self)

        AsyncUtils.ensure_background_loop()
        self.web_audio_bridge = WebAudioBridge(
            None,
            None,
            force_enabled=self.web_audio_required(),
        )
        self.rns_link_manager = RnsLinkManager(
            self_identity_getter=lambda: self.identity,
            reticulum_getter=lambda: getattr(self, "reticulum", None),
            broadcast_event=self._on_rns_link_broadcast,
        )
        self.memory_pressure = MemoryPressureManager(app=self)
        from meshchatx.src.backend.battery_usage_estimate import BatteryUsageTracker

        self.battery_usage = BatteryUsageTracker()
        try:
            self._host_process = psutil.Process()
            # Prime cpu_percent so later non-blocking samples are meaningful.
            self._host_process.cpu_percent(interval=None)
        except Exception:
            self._host_process = None
        # Track long-running rns.link.* handler tasks per WS client so they can
        # be cancelled when the client disconnects.
        self._rns_link_tasks: dict[web.WebSocketResponse, set[asyncio.Task]] = {}
        # Anchor RequestReceipts returned by link.request() for the lifetime of
        # the request. Keyed by (client, request_id).
        self._rns_request_receipts: dict = {}
        if defer_network_setup:
            self._set_startup_stage("http")
        else:
            self.setup_identity(identity)
            self._mark_network_ready()
            self._finish_deferred_startup_services()

    def web_audio_required(self) -> bool:
        """True when LXST host audio is unusable and the browser bridge is mandatory.

        Chaquopy Android has no usable LXST LineSource path. Docker/Alpine images
        typically lack PulseAudio. Do not key this off --headless alone: frozen
        Electron also uses headless (no auto browser) while still having host audio.

        MESHCHAT_FORCE_WEB_AUDIO=1 forces the bridge for debugging or custom hosts.
        """
        if _is_chaquopy_android():
            return True
        force = os.environ.get("MESHCHAT_FORCE_WEB_AUDIO", "").strip().lower()
        if force in ("1", "true", "yes", "on"):
            return True
        cached = getattr(self, "_host_audio_unavailable_cached", None)
        if cached is not None:
            return cached
        unavailable = self._probe_host_audio_unavailable()
        self._host_audio_unavailable_cached = unavailable
        return unavailable

    @staticmethod
    def _probe_host_audio_unavailable() -> bool:
        """Return True when LXST cannot open a host capture device."""
        try:
            from LXST.Sources import Backend

            if Backend is None:
                return True
            Backend()
            return False
        except Exception:
            return True

    # Proxy properties for backward compatibility
    @property
    def identity(self):
        return self.current_context.identity if self.current_context else None

    @identity.setter
    def identity(self, value):
        if self.current_context:
            self.current_context.identity = value

    @property
    def database(self):
        return self.current_context.database if self.current_context else None

    @database.setter
    def database(self, value):
        if self.current_context:
            self.current_context.database = value

    @property
    def db(self):
        return self.database

    @db.setter
    def db(self, value):
        self.database = value

    @property
    def config(self):
        return self.current_context.config if self.current_context else None

    @config.setter
    def config(self, value):
        if self.current_context:
            self.current_context.config = value

    @property
    def message_handler(self):
        return self.current_context.message_handler if self.current_context else None

    @message_handler.setter
    def message_handler(self, value):
        if self.current_context:
            self.current_context.message_handler = value

    @property
    def announce_manager(self):
        return self.current_context.announce_manager if self.current_context else None

    @announce_manager.setter
    def announce_manager(self, value):
        if self.current_context:
            self.current_context.announce_manager = value

    @property
    def archiver_manager(self):
        return self.current_context.archiver_manager if self.current_context else None

    @archiver_manager.setter
    def archiver_manager(self, value):
        if self.current_context:
            self.current_context.archiver_manager = value

    @property
    def map_manager(self):
        return self.current_context.map_manager if self.current_context else None

    @map_manager.setter
    def map_manager(self, value):
        if self.current_context:
            self.current_context.map_manager = value

    @property
    def map_overlay_manager(self):
        return (
            self.current_context.map_overlay_manager if self.current_context else None
        )

    @map_overlay_manager.setter
    def map_overlay_manager(self, value):
        if self.current_context:
            self.current_context.map_overlay_manager = value

    @property
    def map_data_manager(self):
        return self.current_context.map_data_manager if self.current_context else None

    @map_data_manager.setter
    def map_data_manager(self, value):
        if self.current_context:
            self.current_context.map_data_manager = value

    @property
    def docs_manager(self):
        return self.current_context.docs_manager if self.current_context else None

    @docs_manager.setter
    def docs_manager(self, value):
        if self.current_context:
            self.current_context.docs_manager = value

    @property
    def repository_server_manager(self):
        return (
            self.current_context.repository_server_manager
            if self.current_context
            else None
        )

    @repository_server_manager.setter
    def repository_server_manager(self, value):
        if self.current_context:
            self.current_context.repository_server_manager = value

    @property
    def nomadnet_manager(self):
        return self.current_context.nomadnet_manager if self.current_context else None

    @nomadnet_manager.setter
    def nomadnet_manager(self, value):
        if self.current_context:
            self.current_context.nomadnet_manager = value

    @property
    def message_router(self):
        return self.current_context.message_router if self.current_context else None

    @message_router.setter
    def message_router(self, value):
        if self.current_context:
            self.current_context.message_router = value

    @property
    def telephone_manager(self):
        return self.current_context.telephone_manager if self.current_context else None

    @telephone_manager.setter
    def telephone_manager(self, value):
        if self.current_context:
            self.current_context.telephone_manager = value

    @property
    def voicemail_manager(self):
        return self.current_context.voicemail_manager if self.current_context else None

    @voicemail_manager.setter
    def voicemail_manager(self, value):
        if self.current_context:
            self.current_context.voicemail_manager = value

    @property
    def ringtone_manager(self):
        return self.current_context.ringtone_manager if self.current_context else None

    @ringtone_manager.setter
    def ringtone_manager(self, value):
        if self.current_context:
            self.current_context.ringtone_manager = value

    @property
    def notification_sound_manager(self):
        return (
            self.current_context.notification_sound_manager
            if self.current_context
            else None
        )

    @notification_sound_manager.setter
    def notification_sound_manager(self, value):
        if self.current_context:
            self.current_context.notification_sound_manager = value

    @property
    def rncp_handler(self):
        return self.current_context.rncp_handler if self.current_context else None

    @rncp_handler.setter
    def rncp_handler(self, value):
        if self.current_context:
            self.current_context.rncp_handler = value

    @property
    def rns_filesync_handler(self):
        return (
            self.current_context.rns_filesync_handler if self.current_context else None
        )

    @rns_filesync_handler.setter
    def rns_filesync_handler(self, value):
        if self.current_context:
            self.current_context.rns_filesync_handler = value

    @property
    def rnsh_manager(self):
        return self.current_context.rnsh_manager if self.current_context else None

    @rnsh_manager.setter
    def rnsh_manager(self, value):
        if self.current_context:
            self.current_context.rnsh_manager = value

    @property
    def rnx_manager(self):
        return self.current_context.rnx_manager if self.current_context else None

    @rnx_manager.setter
    def rnx_manager(self, value):
        if self.current_context:
            self.current_context.rnx_manager = value

    @property
    def rnstatus_handler(self):
        return self.current_context.rnstatus_handler if self.current_context else None

    @rnstatus_handler.setter
    def rnstatus_handler(self, value):
        if self.current_context:
            self.current_context.rnstatus_handler = value

    @property
    def rnpath_handler(self):
        return self.current_context.rnpath_handler if self.current_context else None

    @rnpath_handler.setter
    def rnpath_handler(self, value):
        if self.current_context:
            self.current_context.rnpath_handler = value

    @property
    def rnpath_trace_handler(self):
        return (
            self.current_context.rnpath_trace_handler if self.current_context else None
        )

    @rnpath_trace_handler.setter
    def rnpath_trace_handler(self, value):
        if self.current_context:
            self.current_context.rnpath_trace_handler = value

    @property
    def rnprobe_handler(self):
        return self.current_context.rnprobe_handler if self.current_context else None

    @rnprobe_handler.setter
    def rnprobe_handler(self, value):
        if self.current_context:
            self.current_context.rnprobe_handler = value

    @property
    def translator_handler(self):
        return self.current_context.translator_handler if self.current_context else None

    @translator_handler.setter
    def translator_handler(self, value):
        if self.current_context:
            self.current_context.translator_handler = value

    @property
    def bot_handler(self):
        return self.current_context.bot_handler if self.current_context else None

    @bot_handler.setter
    def bot_handler(self, value):
        if self.current_context:
            self.current_context.bot_handler = value

    @property
    def forwarding_manager(self):
        return self.current_context.forwarding_manager if self.current_context else None

    @forwarding_manager.setter
    def forwarding_manager(self, value):
        if self.current_context:
            self.current_context.forwarding_manager = value

    @property
    def rrc_manager(self):
        return self.current_context.rrc_manager if self.current_context else None

    @rrc_manager.setter
    def rrc_manager(self, value):
        if self.current_context:
            self.current_context.rrc_manager = value

    @property
    def rrc_server_manager(self):
        return self.current_context.rrc_server_manager if self.current_context else None

    @rrc_server_manager.setter
    def rrc_server_manager(self, value):
        if self.current_context:
            self.current_context.rrc_server_manager = value

    @property
    def community_interfaces_manager(self):
        return (
            self.current_context.community_interfaces_manager
            if self.current_context
            else None
        )

    @community_interfaces_manager.setter
    def community_interfaces_manager(self, value):
        if self.current_context:
            self.current_context.community_interfaces_manager = value

    @property
    def local_lxmf_destination(self):
        return (
            self.current_context.local_lxmf_destination
            if self.current_context
            else None
        )

    @local_lxmf_destination.setter
    def local_lxmf_destination(self, value):
        if self.current_context:
            self.current_context.local_lxmf_destination = value

    @property
    def auth_enabled(self):
        if auth_bypass_from_env():
            return False
        if self.config:
            return self.config.auth_enabled.get()
        return self.auth_enabled_initial

    @property
    def storage_path(self):
        return (
            self.current_context.storage_path
            if self.current_context
            else self.storage_dir
        )

    @storage_path.setter
    def storage_path(self, value):
        if self.current_context:
            self.current_context.storage_path = value

    def _check_bot_lifecycle(self) -> tuple[bool, str]:
        """Create, start, stop, and delete an Echo bot subprocess.

        Uses an isolated identity + Reticulum config under storage so the check
        does not touch user bots or ~/.reticulum.
        """
        from meshchatx.src.backend.bot_handler import BotHandler

        if not self.storage_path or not os.path.exists(self.storage_path):
            return False, "Storage directory does not exist"

        root = os.path.join(self.storage_path, ".self_test_bots")
        identity_dir = os.path.join(root, "identity")
        rns_dir = os.path.join(root, "reticulum")
        bot_id = None
        handler = None
        try:
            if os.path.isdir(root):
                shutil.rmtree(root, ignore_errors=True)
            os.makedirs(identity_dir, exist_ok=True)
            os.makedirs(rns_dir, exist_ok=True)

            previous_rns = os.environ.get("MESHCHAT_BOT_RETICULUM_CONFIG_DIR")
            os.environ["MESHCHAT_BOT_RETICULUM_CONFIG_DIR"] = rns_dir
            try:
                handler = BotHandler(identity_path=identity_dir)
                bot_id = handler.start_bot("echo", "Self-Check Echo Bot")
            finally:
                if previous_rns is None:
                    os.environ.pop("MESHCHAT_BOT_RETICULUM_CONFIG_DIR", None)
                else:
                    os.environ["MESHCHAT_BOT_RETICULUM_CONFIG_DIR"] = previous_rns

            entry = next(
                (e for e in handler.bots_state if e.get("id") == bot_id),
                None,
            )
            if entry is None:
                return False, "Bot entry missing after start"

            pid = entry.get("pid")
            if not pid:
                return False, "Bot process did not report a pid"

            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                if not BotHandler._is_pid_alive(pid):
                    last_err = BotHandler._read_bot_last_error(entry.get("storage_dir"))
                    log_tail = ""
                    try:
                        log_info = handler.read_subprocess_log(bot_id, max_bytes=2048)
                        log_tail = (log_info.get("log") or "").strip()[-500:]
                    except Exception:
                        pass
                    detail = last_err or log_tail or "process exited early"
                    return False, f"Bot process died after start: {detail}"
                # Confirm the launcher wrote something (script or run-module path).
                try:
                    log_info = handler.read_subprocess_log(bot_id, max_bytes=1024)
                    if log_info.get("total_bytes", 0) > 0:
                        break
                except Exception:
                    pass
                time.sleep(0.2)
            else:
                if not BotHandler._is_pid_alive(pid):
                    return False, "Bot process exited before becoming ready"
                # Still alive with empty log is acceptable (buffered / slow start).

            if not handler.stop_bot(bot_id):
                return False, "stop_bot returned False"
            stop_deadline = time.monotonic() + 8.0
            while time.monotonic() < stop_deadline and BotHandler._is_pid_alive(pid):
                time.sleep(0.1)
            if BotHandler._is_pid_alive(pid):
                return False, f"Bot pid {pid} still alive after stop"

            storage_dir = entry.get("storage_dir")
            if not handler.delete_bot(bot_id):
                return False, "delete_bot returned False"
            if any(e.get("id") == bot_id for e in handler.bots_state):
                return False, "Bot still present in state after delete"
            if storage_dir and os.path.exists(storage_dir):
                return False, "Bot storage directory still exists after delete"

            return True, ""
        except Exception as e:
            return False, f"Bot lifecycle check failed: {e}"
        finally:
            if handler is not None and bot_id is not None:
                with contextlib.suppress(Exception):
                    handler.stop_bot(bot_id)
                with contextlib.suppress(Exception):
                    handler.delete_bot(bot_id)
            with contextlib.suppress(Exception):
                if os.path.isdir(root):
                    shutil.rmtree(root, ignore_errors=True)

    def run_self_test(self) -> dict:
        stack_ok = True
        stack_reason = ""
        if not hasattr(self, "reticulum") or self.reticulum is None:
            stack_ok = False
            stack_reason = "Reticulum stack is not initialized"
        else:
            try:
                _ = self.reticulum.config
            except Exception as e:
                stack_ok = False
                stack_reason = f"Reticulum stack internal error: {e!s}"

        config_ok = True
        config_reason = ""
        try:
            if self.config is None:
                config_ok = False
                config_reason = "App configuration is not initialized"
            else:
                _ = self.config.display_name.get()
        except Exception as e:
            config_ok = False
            config_reason = f"App config error: {e!s}"

        if config_ok:
            try:
                reticulum_config_path = self._api_reticulum_config_path()
                if not reticulum_config_path or not os.path.exists(
                    reticulum_config_path,
                ):
                    config_ok = False
                    config_reason = "Reticulum config file not found"
                elif not reticulum_config_has_required_sections(
                    reticulum_config_path,
                ):
                    config_ok = False
                    config_reason = "Reticulum config is missing required sections"
            except Exception as e:
                config_ok = False
                config_reason = f"Reticulum config check failed: {e!s}"

        db_ok = True
        db_reason = ""
        if not self.database:
            db_ok = False
            db_reason = "Database is not initialized"
        else:
            try:
                self.database.execute_sql("SELECT 1").fetchone()
                snapshot = self.database.get_database_health_snapshot()
                if snapshot.get("quick_check") not in ("ok", "unknown"):
                    db_ok = False
                    db_reason = (
                        f"Database quick check returned: {snapshot.get('quick_check')}"
                    )
            except Exception as e:
                db_ok = False
                db_reason = f"Database check failed: {e!s}"

        rw_ok = True
        rw_reason = ""
        try:
            if not self.storage_path or not os.path.exists(self.storage_path):
                rw_ok = False
                rw_reason = "Storage directory does not exist"
            else:
                temp_file_path = os.path.join(self.storage_path, ".self_test_temp")
                test_data = "meshchatx_self_test_write_read_verify"
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(test_data)

                with open(temp_file_path, encoding="utf-8") as f:
                    read_data = f.read()

                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

                if read_data != test_data:
                    rw_ok = False
                    rw_reason = "Read data did not match written data"
        except Exception as e:
            rw_ok = False
            rw_reason = f"Read/write test failed: {e!s}"

        from meshchatx.src.backend import self_check as self_check_mod

        bots_ok, bots_reason = self._check_bot_lifecycle()
        identity_result = self_check_mod.check_identity(self.identity)
        imports_result = self_check_mod.check_critical_imports()
        # Fold Python runtime into imports so the UI stays one row.
        runtime_result = self_check_mod.check_python_runtime()
        if runtime_result["status"] != "ok" and imports_result["status"] == "ok":
            imports_result = runtime_result
        elif runtime_result["status"] != "ok":
            imports_result = {
                "status": "failed",
                "reason": f"{imports_result.get('reason') or ''} | {runtime_result.get('reason') or ''}".strip(
                    " |",
                ),
            }
        storage_lock_result = self_check_mod.check_storage_lock(
            self.storage_path or self.storage_dir,
        )
        temp_fs_result = self_check_mod.check_temp_filesystem()
        fs_sandbox_result = self_check_mod.check_fs_sandbox()
        public_assets_result = self_check_mod.check_public_assets(self.get_public_path)
        lxmf_result = self_check_mod.check_lxmf_router(
            self.message_router,
            self.local_lxmf_destination,
        )
        subprocess_result = self_check_mod.check_subprocess_spawn()
        run_module_result = self_check_mod.check_meshchatx_run_module()
        storage_base = self.storage_path or self.storage_dir
        sqlite_result = self_check_mod.check_sqlite_roundtrip(storage_base)
        identity_file_result = self_check_mod.check_identity_file_roundtrip(
            storage_base,
        )
        loopback_result = self_check_mod.check_loopback_tcp()
        unicode_result = self_check_mod.check_unicode_path(storage_base)
        rnode_result = self_check_mod.check_rnode_support()
        bot_launcher_result = self_check_mod.check_bot_launcher()
        plugins_runtime_result = self_check_mod.check_plugins_runtime(self)
        web_results = self_check_mod.check_web_stack(self)

        return {
            "stack_up": {
                "status": "ok" if stack_ok else "failed",
                "reason": stack_reason,
            },
            "config_good": {
                "status": "ok" if config_ok else "failed",
                "reason": config_reason,
            },
            "db_good": {
                "status": "ok" if db_ok else "failed",
                "reason": db_reason,
            },
            "read_write_good": {
                "status": "ok" if rw_ok else "failed",
                "reason": rw_reason,
            },
            "identity_good": identity_result,
            "imports_good": imports_result,
            "storage_lock_good": storage_lock_result,
            "temp_fs_good": temp_fs_result,
            "fs_sandbox_good": fs_sandbox_result,
            "public_assets_good": public_assets_result,
            "lxmf_router_good": lxmf_result,
            "subprocess_good": subprocess_result,
            "run_module_good": run_module_result,
            "sqlite_roundtrip": sqlite_result,
            "identity_roundtrip": identity_file_result,
            "loopback_tcp": loopback_result,
            "unicode_path_good": unicode_result,
            "rnode_support_good": rnode_result,
            "bot_launcher_good": bot_launcher_result,
            "http_status_good": web_results.get(
                "http_status_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_app_info_good": web_results.get(
                "http_app_info_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_config_good": web_results.get(
                "http_config_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_db_health_good": web_results.get(
                "http_db_health_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_auth_csrf_good": web_results.get(
                "http_auth_csrf_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_bots_status_good": web_results.get(
                "http_bots_status_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_security_good": web_results.get(
                "http_security_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_interfaces_good": web_results.get(
                "http_interfaces_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_reticulum_instance_good": web_results.get(
                "http_reticulum_instance_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_identities_good": web_results.get(
                "http_identities_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_favourites_good": web_results.get(
                "http_favourites_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_telephone_good": web_results.get(
                "http_telephone_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_plugins_good": web_results.get(
                "http_plugins_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_plugins_trust_good": web_results.get(
                "http_plugins_trust_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_sideband_plugins_good": web_results.get(
                "http_sideband_plugins_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_sideband_config_good": web_results.get(
                "http_sideband_config_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_rrc_hubs_good": web_results.get(
                "http_rrc_hubs_good",
                {"status": "failed", "reason": "missing"},
            ),
            "http_rrc_servers_good": web_results.get(
                "http_rrc_servers_good",
                {"status": "failed", "reason": "missing"},
            ),
            "plugins_runtime_good": plugins_runtime_result,
            "websocket_good": web_results.get(
                "websocket_good",
                {"status": "failed", "reason": "missing"},
            ),
            "websocket_rns_link_good": web_results.get(
                "websocket_rns_link_good",
                {"status": "failed", "reason": "missing"},
            ),
            "bots_lifecycle": {
                "status": "ok" if bots_ok else "failed",
                "reason": bots_reason,
            },
        }

    @property
    def database_path(self):
        return self.current_context.database_path if self.current_context else None

    @property
    def _identity_session_id(self):
        return self.current_context.session_id if self.current_context else 0

    @_identity_session_id.setter
    def _identity_session_id(self, value):
        if self.current_context:
            self.current_context.session_id = value

    def get_public_path(self, filename=""):
        if self.public_dir_override:
            return os.path.join(self.public_dir_override, filename)
        return get_file_path(os.path.join("public", filename))

    @staticmethod
    def _normalize_reticulum_config_dir(config_candidate: str | None) -> str:
        """Normalize Reticulum config candidate to a config directory path."""
        candidate = config_candidate
        if not candidate:
            candidate = (
                getattr(RNS.Reticulum, "configdir", None)
                or os.path.dirname(getattr(RNS.Reticulum, "configpath", "") or "")
                or os.path.expanduser("~/.reticulum")
            )

        candidate = os.path.expanduser(str(candidate))
        # Reticulum's config file is plaintext named "config" (no extension).
        # If a file path is provided, convert it to its parent directory.
        if os.path.basename(candidate) == "config" and not os.path.isdir(candidate):
            return os.path.dirname(candidate) or os.path.expanduser("~/.reticulum")
        return candidate

    def _reticulum_config_file_path(self) -> str:
        return os.path.join(
            self._normalize_reticulum_config_dir(self.reticulum_config_dir),
            "config",
        )

    @staticmethod
    def _write_rns_reticulum_default_config_file(config_path: str) -> str:
        """Write RNS stock default config to config_path; return on-disk text.

        Uses the same template and ConfigObj path as Reticulum.__create_default_config.
        """
        from RNS.vendor.configobj import ConfigObj

        rns_reticulum_mod = importlib.import_module("RNS.Reticulum")
        default_spec = rns_reticulum_mod.__default_rns_config__
        config_dir = os.path.dirname(config_path) or os.path.abspath(".")
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        cfg = ConfigObj(default_spec)
        cfg.filename = config_path
        cfg.write()
        with open(config_path) as f:
            return f.read()

    def backup_database(self, backup_path=None):
        if not self.database:
            raise RuntimeError("Database not initialized")
        return self.database.backup_database(self.storage_path, backup_path)

    def list_database_backups(self):
        if not self.database:
            raise RuntimeError("Database not initialized")
        return self.database.list_auto_backups(self.storage_path)

    def export_database_backup(self, name: str, dest_path: str):
        if not self.database:
            raise RuntimeError("Database not initialized")
        return self.database.copy_auto_backup(self.storage_path, name, dest_path)

    def prepare_for_database_restore(self) -> str | None:
        db_path = self.database_path
        self._teardown_all_contexts_for_reload()
        from meshchatx.src.backend.database.provider import DatabaseProvider

        if DatabaseProvider._instance is not None:
            DatabaseProvider._instance.close_all()
            DatabaseProvider._instance = None
        return db_path

    @staticmethod
    def _schedule_process_restart(delay: float = 1.0) -> None:
        def restart():
            time.sleep(delay)
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                print(f"Failed to restart: {e}")
                os._exit(0)

        threading.Thread(target=restart, daemon=True).start()

    def restore_database(self, backup_path, *, relaunch: bool = False):
        db_path = self.prepare_for_database_restore()
        if not db_path:
            raise RuntimeError("Database path is unknown")
        from meshchatx.src.backend.database import Database

        db = Database(db_path)
        try:
            result = db.restore_database(backup_path)
        finally:
            db.close_all()
        identity_storage_file = os.path.join(os.path.dirname(db_path), "identity")
        main_identity_file = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        if os.path.isfile(identity_storage_file):
            os.makedirs(os.path.dirname(main_identity_file), exist_ok=True)
            shutil.copy2(identity_storage_file, main_identity_file)
        if relaunch:
            self._schedule_process_restart()
        return result

    def auto_recover_database(self, *, relaunch: bool = True) -> dict:
        from meshchatx.src.backend.database.auto_recover import (
            run_auto_database_recover,
        )
        from meshchatx.src.backend.database.schema import DatabaseSchema

        storage = self.storage_path
        if not storage:
            msg = "Storage path is unknown"
            raise RuntimeError(msg)

        def restore_fn(path: str) -> dict:
            return self.restore_database(path, relaunch=relaunch)

        def sqlite_recover_fn() -> dict:
            path = self.database_path
            if not path:
                msg = "Database path is unknown"
                raise RuntimeError(msg)
            from meshchatx.src.backend.database import Database

            db = Database(path)
            return db.run_database_recovery()

        return run_auto_database_recover(
            storage,
            self.database_path,
            DatabaseSchema.LATEST_VERSION,
            restore_fn,
            sqlite_recover_fn=sqlite_recover_fn,
        )

    def _resolve_database_restore_path(self, path: str) -> str | None:
        """Resolve a restore zip under identity snapshots or database-backups only."""
        if not isinstance(path, str) or not path or "\x00" in path:
            return None
        storage = self.storage_path
        if not storage:
            return None
        allowed_roots = [
            os.path.join(storage, "snapshots"),
            os.path.join(storage, "database-backups"),
        ]
        candidates: list[str] = []
        if os.path.isabs(path):
            candidates.append(path)
        else:
            for root in allowed_roots:
                candidates.append(os.path.join(root, path))
                if not path.endswith(".zip"):
                    candidates.append(os.path.join(root, path + ".zip"))
        for candidate in candidates:
            real = os.path.realpath(candidate)
            if not os.path.isfile(real):
                continue
            if any(is_path_within_dir(real, root) for root in allowed_roots):
                return real
        return None

    def reset_password(self):
        """Clear the stored password hash so a new password can be set via the web UI."""
        if self.config.auth_password_hash.get() is not None:
            self.config.auth_password_hash.set(None)
            return True
        return False

    @staticmethod
    def _disable_rnode_interfaces_on_android(config_path: str) -> bool:
        """Disable enabled RNode* interfaces in Reticulum config (Android recovery helper)."""
        if not _is_chaquopy_android():
            return False
        from meshchatx.src.backend.rnode_support import (
            disable_rnode_interfaces_in_config,
        )

        return disable_rnode_interfaces_in_config(config_path, is_android=True)

    def _ensure_reticulum_config(self, materialize: bool = True):
        """Normalize reticulum_config_dir and optionally ensure a config file exists.

        When materialize is true (default), write RNS stock defaults if the file
        is missing or lacks required sections so first Reticulum startup is reliable.

        API handlers that must distinguish a missing file (e.g. raw config GET) pass
        materialize=False to only normalize the directory path.
        """
        config_dir = self._normalize_reticulum_config_dir(self.reticulum_config_dir)
        self.reticulum_config_dir = config_dir
        if not materialize:
            return
        if not getattr(self, "_reticulum_instance_name_startup_repair_done", False):
            self._repair_reticulum_instance_name_corruption()
            self._reticulum_instance_name_startup_repair_done = True
        config_path = os.path.join(config_dir, "config")
        needs_default = not reticulum_config_has_required_sections(config_path)
        if not needs_default:
            repair_unparseable_reticulum_config(
                config_path,
                write_default=self._write_rns_reticulum_default_config_file,
            )
            needs_default = not reticulum_config_has_required_sections(config_path)
        if needs_default:
            if not os.path.isdir(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            self._write_rns_reticulum_default_config_file(config_path)
        try:
            from RNS.vendor.configobj import ConfigObj

            cfg = ConfigObj(config_path)
            if "default_bootstrap_only" in cfg.get("reticulum", {}):
                cfg["reticulum"].pop("default_bootstrap_only", None)
                cfg.write()
        except Exception as exc:
            logger.warning(
                "Failed to scrub default_bootstrap_only from %s: %s",
                config_path,
                exc,
            )
        from meshchatx.src.backend.rnode_support import (
            guard_invalid_rnode_txpower_in_config,
            guard_rnode_interfaces_on_android,
            guard_rnode_interfaces_on_desktop,
            normalize_rnode_tcp_host_in_config,
        )

        normalize_rnode_tcp_host_in_config(config_path)
        guard_rnode_interfaces_on_android(config_path)
        guard_rnode_interfaces_on_desktop(config_path)
        guard_invalid_rnode_txpower_in_config(config_path)
        i2p_support.guard_i2p_interfaces_in_config(config_path)
        ensure_safe_reticulum_runtime_flags(config_path)
        try:
            from meshchatx.src.backend.interface_module_store import (
                ensure_bundled_interface_modules,
            )

            ensure_bundled_interface_modules(config_dir)
        except Exception as exc:
            logger.warning(
                "Failed to sync bundled interface modules into %s: %s",
                config_dir,
                exc,
            )

    def _set_startup_stage(self, stage: str, error: str | None = None) -> None:
        previous = getattr(self, "_startup_stage", None)
        self._startup_stage = stage
        if error is not None:
            self._startup_error = error
        # Same stage can be set from both the network-setup wrapper and
        # setup_identity. Only log transitions to keep console noise down.
        if previous != stage or error is not None:
            print(f"Startup stage: {stage}", flush=True)

    def _mark_network_ready(self) -> None:
        self._network_ready = True
        self._network_degraded = False
        self._ui_ready = True
        self._startup_stage = "ready"
        self._startup_error = None
        self._rns_recovery_actions = []
        self._network_ready_event.set()
        self._schedule_reticulum_signal_handlers()

    def _mark_network_degraded(self, error: str) -> None:
        """Keep HTTP/UI alive when the mesh stack cannot start."""
        self._network_ready = False
        self._network_degraded = True
        self._ui_ready = True
        self._startup_stage = "failed"
        self._startup_error = error
        print(f"Network degraded: {error}", flush=True)

    def _schedule_reticulum_signal_handlers(self) -> None:
        """Install RNS signal handlers on the main asyncio loop when possible."""
        if threading.current_thread() is threading.main_thread():
            _install_reticulum_signal_handlers()
            return
        loop = AsyncUtils.main_loop
        if loop is None or not loop.is_running():
            return
        try:
            loop.call_soon_threadsafe(_install_reticulum_signal_handlers)
        except Exception:
            pass

    def _ensure_sideband_telemetry_loop(self) -> None:
        config = self.sideband_plugin_loader.get_config()
        should_run = bool(config.get("service_plugins_enabled"))
        if should_run and not self._sideband_telemetry_running:
            self._sideband_telemetry_running = True

            def telemetry_job():
                while self._sideband_telemetry_running:
                    try:
                        self.sideband_plugin_loader.update_telemetry()
                    except Exception:
                        pass
                    time.sleep(60)

            self._sideband_telemetry_thread = threading.Thread(
                target=telemetry_job,
                daemon=True,
                name="sideband-plugin-telemetry",
            )
            self._sideband_telemetry_thread.start()
        elif not should_run:
            self._sideband_telemetry_running = False

    def _startup_status_payload(self) -> dict:
        demo_fields = {
            "demo_mode": self.demo_mode,
            "altcha_enabled": self.altcha_enabled,
            "auth_page_hint": self.auth_page_hint,
        }
        if self._startup_stage == "failed" or self._startup_error:
            payload = {
                "status": "failed",
                "stage": "failed",
                "network_ready": False,
                "network_degraded": True,
                "ui_ready": True,
                "listen_host": self.listen_host,
                "listen_port": self.listen_port,
                "https_enabled": self.use_https,
                "is_loopback_bind": _is_loopback_bind_host(self.listen_host),
                "plugins_enabled": self.plugins_enabled,
                **demo_fields,
                **self._landlock_status_dict(),
            }
            if self._startup_error:
                payload["error"] = self._startup_error
            if self._rns_recovery_actions:
                payload["recovery_actions"] = list(self._rns_recovery_actions)
            return payload
        ready = bool(self._network_ready) and bool(
            self.current_context and self.current_context.running,
        )
        stage = "ready" if ready else (self._startup_stage or "starting")
        return {
            "status": "ok" if ready else "starting",
            "stage": stage,
            "network_ready": ready,
            "network_degraded": False,
            "ui_ready": True if ready else bool(self._ui_ready),
            "listen_host": self.listen_host,
            "listen_port": self.listen_port,
            "https_enabled": self.use_https,
            "is_loopback_bind": _is_loopback_bind_host(self.listen_host),
            "plugins_enabled": self.plugins_enabled,
            **demo_fields,
            **self._landlock_status_dict(),
        }

    def wait_until_network_ready(self, timeout: float | None = None) -> bool:
        if (
            self._network_ready
            and self.current_context
            and self.current_context.running
        ):
            return True
        return self._network_ready_event.wait(timeout)

    def start_network_setup_in_background(
        self,
        identity: RNS.Identity | None = None,
    ) -> None:
        pending = identity if identity is not None else self._pending_identity
        if pending is None:
            raise RuntimeError("No identity available for network setup")
        self._pending_identity = pending
        if (
            self._network_ready
            and self.current_context
            and self.current_context.running
        ):
            return
        with self._network_setup_lock:
            if self._network_setup_thread and self._network_setup_thread.is_alive():
                return
            self._set_startup_stage("starting")
            thread = threading.Thread(
                target=self._run_network_setup,
                name="meshchatx-network-setup",
                daemon=True,
            )
            self._network_setup_thread = thread
            thread.start()

    def _run_network_setup(self) -> None:
        identity = self._pending_identity
        if identity is None:
            self._set_startup_stage("failed", "No identity available for network setup")
            return
        try:
            self.setup_identity(identity)
            if self.config is not None and getattr(self, "session_secret_key", None):
                try:
                    self.config.auth_session_secret.set(self.session_secret_key)
                except Exception as exc:
                    print(f"Failed to persist session secret into config: {exc}")
            self._mark_network_ready()
            self._finish_deferred_startup_services()
            print("Network stack ready", flush=True)
            if self.websocket_clients:
                try:
                    AsyncUtils.run_async(
                        self.websocket_broadcast(
                            json.dumps(
                                {
                                    "type": "startup_status",
                                    "status": "ok",
                                    "stage": "ready",
                                    "network_ready": True,
                                },
                            ),
                        ),
                    )
                except Exception:
                    pass
        except Exception as exc:
            traceback.print_exc()
            self._mark_network_degraded(str(exc))
            if self.websocket_clients:
                try:
                    AsyncUtils.run_async(
                        self.websocket_broadcast(
                            json.dumps(
                                {
                                    "type": "startup_status",
                                    "status": "failed",
                                    "stage": "failed",
                                    "network_ready": False,
                                    "network_degraded": True,
                                    "ui_ready": True,
                                    "error": str(exc),
                                },
                            ),
                        ),
                    )
                except Exception:
                    pass

    def setup_identity(self, identity: RNS.Identity):
        identity_hash = identity.hash.hex()

        self.running = True

        # Check if we already have a context for this identity
        if identity_hash in self.contexts:
            identity_storage_dir = os.path.join(
                self.storage_dir,
                "identities",
                identity_hash,
            )
            if not os.path.isdir(identity_storage_dir):
                stale = self.contexts.pop(identity_hash)
                with contextlib.suppress(Exception):
                    stale.teardown()
            else:
                self.current_context = self.contexts[identity_hash]
                if not self.current_context.running:
                    self.current_context.setup()
                self.web_audio_bridge = WebAudioBridge(
                    self.current_context.telephone_manager,
                    self.current_context.config,
                    force_enabled=self.web_audio_required(),
                )
                if self._network_ready:
                    self._finish_deferred_startup_services()
                self._apply_demo_mode_runtime()
                return

        # Initialize Reticulum if not already done
        if not hasattr(self, "reticulum"):
            self._set_startup_stage("rns")
            self._ensure_reticulum_config()
            rns_loglevel = _resolve_rns_loglevel(self._rns_loglevel_cli)
            self.reticulum = _create_reticulum_instance(
                self.reticulum_config_dir,
                loglevel=rns_loglevel,
            )
            _restore_rns_console_logging_after_reticulum_init(self)
            self.page_node_manager.load_nodes()
            self.plugin_manager.set_app(self)

        # Create new context
        self._set_startup_stage("identity")
        context = IdentityContext(identity, self)
        self.contexts[identity_hash] = context
        self.current_context = context
        context.setup()
        self.web_audio_bridge = WebAudioBridge(
            context.telephone_manager,
            context.config,
            force_enabled=self.web_audio_required(),
        )

        for node in self.page_node_manager.nodes.values():
            if node.running and node.destination:
                self._register_local_page_node_announce(node)

        # Link database to memory log handler
        memory_log_handler.set_database(context.database)

        # Wire crash recovery with DB + log handler for adaptive diagnostics
        if hasattr(self, "_crash_recovery") and self._crash_recovery:
            self._crash_recovery.set_database(context.database)
            self._crash_recovery.log_handler = memory_log_handler

        # Start health monitor if not already running
        if not hasattr(self, "_health_monitor") or self._health_monitor is None:
            self._health_monitor = HealthMonitor(
                log_handler=memory_log_handler,
                app=self,
            )
            self._health_monitor.start()

        if self._network_ready:
            self._finish_deferred_startup_services()

        self._apply_demo_mode_runtime()

    def _apply_demo_mode_runtime(self) -> None:
        if not self.demo_mode:
            return
        ctx = self.current_context
        if not ctx or not ctx.config:
            return
        self.plugins_enabled = False
        ctx.config.privacy_mode_enabled.set(True)
        ctx.config.auto_announce_enabled.set(False)
        if self.auth_enabled_initial:
            ctx.config.auth_enabled.set(True)
        if self.auth_enabled and ctx.config.auth_password_hash.get() is None:
            password = demo_auth_password_from_env()
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            ctx.config.auth_password_hash.set(password_hash)

    def _finish_deferred_startup_services(self) -> None:
        """Start non-critical services after network_ready is published."""
        context = self.current_context
        if context is not None:
            try:
                context.setup_deferred_services()
            except Exception as exc:
                print(f"Deferred identity services failed: {exc}", flush=True)
        self._start_deferred_reticulum_services()

    def _start_deferred_reticulum_services(self) -> None:
        if self._reticulum_secondary_started:
            return
        if not hasattr(self, "reticulum"):
            return
        self._reticulum_secondary_started = True
        try:
            self.page_node_manager.start_all()
            for node in self.page_node_manager.nodes.values():
                if node.running and node.destination:
                    self._register_local_page_node_announce(node)
        except Exception as exc:
            print(f"Deferred page node start failed: {exc}", flush=True)
        if self.plugins_enabled:
            try:
                self.plugin_manager.install_bundled_examples()
            except Exception as exc:
                print(f"Bundled plugin sync failed: {exc}", flush=True)
        try:
            self.sideband_plugin_loader.reload()
            self._ensure_sideband_telemetry_loop()
        except Exception as exc:
            print(f"Sideband plugin loader init failed: {exc}")

    def _checkpoint_and_close(self):
        # delegated to database instance
        self.database._checkpoint_and_close()

    def _get_identity_bytes(self) -> bytes:
        return self.identity_manager.get_identity_bytes(self.identity)

    def cleanup_rns_state_for_identity(self, identity_hash):
        if not identity_hash:
            return

        if isinstance(identity_hash, str):
            identity_hash_bytes = bytes.fromhex(identity_hash)
            identity_hash_hex = identity_hash
        else:
            identity_hash_bytes = identity_hash
            identity_hash_hex = identity_hash.hex()

        print(f"Aggressively cleaning up RNS state for identity {identity_hash_hex}")

        # 1. Deregister destinations
        try:
            # We iterate over a copy of the list because we are modifying it
            for destination in list(RNS.Transport.destinations):
                match = False
                # check identity hash
                if hasattr(destination, "identity") and destination.identity:
                    if destination.identity.hash == identity_hash_bytes:
                        match = True

                if match:
                    print(
                        f"Deregistering RNS destination {destination} ({RNS.prettyhexrep(destination.hash)})",
                    )
                    RNS.Transport.deregister_destination(destination)
        except Exception as e:
            print(f"Error while cleaning up RNS destinations: {e}")

        # 2. Teardown active links
        try:
            for link in list(RNS.Transport.active_links):
                match = False
                # check if local identity or destination matches
                if hasattr(link, "destination") and link.destination:
                    if (
                        hasattr(link.destination, "identity")
                        and link.destination.identity
                    ):
                        if link.destination.identity.hash == identity_hash_bytes:
                            match = True

                if match:
                    print(f"Tearing down RNS link {link}")
                    try:
                        link.teardown()
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error while cleaning up RNS links: {e}")

    def _clear_mesh_link_caches(self):
        """Drop process-global mesh links so identity switch cannot reuse sessions."""
        clear_all_cached_links()
        clear_all_nomadnet_cached_links()

    def _drop_auto_resend_locks(self, identity_hash: str | None) -> None:
        """Drop idle auto-resend locks for a torn-down identity."""
        if not identity_hash:
            return
        coord = getattr(self, "_auto_resend_coordinator", None)
        if coord is None:
            return
        with contextlib.suppress(Exception):
            coord.drop_identity(identity_hash)
        canonical = normalize_identity_storage_hash(identity_hash)
        if canonical and canonical != identity_hash:
            with contextlib.suppress(Exception):
                coord.drop_identity(canonical)

    def teardown_identity(self):
        if self.current_context:
            self.running = False
            identity_hash = self.current_context.identity_hash
            self.current_context.teardown()
            if identity_hash in self.contexts:
                del self.contexts[identity_hash]
            self.current_context = None
            # Drop Nomad and RNS links that may have identified as the prior identity.
            self._clear_mesh_link_caches()
            self._drop_auto_resend_locks(identity_hash)
            gc.collect()

    def _teardown_all_contexts_for_reload(self):
        # Stop per-identity long-running services before tearing down contexts.
        for identity_hash in list(self.contexts.keys()):
            ctx = self.contexts.get(identity_hash)
            if ctx is None:
                continue
            bot_handler = getattr(ctx, "bot_handler", None)
            if bot_handler is not None:
                with contextlib.suppress(Exception):
                    bot_handler.stop_all()
            with contextlib.suppress(Exception):
                self.stop_local_propagation_node(context=ctx)

        # Stop page node mesh servers before resetting transport state.
        if hasattr(self, "page_node_manager"):
            with contextlib.suppress(Exception):
                self.page_node_manager.teardown()

        for identity_hash in list(self.contexts.keys()):
            ctx = self.contexts.get(identity_hash)
            if ctx is None:
                continue
            with contextlib.suppress(Exception):
                ctx.teardown()

        dropped_identity_hashes = list(self.contexts.keys())
        self.contexts.clear()
        self.current_context = None
        self.running = False
        # Same drop as teardown_identity. Reload and zip restore must not keep
        # Nomad or RNS Link sessions from the torn-down identities.
        self._clear_mesh_link_caches()
        for identity_hash in dropped_identity_hashes:
            self._drop_auto_resend_locks(identity_hash)
        gc.collect()

    async def _send_rns_reload_status(
        self,
        stage: str,
        message: str,
        *,
        level: str = "info",
        in_progress: bool = True,
    ):
        with contextlib.suppress(Exception):
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "reticulum_reload_status",
                        "stage": stage,
                        "message": message,
                        "level": level,
                        "in_progress": in_progress,
                    },
                ),
            )

    def _force_close_listener(self, listener):
        """Aggressively close a multiprocessing.connection.Listener.

        Calls Listener.close() and additionally drills through the inner
        SocketListener wrapper to close the underlying socket file descriptor.
        Necessary because the rpc_loop thread can retain references to the
        listener that prevent the kernel from releasing abstract AF_UNIX
        addresses on plain close().
        """
        try:
            if hasattr(listener, "close"):
                with contextlib.suppress(Exception):
                    listener.close()
        finally:
            socket_type = getattr(socket, "SocketType", None)
            wrappers = [listener]

            listener_inner = getattr(listener, "_listener", None)
            if listener_inner is not None:
                wrappers.append(listener_inner)

            for wrapper in list(wrappers):
                inner_socket = getattr(wrapper, "_socket", None)
                if inner_socket is not None:
                    wrappers.append(inner_socket)
                plain_socket = getattr(wrapper, "socket", None)
                if plain_socket is not None:
                    wrappers.append(plain_socket)

            for obj in wrappers:
                if socket_type is None or not isinstance(obj, socket_type):
                    continue
                fileno = -1
                try:
                    fileno = obj.fileno()
                except Exception:
                    pass
                with contextlib.suppress(Exception):
                    obj.close()
                if fileno != -1:
                    try:
                        os.close(fileno)
                    except OSError:
                        pass

            for wrapper in wrappers:
                with contextlib.suppress(Exception):
                    if hasattr(wrapper, "_socket"):
                        wrapper._socket = None
                with contextlib.suppress(Exception):
                    if hasattr(wrapper, "socket"):
                        wrapper.socket = None
            with contextlib.suppress(Exception):
                if hasattr(listener, "_listener"):
                    listener._listener = None

    def _force_close_abstract_unix_addr(self, addr) -> bool:
        """Close every socket FD in the current process bound to addr.

        Returns True if any FD was closed. addr is expected to be a string
        starting with a NUL byte (abstract AF_UNIX namespace).
        """
        if not (isinstance(addr, str) and addr.startswith("\0")):
            return False

        target_bytes = addr.encode("utf-8", errors="replace")
        target_no_nul = target_bytes[1:]
        closed_any = False

        try:
            current_process = psutil.Process()
            for conn in current_process.net_connections(kind="unix"):
                try:
                    laddr = getattr(conn, "laddr", None)
                    fd = getattr(conn, "fd", -1)
                    if not laddr or fd in (-1, None):
                        continue

                    if isinstance(laddr, str):
                        laddr_bytes = laddr.encode("utf-8", errors="replace")
                    elif isinstance(laddr, bytes):
                        laddr_bytes = laddr
                    else:
                        continue

                    laddr_no_nul = (
                        laddr_bytes[1:]
                        if laddr_bytes.startswith(b"\0")
                        else laddr_bytes
                    )

                    if (
                        laddr_bytes in (target_bytes, target_no_nul)
                        or laddr_no_nul == target_no_nul
                    ):
                        try:
                            os.close(fd)
                            closed_any = True
                            print(
                                f"Force closed lingering abstract UNIX FD {fd} for {addr[1:]}",
                            )
                        except OSError as fd_err:
                            print(
                                f"Failed to close FD {fd} for {addr[1:]}: {fd_err}",
                            )
                except Exception:
                    pass
        except Exception as e:
            print(f"Error scanning process for abstract UNIX FDs: {e}")

        if closed_any:
            gc.collect()
            time.sleep(0.2)

        return closed_any

    _reload_instance_suffix_re = re.compile(r"-reload-(\d+)-(\d+)$")
    _meshchat_reload_pid_max = 4_194_304
    _meshchat_reload_epoch_min = 1_577_836_800
    _meshchat_reload_epoch_max = 4_102_444_800

    @staticmethod
    def _reset_transport_globals_for_reload() -> None:
        """Clear RNS Transport globals so a new Reticulum can start cleanly.

        Reticulum.exit_handler sets Transport._should_run = False. Upstream
        Transport.start never flips it back, so hot reload must restore it or
        the new jobloop exits immediately and path/link tools stay dead while
        interface RX/TX counters still update.
        """
        RNS.Transport._should_run = True
        if hasattr(RNS.Transport, "jobs_running"):
            RNS.Transport.jobs_running = False
        RNS.Transport.interfaces = []
        RNS.Transport.local_client_interfaces = []
        RNS.Transport.destinations = []
        if hasattr(RNS.Transport, "destinations_map"):
            RNS.Transport.destinations_map = {}
        RNS.Transport.active_links = []
        RNS.Transport.pending_links = []
        RNS.Transport.announce_handlers = []
        RNS.Transport.announce_table = {}
        RNS.Transport.path_table = {}
        RNS.Transport.reverse_table = {}
        RNS.Transport.link_table = {}
        RNS.Transport.held_announces = {}
        RNS.Transport.tunnels = {}
        RNS.Transport.path_requests = {}
        RNS.Transport.path_states = {}
        RNS.Transport.announce_rate_table = {}
        RNS.Transport.control_destinations = []
        RNS.Transport.control_hashes = []
        RNS.Transport.mgmt_destinations = []
        RNS.Transport.mgmt_hashes = []

    @staticmethod
    def _looks_like_meshchat_hot_reload_tail(pid: int, epoch: int) -> bool:
        """Limit repairs to suffixes reload_reticulum actually writes.

        Hot reload uses -reload-{os.getpid()}-{int(time.time())}. Names like
        my-net-reload-peer must not be truncated.
        """
        if pid < 1 or pid > ReticulumMeshChat._meshchat_reload_pid_max:
            return False
        if (
            epoch < ReticulumMeshChat._meshchat_reload_epoch_min
            or epoch > ReticulumMeshChat._meshchat_reload_epoch_max
        ):
            return False
        return True

    @staticmethod
    def _strip_reload_instance_suffix(name):
        """Remove stacked MeshChat hot-reload tails only (validated pid + unix time)."""
        if not isinstance(name, str):
            return None
        out = name.strip()
        if not out:
            return None
        while True:
            m = ReticulumMeshChat._reload_instance_suffix_re.search(out)
            if not m or m.end() != len(out):
                break
            try:
                pid = int(m.group(1))
                epoch = int(m.group(2))
            except ValueError:
                break
            if not ReticulumMeshChat._looks_like_meshchat_hot_reload_tail(pid, epoch):
                break
            out = out[: m.start()].strip()
        return out or None

    def _read_reticulum_instance_name(self):
        """Return current Reticulum instance_name from config or None."""
        config_dir = self._normalize_reticulum_config_dir(
            getattr(self, "reticulum_config_dir", None),
        )
        config_path = os.path.join(config_dir, "config")
        if not os.path.isfile(config_path):
            return None

        cp = configparser.ConfigParser()
        try:
            cp.read(config_path)
        except configparser.Error:
            return None
        if not cp.has_section("reticulum"):
            return None
        return cp.get("reticulum", "instance_name", fallback=None)

    def _repair_reticulum_instance_name_corruption(self):
        """Rewrite persisted instance_name if hot-reload suffixes were left on disk."""
        raw = self._read_reticulum_instance_name()
        if not raw:
            return
        cleaned = ReticulumMeshChat._strip_reload_instance_suffix(raw)
        if cleaned == raw or cleaned is None:
            return
        self._write_reticulum_instance_name(cleaned)

    def _write_reticulum_instance_name(self, instance_name):
        """Persist a Reticulum instance_name value into the config."""
        config_dir = self._normalize_reticulum_config_dir(
            getattr(self, "reticulum_config_dir", None),
        )
        config_path = os.path.join(config_dir, "config")
        cp = configparser.ConfigParser()
        try:
            cp.read(config_path)
        except configparser.Error:
            cp = configparser.ConfigParser()
        if not cp.has_section("reticulum"):
            cp.add_section("reticulum")
        cp.set("reticulum", "instance_name", instance_name)
        with open(config_path, "w", encoding="utf-8") as f:
            cp.write(f)

    async def reload_reticulum(self):
        print("Hot reloading Reticulum stack...")
        # Keep reference to old reticulum instance for cleanup
        old_reticulum = getattr(self, "reticulum", None)
        identity_to_restore = self.identity
        identity_hashes = []
        for ctx in list(self.contexts.values()):
            with contextlib.suppress(Exception):
                identity_hashes.append(ctx.identity.hash)
        if not identity_hashes:
            identity_hash = getattr(identity_to_restore, "hash", None)
            if identity_hash:
                identity_hashes.append(identity_hash)

        try:
            if identity_to_restore is None:
                raise RuntimeError(
                    "Cannot reload Reticulum without an active identity context.",
                )
            await self._send_rns_reload_status(
                "starting",
                "Reloading RNS stack...",
            )

            # Signal background loops to exit
            self._identity_session_id += 1
            self._network_ready = False

            await self._send_rns_reload_status(
                "stopping-services",
                "Stopping bots and mesh services across identities...",
            )
            self._teardown_all_contexts_for_reload()

            # Give loops a moment to finish
            await asyncio.sleep(2)

            await self._send_rns_reload_status(
                "deregistering",
                "Deregistering destinations and active links...",
            )
            for identity_hash in identity_hashes:
                self.cleanup_rns_state_for_identity(identity_hash)

            # Close RNS instance first to let it detach interfaces naturally
            await self._send_rns_reload_status(
                "detaching",
                "Detaching interfaces and shutting down Reticulum...",
            )
            try:
                # Use class method to ensure all instances are cleaned up if any
                RNS.Reticulum.exit_handler()
            except Exception as e:
                print(f"Warning during RNS exit: {e}")

            # Aggressively close RNS interfaces to release sockets if they didn't close
            try:
                interfaces = []
                if hasattr(RNS.Transport, "interfaces"):
                    interfaces.extend(RNS.Transport.interfaces)
                if hasattr(RNS.Transport, "local_client_interfaces"):
                    interfaces.extend(RNS.Transport.local_client_interfaces)

                for interface in interfaces:
                    try:
                        # Generic socketserver shutdown
                        if hasattr(interface, "server") and interface.server:
                            try:
                                interface.server.shutdown()
                                interface.server.server_close()
                            except Exception:
                                pass

                        # AutoInterface specific
                        if hasattr(interface, "interface_servers"):
                            for server in interface.interface_servers.values():
                                try:
                                    server.shutdown()
                                    server.server_close()
                                except Exception:
                                    pass

                        # For LocalServerInterface which Reticulum doesn't close properly
                        if hasattr(interface, "server") and interface.server:
                            try:
                                interface.server.shutdown()
                                interface.server.server_close()
                            except Exception:
                                pass

                        # TCPClientInterface/etc
                        if hasattr(interface, "socket") and interface.socket:
                            try:
                                # Check if socket is still valid before shutdown
                                if (
                                    hasattr(interface.socket, "fileno")
                                    and interface.socket.fileno() != -1
                                ):
                                    try:
                                        interface.socket.shutdown(socket.SHUT_RDWR)
                                    except Exception:
                                        pass
                                    try:
                                        interface.socket.close()
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        interface.detach()
                        interface.detached = True
                    except Exception as e:
                        print(f"Warning closing interface during reload: {e}")
            except Exception as e:
                print(f"Warning during aggressive interface cleanup: {e}")

            if old_reticulum:
                rpc_listener_names = [
                    "rpc_listener",
                    "_Reticulum__rpc_listener",
                    "_rpc_listener",
                ]
                for attr_name in rpc_listener_names:
                    if hasattr(old_reticulum, attr_name):
                        listener = getattr(old_reticulum, attr_name)
                        if listener:
                            try:
                                print(
                                    f"Forcing closure of RPC listener in {attr_name}...",
                                )
                                self._force_close_listener(listener)
                                setattr(old_reticulum, attr_name, None)
                            except Exception as e:
                                print(f"Warning closing RPC listener {attr_name}: {e}")

            # Clear RNS singleton and internal state to allow re-initialization
            try:
                # Reticulum uses private variables for singleton and state control
                # We need to clear them so we can create a new instance
                if hasattr(RNS.Reticulum, "_Reticulum__instance"):
                    # Keep the instance object until we're done waiting for sockets.
                    # Some Reticulum background workers still consult get_instance().
                    pass
                if hasattr(RNS.Reticulum, "_Reticulum__exit_handler_ran"):
                    RNS.Reticulum._Reticulum__exit_handler_ran = False
                if hasattr(RNS.Reticulum, "_Reticulum__interface_detach_ran"):
                    RNS.Reticulum._Reticulum__interface_detach_ran = False

                self._reset_transport_globals_for_reload()
                clear_all_cached_links()
                clear_all_nomadnet_cached_links()

                # Clear Identity globals
                RNS.Identity.known_destinations = {}
                RNS.Identity.known_ratchets = {}

                # Unregister old exit handlers from atexit if possible
                try:
                    # Reticulum uses a staticmethod exit_handler
                    atexit.unregister(RNS.Reticulum.exit_handler)
                except Exception:
                    pass

            except Exception as e:
                print(f"Warning clearing RNS state: {e}")

            # Remove reticulum instance from self
            if hasattr(self, "reticulum"):
                del self.reticulum

            print("Waiting for ports to settle...")
            await asyncio.sleep(4)

            # Detect RPC type from reticulum instance if possible, otherwise default to both
            rpc_addrs = []
            if old_reticulum:
                if hasattr(old_reticulum, "rpc_addr") and old_reticulum.rpc_addr:
                    rpc_addrs.append(
                        (
                            old_reticulum.rpc_addr,
                            getattr(old_reticulum, "rpc_type", "AF_INET"),
                        ),
                    )

            # Also check the config file for ports
            try:
                config_dir = self._normalize_reticulum_config_dir(
                    getattr(self, "reticulum_config_dir", None),
                )
                config_path = os.path.join(config_dir, "config")
                if os.path.isfile(config_path):
                    cp = configparser.ConfigParser()
                    try:
                        cp.read(config_path)
                    except configparser.Error:
                        pass
                    else:
                        if cp.has_section("reticulum"):
                            rpc_port = cp.getint(
                                "reticulum",
                                "rpc_port",
                                fallback=37429,
                            )
                            rpc_bind = cp.get(
                                "reticulum",
                                "rpc_bind",
                                fallback="127.0.0.1",
                            )
                            shared_port = cp.getint(
                                "reticulum",
                                "shared_instance_port",
                                fallback=37428,
                            )
                            shared_bind = cp.get(
                                "reticulum",
                                "shared_instance_bind",
                                fallback="127.0.0.1",
                            )

                            # Only add if not already there
                            if not any(
                                addr == (rpc_bind, rpc_port) for addr, _ in rpc_addrs
                            ):
                                rpc_addrs.append(((rpc_bind, rpc_port), "AF_INET"))
                            if not any(
                                addr == (shared_bind, shared_port)
                                for addr, _ in rpc_addrs
                            ):
                                rpc_addrs.append(
                                    ((shared_bind, shared_port), "AF_INET"),
                                )
            except Exception as e:
                print(f"Warning reading Reticulum config for ports: {e}")

            if not rpc_addrs:
                rpc_addrs.append((("127.0.0.1", 37429), "AF_INET"))
                rpc_addrs.append((("127.0.0.1", 37428), "AF_INET"))

            abstract_unix_addr_in_use_after_wait = False
            reload_probe_attempts = 3
            for i in range(reload_probe_attempts):
                all_free = True
                for addr, family_str in rpc_addrs:
                    try:
                        family = (
                            socket.AF_INET
                            if family_str == "AF_INET"
                            else socket.AF_UNIX
                        )
                        s = socket.socket(family, socket.SOCK_STREAM)
                        s.settimeout(0.5)
                        try:
                            # Use SO_REUSEADDR to check if we can actually bind
                            if family == socket.AF_INET:
                                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            s.bind(addr)
                            s.close()
                        except OSError:
                            addr_display = addr
                            if (
                                family == socket.AF_UNIX
                                and isinstance(addr, str)
                                and addr.startswith("\0")
                            ):
                                addr_display = addr[1:] + " (abstract)"

                            print(
                                f"RPC addr {addr_display} still in use... (attempt {i + 1}/{reload_probe_attempts})",
                            )
                            s.close()
                            is_abstract_unix_addr = (
                                family == socket.AF_UNIX
                                and isinstance(addr, str)
                                and addr.startswith("\0")
                            )
                            if is_abstract_unix_addr:
                                released = False
                                if self._force_close_abstract_unix_addr(addr):
                                    try:
                                        s2 = socket.socket(
                                            socket.AF_UNIX,
                                            socket.SOCK_STREAM,
                                        )
                                        try:
                                            s2.bind(addr)
                                            s2.close()
                                            print(
                                                f"Released abstract RPC addr {addr_display} from this process.",
                                            )
                                            released = True
                                        except OSError:
                                            s2.close()
                                    except Exception:
                                        pass

                                if released:
                                    continue

                                all_free = False
                                continue

                            all_free = False

                            # If we are stuck, try to force close the connection manually
                            if i > 1:
                                try:
                                    current_process = psutil.Process()
                                    # We use kind='all' to catch both TCP and UNIX sockets
                                    for conn in current_process.net_connections(
                                        kind="all",
                                    ):
                                        try:
                                            match = False
                                            if conn.laddr:
                                                if (
                                                    family_str == "AF_INET"
                                                    and isinstance(conn.laddr, tuple)
                                                ):
                                                    # Match IP and port for IPv4
                                                    if conn.laddr.port == addr[1] and (
                                                        conn.laddr.ip == addr[0]
                                                        or addr[0] == "0.0.0.0"
                                                    ):
                                                        match = True
                                                elif family_str == "AF_UNIX":
                                                    # Match path for UNIX sockets, including abstract
                                                    # Psutil sometimes returns abstract addresses as strings or bytes,
                                                    # with or without the leading null byte.
                                                    laddr = conn.laddr

                                                    # Normalize both to bytes for comparison
                                                    target_addr = (
                                                        addr
                                                        if isinstance(addr, bytes)
                                                        else addr.encode()
                                                        if isinstance(addr, str)
                                                        else b""
                                                    )
                                                    current_laddr = (
                                                        laddr
                                                        if isinstance(laddr, bytes)
                                                        else laddr.encode()
                                                        if isinstance(laddr, str)
                                                        else b""
                                                    )

                                                    if (
                                                        current_laddr == target_addr
                                                        or (
                                                            target_addr.startswith(
                                                                b"\0",
                                                            )
                                                            and current_laddr
                                                            == target_addr[1:]
                                                        )
                                                        or (
                                                            current_laddr.startswith(
                                                                b"\0",
                                                            )
                                                            and target_addr
                                                            == current_laddr[1:]
                                                        )
                                                    ):
                                                        match = True
                                                    elif (
                                                        target_addr in current_laddr
                                                        or current_laddr in target_addr
                                                    ):
                                                        # Last resort: partial match
                                                        if (
                                                            len(target_addr) > 5
                                                            and len(current_laddr) > 5
                                                        ):
                                                            match = True

                                            if match:
                                                # If we found a match, force close the file descriptor
                                                # to tell the OS to release the socket immediately.
                                                status_str = getattr(
                                                    conn,
                                                    "status",
                                                    "UNKNOWN",
                                                )
                                                print(
                                                    f"Force closing lingering {family_str} connection {conn.laddr} (status: {status_str})",
                                                )

                                                try:
                                                    if (
                                                        hasattr(conn, "fd")
                                                        and conn.fd != -1
                                                    ):
                                                        try:
                                                            os.close(conn.fd)
                                                        except Exception as fd_err:
                                                            print(
                                                                f"Failed to close FD {getattr(conn, 'fd', 'N/A')}: {fd_err}",
                                                            )
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                except Exception as e:
                                    print(
                                        f"Error during manual RPC connection kill: {e}",
                                    )

                            break
                    except Exception as e:
                        print(f"Error checking RPC addr {addr}: {e}")

                if all_free:
                    print("All RNS ports/sockets are free.")
                    break

                await asyncio.sleep(1)

            if not all_free:
                await asyncio.sleep(2)
                for addr, family_str in rpc_addrs:
                    if (
                        family_str == "AF_UNIX"
                        and isinstance(addr, str)
                        and addr.startswith("\0")
                    ):
                        with contextlib.suppress(Exception):
                            self._force_close_abstract_unix_addr(addr)

                last_check_all_free = True
                for addr, family_str in rpc_addrs:
                    try:
                        family = (
                            socket.AF_INET
                            if family_str == "AF_INET"
                            else socket.AF_UNIX
                        )
                        s = socket.socket(family, socket.SOCK_STREAM)
                        try:
                            s.bind(addr)
                            s.close()
                        except OSError:
                            s.close()
                            is_abstract = (
                                family == socket.AF_UNIX
                                and isinstance(addr, str)
                                and addr.startswith("\0")
                            )
                            if is_abstract:
                                abstract_unix_addr_in_use_after_wait = True
                                continue
                            last_check_all_free = False
                            break
                        except Exception:
                            pass
                    except Exception:
                        pass

                if not last_check_all_free:
                    raise OSError(
                        "Timeout waiting for RNS ports to be released. Cannot restart.",
                    )
                print("RNS ports finally free after last-second check.")

            gc.collect()

            if hasattr(RNS.Reticulum, "_Reticulum__instance"):
                RNS.Reticulum._Reticulum__instance = None

            switched_instance_name = None
            instance_restore_name = None
            if abstract_unix_addr_in_use_after_wait:
                stored_instance_name = self._read_reticulum_instance_name()
                stable_base = ReticulumMeshChat._strip_reload_instance_suffix(
                    stored_instance_name,
                )
                instance_restore_name = (
                    stable_base if stable_base is not None else "default"
                )
                switched_instance_name = (
                    f"{instance_restore_name}-reload-{os.getpid()}-{int(time.time())}"
                )
                self._write_reticulum_instance_name(switched_instance_name)
                print(
                    "Abstract UNIX RPC address remained busy. "
                    f"Retrying with temporary instance_name={switched_instance_name}",
                )

            self.running = True
            await self._send_rns_reload_status(
                "starting-services",
                "Starting identity services again...",
            )
            try:
                self.setup_identity(identity_to_restore)
            finally:
                if switched_instance_name:
                    self._write_reticulum_instance_name(instance_restore_name)
            self._mark_network_ready()
            self._finish_deferred_startup_services()
            await self._send_rns_reload_status(
                "done",
                "RNS reload complete.",
                level="success",
                in_progress=False,
            )

            return True
        except Exception as e:
            print(f"Hot reload failed: {e}")

            traceback.print_exc()
            await self._send_rns_reload_status(
                "failed",
                f"RNS reload failed: {e!s}",
                level="error",
                in_progress=False,
            )

            # Try to recover if possible without wiping storage.
            if not hasattr(self, "reticulum") and identity_to_restore is not None:
                try:
                    self.setup_identity(identity_to_restore)
                    self._mark_network_ready()
                    self._finish_deferred_startup_services()
                    return False
                except Exception as recover_exc:
                    self._mark_network_degraded(
                        f"RNS reload failed and recovery failed: {recover_exc}",
                    )
            else:
                self._mark_network_degraded(f"RNS reload failed: {e}")

            return False

    async def hotswap_identity(self, identity_hash, keep_alive=False):
        async with self._identity_hotswap_lock:
            return await self._hotswap_identity_locked(
                identity_hash,
                keep_alive=keep_alive,
            )

    async def _hotswap_identity_locked(self, identity_hash, keep_alive=False):
        old_identity = self.identity

        main_identity_file = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        backup_identity_file = main_identity_file + ".bak"
        backup_created = False

        try:
            canonical = normalize_identity_storage_hash(identity_hash)
            if not canonical:
                raise ValueError("Invalid identity hash")
            # load the new identity
            identities_root = os.path.join(self.storage_dir, "identities")
            identity_dir = os.path.join(identities_root, canonical)
            identity_file = os.path.join(identity_dir, "identity")
            if not is_path_within_dir(identity_dir, identities_root):
                raise ValueError("Invalid identity hash")
            if not os.path.exists(identity_file):
                raise ValueError("Identity file not found")

            # Validate that the identity file can be loaded
            new_identity = RNS.Identity.from_file(identity_file)
            if not new_identity:
                raise ValueError("Identity file corrupted or invalid")

            # 1. Backup current identity file
            if os.path.exists(main_identity_file):
                shutil.copy2(main_identity_file, backup_identity_file)
                backup_created = True

            # 2. teardown old identity if not keeping alive
            if not keep_alive:
                self.teardown_identity()
                # Give a moment for destinations to clear from transport
                await asyncio.sleep(2)
            else:
                # Even when keeping the old context alive, never reuse mesh links
                # that may already be identified as the prior identity.
                self._clear_mesh_link_caches()

            # 3. update main identity file
            shutil.copy2(identity_file, main_identity_file)

            # 4. setup new identity
            self.running = True
            # setup_identity initializes context if needed and sets it as current
            self.setup_identity(new_identity)
            try:
                if getattr(self, "bug_report_manager", None) is not None:
                    self.bug_report_manager.on_identity_switch()
            except Exception:
                pass

            # 5. broadcast update to clients
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "identity_switched",
                        "identity_hash": canonical,
                        "display_name": (
                            self.config.display_name.get()
                            if hasattr(self, "config")
                            else "Unknown"
                        ),
                        "requires_reauth": bool(self.auth_enabled),
                    },
                ),
            )

            # Clean up backup on success
            if backup_created and os.path.exists(backup_identity_file):
                os.remove(backup_identity_file)

            return True
        except Exception as e:
            print(f"Hotswap failed: {e}")
            traceback.print_exc()

            # RECOVERY: Try to switch back to last identity
            try:
                print("Attempting to restore previous identity...")
                if backup_created and os.path.exists(backup_identity_file):
                    shutil.copy2(backup_identity_file, main_identity_file)
                    os.remove(backup_identity_file)

                self.running = True
                if old_identity:
                    self.setup_identity(old_identity)
            except Exception as recovery_err:
                print(f"Recovery failed: {recovery_err}")
                traceback.print_exc()

                # FINAL FAILSAFE: Create a brand new identity
                try:
                    print(
                        "CRITICAL: Restoration of previous identity failed. Creating a brand new emergency identity...",
                    )
                    new_id_data = self.create_identity(
                        display_name="Emergency Recovery",
                    )
                    new_id_hash = new_id_data["hash"]

                    # Try to load the newly created identity
                    emergency_identity_file = os.path.join(
                        self.storage_dir,
                        "identities",
                        new_id_hash,
                        "identity",
                    )
                    emergency_id = RNS.Identity.from_file(emergency_identity_file)

                    if emergency_id:
                        # Copy to main identity file
                        shutil.copy2(emergency_identity_file, main_identity_file)
                        self.running = True
                        self.setup_identity(emergency_id)
                        print(f"Emergency identity created and loaded: {new_id_hash}")
                    else:
                        raise RuntimeError(
                            "Failed to load newly created emergency identity",
                        )

                except Exception as final_err:
                    print(
                        f"ULTIMATE FAILURE: Could not even create emergency identity: {final_err}",
                    )
                    traceback.print_exc()

            return False

    def backup_identity(self):
        return self.identity_manager.backup_identity(self.identity)

    def backup_identity_base32(self) -> str:
        return self.identity_manager.backup_identity_base32(self.identity)

    def list_identities(self):
        return self.identity_manager.list_identities(
            self.identity.hash.hex()
            if hasattr(self, "identity") and self.identity
            else None,
        )

    def create_identity(self, display_name=None):
        return self.identity_manager.create_identity(display_name)

    def _evict_cached_identity_context(self, identity_hash: str) -> None:
        canonical = normalize_identity_storage_hash(identity_hash)
        if not canonical:
            return
        ctx = self.contexts.pop(canonical, None)
        if ctx is not None:
            with contextlib.suppress(Exception):
                ctx.teardown()
        self._propagation_sync_metrics.pop(canonical, None)
        self._drop_auto_resend_locks(canonical)

    def delete_identity(self, identity_hash):
        current_hash = (
            self.identity.hash.hex()
            if hasattr(self, "identity") and self.identity
            else None
        )
        deleted = self.identity_manager.delete_identity(identity_hash, current_hash)
        if deleted:
            self._evict_cached_identity_context(identity_hash)
        return deleted

    def restore_identity_from_bytes(
        self,
        identity_bytes: bytes,
        display_name: str | None = None,
    ):
        return self.identity_manager.restore_identity_from_bytes(
            identity_bytes,
            display_name=display_name,
        )

    def restore_identity_from_base32(
        self,
        base32_value: str,
        display_name: str | None = None,
    ):
        return self.identity_manager.restore_identity_from_base32(
            base32_value,
            display_name=display_name,
        )

    def update_identity_metadata_cache(self):
        if not hasattr(self, "identity") or not self.identity:
            return

        identity_hash = self.identity.hash.hex()
        metadata = {
            "display_name": self.config.display_name.get(),
            "icon_name": self.config.lxmf_user_icon_name.get(),
            "icon_foreground_colour": self.config.lxmf_user_icon_foreground_colour.get(),
            "icon_background_colour": self.config.lxmf_user_icon_background_colour.get(),
            "lxmf_address": self.config.lxmf_address_hash.get(),
            "lxst_address": self.config.lxst_address_hash.get(),
        }
        self.identity_manager.update_metadata_cache(identity_hash, metadata)

    def _run_startup_auto_recovery(self):
        try:
            self.database.initialize()
            print("Attempting SQLite auto recovery on startup...")
            actions = []
            actions.append(
                {
                    "step": "wal_checkpoint",
                    "result": self.database.provider.checkpoint(),
                },
            )
            actions.append(
                {
                    "step": "integrity_check",
                    "result": self.database.provider.integrity_check(),
                },
            )
            self.database.provider.vacuum()
            self.database._tune_sqlite_pragmas()
            actions.append(
                {
                    "step": "quick_check_after",
                    "result": self.database.provider.quick_check(),
                },
            )
            print(f"Auto recovery completed: {actions}")
        finally:
            try:
                self.database.close_all()
            except Exception as e:
                print(f"Failed to close database during recovery: {e}")

    # gets app version from the synchronized Python version helper
    @staticmethod
    def get_app_version() -> str:
        return app_version

    @staticmethod
    def get_build_meta() -> dict:
        """Baked git commit / channel from meshchatx.src.build_meta."""
        try:
            from meshchatx.src import build_meta as _build_meta

            return dict(_build_meta.as_dict(app_version))
        except Exception:
            return {
                "git_commit": "",
                "git_commit_short": "",
                "build_channel": "local",
                "is_dev_build": False,
                "display_version": app_version,
            }

    def _api_reticulum_config_path(self) -> str | None:
        r = getattr(self, "reticulum", None)
        if r is not None:
            p = getattr(r, "configpath", None)
            if p:
                return str(p)
        rd = self._normalize_reticulum_config_dir(
            getattr(self, "reticulum_config_dir", None),
        )
        if rd:
            return os.path.join(rd, "config")
        return None

    @staticmethod
    def get_package_version(package_name: str, default: str = "unknown") -> str:
        """Resolve an installed distribution version for About /app/info.

        cx_Freeze and similar bundles often omit .dist-info; fall back to module
        attributes and known submodule layouts (e.g. websockets.version).
        """
        try:
            from packaging.utils import canonicalize_name as _canonicalize_name
        except Exception:

            def _canonicalize_name(name: str) -> str:
                return str(name).strip().lower().replace("_", "-")

        def _from_metadata(dist_name: str) -> str | None:
            for candidate in dict.fromkeys((dist_name, _canonicalize_name(dist_name))):
                try:
                    v = importlib.metadata.version(candidate)
                    if v:
                        return str(v)
                except Exception:
                    pass
                try:
                    v = importlib.metadata.distribution(candidate).version
                    if v:
                        return str(v)
                except Exception:
                    pass
            return None

        resolved = _from_metadata(package_name)
        if resolved:
            return resolved

        module_name = package_name.replace("-", "_")
        top_level = module_name.split(".")[0]

        try:
            for dist_name in importlib.metadata.packages_distributions().get(
                top_level,
                (),
            ):
                resolved = _from_metadata(dist_name)
                if resolved:
                    return resolved
        except Exception:
            pass

        try:
            module = importlib.import_module(module_name)
            ver = getattr(module, "__version__", None)
            if ver:
                return str(ver)
        except Exception:
            pass

        if top_level == "websockets":
            try:
                from websockets.version import version as websockets_semver

                if websockets_semver:
                    return str(websockets_semver)
            except Exception:
                pass

        if top_level == "lxmfy":
            try:
                vmod = importlib.import_module("lxmfy.__version__")
                ver = getattr(vmod, "__version__", None)
                if ver:
                    return str(ver)
            except Exception:
                pass

        if top_level == "rns_filesync":
            try:
                module = importlib.import_module("rns_filesync")
                ver = getattr(module, "__version__", None)
                if ver:
                    return str(ver)
            except Exception:
                pass

        embedded_specs: dict[str, tuple[str, str]] = {
            "aiohttp": ("aiohttp", "__version__"),
            "aiohttp-session": ("aiohttp_session", "__version__"),
            "cryptography": ("cryptography", "__version__"),
            "psutil": ("psutil", "__version__"),
            "websockets": ("websockets", "__version__"),
            "bcrypt": ("bcrypt", "__version__"),
            "ply": ("ply", "__version__"),
            "lxmfy": ("lxmfy", "__version__"),
            "rns-filesync": ("rns_filesync", "__version__"),
            "rns_filesync": ("rns_filesync", "__version__"),
        }
        if package_name in embedded_specs:
            mod_name, attr = embedded_specs[package_name]
            try:
                module = importlib.import_module(mod_name)
                ver = getattr(module, attr, None)
                if ver:
                    return str(ver)
            except Exception:
                pass
            if package_name == "ply":
                try:
                    lex = importlib.import_module("ply.lex")
                    ver = getattr(lex, "VERSION", None)
                    if ver:
                        return str(ver)
                except Exception:
                    pass

        return default

    @staticmethod
    def parse_discovery_patterns(value):
        if value is None:
            return []
        if isinstance(value, str):
            value = value.replace("\n", ",")
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, (list, tuple)):
            return [str(part).strip() for part in value if str(part).strip()]
        text_value = str(value).strip()
        return [text_value] if text_value else []

    @staticmethod
    def sanitize_discovery_patterns(
        value,
        max_patterns: int = 128,
        max_pattern_length: int = 128,
    ):
        sanitized = []
        seen = set()
        for pattern in ReticulumMeshChat.parse_discovery_patterns(value):
            cleaned = (
                pattern.replace("\r", "").replace("\n", "").replace(",", "").strip()
            )
            if not cleaned:
                continue
            cleaned = "".join(ch for ch in cleaned if ch.isprintable()).strip()
            if not cleaned:
                continue
            if len(cleaned) > max_pattern_length:
                cleaned = cleaned[:max_pattern_length]
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            sanitized.append(cleaned)
            if len(sanitized) >= max_patterns:
                break
        return sanitized

    @staticmethod
    def _reticulum_yes_no_preference(value, *, default):
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("false", "no", "0", "n", "off"):
            return False
        if s in ("true", "yes", "1", "y", "on"):
            return True
        return default

    @staticmethod
    def _bootstrap_only_request_yes_no(value):
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        s = str(value).strip().lower()
        if s in ("true", "yes", "1", "y", "on"):
            return "yes"
        if s in ("false", "no", "0", "n", "off"):
            return "no"
        return None

    @staticmethod
    def apply_bootstrap_only_to_interface(
        interface_details,
        data,
        default_enabled,
        *,
        updating_existing=False,
    ):
        if "bootstrap_only" in data:
            yn = ReticulumMeshChat._bootstrap_only_request_yes_no(
                data.get("bootstrap_only"),
            )
            if yn == "yes":
                interface_details["bootstrap_only"] = "yes"
            elif yn == "no":
                interface_details["bootstrap_only"] = "no"
            else:
                interface_details.pop("bootstrap_only", None)
            return
        if updating_existing:
            return
        if default_enabled:
            interface_details["bootstrap_only"] = "yes"
        else:
            interface_details.pop("bootstrap_only", None)

    @staticmethod
    def _to_jsonable(obj):
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, dict):
            return {k: ReticulumMeshChat._to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [ReticulumMeshChat._to_jsonable(v) for v in obj]
        return obj

    def _get_interface_stats_payload(self) -> dict:
        empty: dict = {"interfaces": []}
        reticulum = getattr(self, "reticulum", None)
        if not reticulum:
            return empty
        try:
            raw = reticulum.get_interface_stats()
        except Exception as exc:
            logger.warning("Failed to get interface stats: %s", exc)
            return empty
        if not isinstance(raw, dict):
            return empty
        payload = self._to_jsonable(raw)
        for interface in payload.get("interfaces") or []:
            if isinstance(interface, dict) and "short_name" in interface:
                interface["interface_name"] = interface["short_name"]
        return payload

    @staticmethod
    def discovery_filter_candidates(interface):
        if not isinstance(interface, dict):
            return [str(interface)]
        candidates = []
        for key in (
            "name",
            "type",
            "reachable_on",
            "target_host",
            "remote",
            "listen_ip",
            "port",
            "target_port",
            "listen_port",
            "discovery_hash",
            "transport_id",
            "network_id",
            "network_name",
            "ifac_netname",
        ):
            value = interface.get(key)
            if value is not None and value != "":
                candidates.append(str(value))

        host = (
            interface.get("reachable_on")
            or interface.get("target_host")
            or interface.get("remote")
            or interface.get("listen_ip")
        )
        port = (
            interface.get("port")
            or interface.get("target_port")
            or interface.get("listen_port")
        )
        if host and port:
            candidates.append(f"{host}:{port}")
        return candidates

    @staticmethod
    def matches_discovery_pattern(patterns, interface):
        if not patterns:
            return False
        candidates = [
            value.lower()
            for value in ReticulumMeshChat.discovery_filter_candidates(interface)
        ]
        for pattern in patterns:
            normalized_pattern = str(pattern).lower()
            for candidate in candidates:
                if fnmatch.fnmatchcase(candidate, normalized_pattern):
                    return True
        return False

    @staticmethod
    def normalize_discovered_ifac_fields(interfaces):
        """Surface IFAC fields from discovery announces in a frontend-friendly shape.

        RNS publishes IFAC values in discovered interface dicts as
        ifac_netname and ifac_netkey (when the publishing interface
        sets publish_ifac = yes). The Reticulum config file uses
        network_name / passphrase instead. This helper keeps the raw
        RNS keys for backwards compatibility but also exposes the canonical
        config-style aliases (network_name and passphrase) and ensures
        the optional config_entry blob is always a string when present.

        Returns the list with new keys added; missing values become None
        so the frontend can render placeholders consistently.
        """
        if not isinstance(interfaces, list):
            return interfaces
        normalized = []
        for entry in interfaces:
            if not isinstance(entry, dict):
                normalized.append(entry)
                continue
            updated = dict(entry)

            netname = updated.get("ifac_netname")
            netkey = updated.get("ifac_netkey")
            config_entry = updated.get("config_entry")

            if isinstance(netname, bytes):
                try:
                    netname = netname.decode("utf-8")
                except Exception:
                    netname = netname.hex()
            if isinstance(netkey, bytes):
                try:
                    netkey = netkey.decode("utf-8")
                except Exception:
                    netkey = netkey.hex()
            if isinstance(config_entry, bytes):
                try:
                    config_entry = config_entry.decode("utf-8")
                except Exception:
                    config_entry = None

            updated["ifac_netname"] = netname or None
            updated["ifac_netkey"] = netkey or None
            updated["config_entry"] = config_entry or None
            updated["network_name"] = updated["ifac_netname"]
            updated["passphrase"] = updated["ifac_netkey"]
            updated["publish_ifac"] = bool(
                updated["ifac_netname"] or updated["ifac_netkey"],
            )
            normalized.append(updated)
        return normalized

    @staticmethod
    def filter_discovered_interfaces(
        interfaces,
        whitelist_patterns,
        blacklist_patterns,
    ):
        if not isinstance(interfaces, list):
            return interfaces
        whitelist = ReticulumMeshChat.sanitize_discovery_patterns(whitelist_patterns)
        blacklist = ReticulumMeshChat.sanitize_discovery_patterns(blacklist_patterns)
        return [
            interface
            for interface in interfaces
            if (
                (
                    not whitelist
                    or ReticulumMeshChat.matches_discovery_pattern(whitelist, interface)
                )
                and not ReticulumMeshChat.matches_discovery_pattern(
                    blacklist,
                    interface,
                )
            )
        ]

    def _default_announce_fetch_limit(self, aspect):
        ctx = self.current_context
        if not ctx or not ctx.config:
            return 2500
        keys = {
            "lxmf.delivery": ctx.config.announce_fetch_limit_lxmf_delivery,
            "nomadnetwork.node": ctx.config.announce_fetch_limit_nomadnetwork_node,
            "lxmf.propagation": ctx.config.announce_fetch_limit_lxmf_propagation,
            "lxst.telephony": ctx.config.announce_fetch_limit_lxmf_delivery,
        }
        cfg = keys.get(aspect)
        if cfg is None:
            return 2500
        v = cfg.get()
        if v is None or v < 1:
            return 2500
        return min(int(v), 100_000)

    def get_lxst_version(self) -> str:
        return self.get_package_version("lxst", getattr(LXST, "__version__", "unknown"))

    async def announce_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        gc_counter = 0

        while self.running and ctx.running and ctx.session_id == session_id:
            now = time.time()
            should_announce = interval_action_due(
                ctx.config.auto_announce_enabled.get(),
                ctx.config.last_announced_at.get(),
                ctx.config.auto_announce_interval_seconds.get(),
                now,
            )

            # announce
            if should_announce:
                await self.announce(context=ctx)

                # also announce forwarding aliases if any
                if ctx.forwarding_manager:
                    await asyncio.to_thread(ctx.forwarding_manager.announce_aliases)

            gc_counter += 1
            if gc_counter >= 300:
                gc_counter = 0
                try:
                    await asyncio.to_thread(self.memory_pressure.run_periodic_cleanup)
                except Exception as exc:
                    print(f"[memory_pressure] periodic cleanup error: {exc}")
                # Python 3.14+ incremental GC: with threshold[2]==0 full gen2
                # collections are never scheduled automatically, so force one.
                if sys.version_info >= (3, 14) and gc.get_threshold()[2] == 0:
                    gc.collect(2)
                else:
                    gc.collect()

            await asyncio.sleep(1)

    async def _memory_diag_snapshot_loop(self):
        if not self._mem_diag:
            return
        while self.running and self._mem_diag.enabled:
            try:
                await asyncio.to_thread(self._mem_diag.snapshot)
                n = self._mem_diag.total_snapshots
                if n % 12 == 0:
                    report = await asyncio.to_thread(
                        self._mem_diag.diff_snapshots,
                        top_n=10,
                    )
                    if report:
                        growth = sum(r["size_mib"] for r in report)
                        print(
                            f"[mem_diag] Snapshot #{n}: +{growth:.2f} MiB "
                            f"growth in top {len(report)} sites",
                        )
            except Exception as exc:
                print(f"[mem_diag] Snapshot error: {exc}")
            await asyncio.sleep(300)  # every 5 minutes

    # automatically syncs propagation nodes based on user config
    async def announce_sync_propagation_nodes(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        router = ctx.message_router
        sync_start_time = None
        while self.running and ctx.running and ctx.session_id == session_id:
            auto_sync_interval_seconds = ctx.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
            last_synced_at = (
                ctx.config.lxmf_preferred_propagation_node_last_synced_at.get()
            )
            outbound_node = router.get_outbound_propagation_node() if router else None
            should_sync = outbound_node is not None and interval_action_due(
                auto_sync_interval_seconds is not None
                and auto_sync_interval_seconds > 0,
                last_synced_at,
                auto_sync_interval_seconds,
                time.time(),
            )

            if should_sync and sync_start_time is None:
                started = await self.sync_propagation_nodes(context=ctx)
                if started:
                    sync_start_time = time.monotonic()

            if sync_start_time is not None and router:
                state = router.propagation_transfer_state
                elapsed = time.monotonic() - sync_start_time
                path_stuck = (
                    state == router.PR_PATH_REQUESTED
                    and outbound_node is not None
                    and not RNS.Transport.has_path(outbound_node)
                    and elapsed > 45.0
                )
                if propagation_sync_is_terminal(state):
                    if state != router.PR_IDLE:
                        self.stop_propagation_node_sync(context=ctx)
                        with contextlib.suppress(Exception):
                            router.propagation_transfer_state = router.PR_IDLE
                            router.propagation_transfer_progress = 0.0
                    ctx.config.lxmf_preferred_propagation_node_last_synced_at.set(
                        int(time.time()),
                    )
                    await self.send_config_to_websocket_clients(context=ctx)
                    sync_start_time = None
                elif path_stuck or elapsed > 120:
                    self.stop_propagation_node_sync(context=ctx)
                    with contextlib.suppress(Exception):
                        router.propagation_transfer_state = router.PR_IDLE
                    ctx.config.lxmf_preferred_propagation_node_last_synced_at.set(
                        int(time.time()),
                    )
                    await self.send_config_to_websocket_clients(context=ctx)
                    sync_start_time = None

            # wait 1 second before next loop
            await asyncio.sleep(1)

    async def crawler_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                if ctx.config.crawler_enabled.get():
                    crawler = getattr(ctx, "crawler_manager", None)
                    homepage = (
                        ctx.config.nomad_default_page_path.get() or "/page/index.mu"
                    )
                    # Sweep announced nodes. Policy decides whether to queue.
                    known_nodes = ctx.database.announces.get_announces(
                        aspect="nomadnetwork.node",
                    )
                    for node in known_nodes:
                        if (
                            not self.running
                            or not ctx.running
                            or ctx.session_id != session_id
                        ):
                            break
                        dest = node["destination_hash"]
                        if crawler:
                            crawler.queue_if_allowed(
                                dest,
                                homepage,
                                depth=0,
                                announced_recently=True,
                            )
                        else:
                            self.queue_crawler_task(dest, homepage, context=ctx)

                    max_retries = ctx.config.crawler_max_retries.get()
                    max_concurrent = max(
                        1,
                        min(2, int(ctx.config.crawler_max_concurrent.get() or 1)),
                    )
                    if crawler:
                        tasks = crawler.select_next_tasks(
                            max_retries=max_retries,
                            max_concurrent=max_concurrent,
                        )
                    else:
                        tasks = ctx.database.misc.get_pending_or_failed_crawl_tasks(
                            max_retries=max_retries,
                            max_concurrent=max_concurrent,
                        )

                    if tasks and self.running and ctx.running:
                        await asyncio.gather(
                            *[
                                self.process_crawler_task(task, context=ctx)
                                for task in tasks
                            ],
                        )

            except Exception as e:
                print(f"Error in crawler loop for {ctx.identity_hash}: {e}")

            # Wait 60s between policy sweeps (was 30s). Less mesh load.
            for _ in range(60):
                if not self.running or not ctx.running or ctx.session_id != session_id:
                    return
                await asyncio.sleep(1)

    async def process_crawler_task(self, task, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        crawler = getattr(ctx, "crawler_manager", None)
        task_id = task["id"]
        destination_hash = task["destination_hash"]
        page_path = task["page_path"]
        depth = int(task.get("depth") or 0)

        if crawler and crawler.is_opted_out(destination_hash):
            ctx.database.misc.update_crawl_task(
                task_id,
                status="cancelled",
                updated_at=datetime.now(UTC),
            )
            return

        if crawler and not crawler.node_may_request_today(destination_hash):
            # Defer until the daily slot opens.
            ctx.database.misc.update_crawl_task(
                task_id,
                status="pending",
                next_retry_at=datetime.now(UTC) + timedelta(hours=6),
                updated_at=datetime.now(UTC),
            )
            return

        if crawler:
            ok, reason, hops = crawler.path_ready_for_crawl(destination_hash)
            if not ok:
                if reason == "no_path":
                    ctx.database.misc.update_crawl_task(
                        task_id,
                        status="pending",
                        next_retry_at=datetime.now(UTC) + timedelta(minutes=15),
                        updated_at=datetime.now(UTC),
                    )
                    return
                crawler.mark_node_requested(
                    destination_hash,
                    hops=hops if hops < 64 else None,
                    skipped_reason=reason,
                )
                ctx.database.misc.update_crawl_task(
                    task_id,
                    status="skipped",
                    updated_at=datetime.now(UTC),
                )
                return
        else:
            hops = 0

        ctx.database.misc.update_crawl_task(
            task_id,
            status="crawling",
            last_retry_at=datetime.now(UTC),
        )

        print(
            f"Crawler: Archiving {destination_hash}:{page_path} "
            f"(Attempt {task['retry_count'] + 1}, depth={depth})",
        )

        done_event = asyncio.Event()
        success = [False]
        content_received = [None]
        failure_reason = ["timeout"]
        started = time.monotonic()

        def on_success(content):
            success[0] = True
            content_received[0] = content
            done_event.set()

        def on_failure(reason):
            failure_reason[0] = reason
            done_event.set()

        def on_progress(progress):
            pass

        downloader = NomadnetPageDownloader(
            destination_hash=bytes.fromhex(destination_hash),
            page_path=page_path,
            data=None,
            on_page_download_success=on_success,
            on_page_download_failure=on_failure,
            on_progress_update=on_progress,
            timeout=120,
            reticulum=getattr(self, "reticulum", None),
            **nomad_link_identity_kwargs(
                self,
                bytes.fromhex(destination_hash),
                private=False,
            ),
        )

        try:
            download_task = asyncio.create_task(downloader.download())
            try:
                await asyncio.wait_for(done_event.wait(), timeout=180)
            except TimeoutError:
                failure_reason[0] = "timeout"
                downloader.cancel()
            await download_task
        except Exception as e:
            print(
                f"Crawler: Error during download for {destination_hash}:{page_path}: {e}",
            )
            failure_reason[0] = str(e)
            done_event.set()

        elapsed_ms = (time.monotonic() - started) * 1000.0
        rtt_ms = None
        try:
            from meshchatx.src.backend.crawler_manager import link_rtt_ms
            from meshchatx.src.backend.nomadnet_downloader import get_cached_active_link

            link = get_cached_active_link(bytes.fromhex(destination_hash))
            rtt_ms = link_rtt_ms(link)
        except Exception:
            rtt_ms = None
        if rtt_ms is None:
            # Wall time for a single page request is a coarse stand-in.
            rtt_ms = elapsed_ms

        if crawler:
            crawler.mark_node_requested(
                destination_hash,
                rtt_ms=rtt_ms,
                hops=hops if isinstance(hops, int) else None,
            )

        if crawler and crawler.rtt_exceeds_limit(rtt_ms):
            print(
                f"Crawler: Skipping {destination_hash} (RTT {rtt_ms:.0f}ms above limit)",
            )
            crawler.mark_node_requested(
                destination_hash,
                rtt_ms=rtt_ms,
                hops=hops if isinstance(hops, int) else None,
                skipped_reason="rtt",
            )
            ctx.database.misc.update_crawl_task(
                task_id,
                status="skipped",
                updated_at=datetime.now(UTC),
            )
            return

        if success[0]:
            content = content_received[0] or ""
            from meshchatx.src.backend.crawler_manager import content_signals_nocrawl

            if content_signals_nocrawl(content):
                print(f"Crawler: Node {destination_hash} signalled nocrawl")
                if crawler:
                    crawler.record_opt_out(
                        destination_hash,
                        reason="page_signal",
                        source="signal",
                    )
                ctx.database.misc.update_crawl_task(
                    task_id,
                    status="cancelled",
                    updated_at=datetime.now(UTC),
                )
                return

            print(f"Crawler: Successfully archived {destination_hash}:{page_path}")
            self.archive_page(
                destination_hash,
                page_path,
                content,
                is_manual=False,
                context=ctx,
            )
            ctx.database.misc.update_crawl_task(
                task_id,
                status="completed",
                updated_at=datetime.now(UTC),
            )
            if crawler:
                crawler.database.misc.upsert_crawl_node_stats(
                    destination_hash,
                    pages_indexed=crawler.pages_indexed_for_node(destination_hash),
                )
                for child in crawler.discover_child_paths(
                    destination_hash,
                    content,
                    parent_depth=depth,
                    parent_path=page_path,
                ):
                    crawler.queue_if_allowed(
                        destination_hash,
                        child,
                        depth=depth + 1,
                        announced_recently=True,
                    )
        else:
            print(
                f"Crawler: Failed to archive {destination_hash}:{page_path} - {failure_reason[0]}",
            )
            retry_count = task["retry_count"] + 1
            retry_delay = ctx.config.crawler_retry_delay_seconds.get()
            backoff_delay = retry_delay * (2 ** (retry_count - 1))
            next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff_delay)
            ctx.database.misc.update_crawl_task(
                task_id,
                status="failed",
                retry_count=retry_count,
                next_retry_at=next_retry_at,
                updated_at=datetime.now(UTC),
            )

    # uses the provided destination hash as the active propagation node
    def set_active_propagation_node(self, destination_hash: str | None, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.message_router:
            return

        # Always cancel an in-flight sync before switching nodes so we don't
        # orphan a transfer or leave the router in a stuck state.
        self.stop_propagation_node_sync(context=ctx)

        # set outbound propagation node
        if destination_hash is not None and destination_hash != "":
            try:
                destination_hash_bytes = bytes.fromhex(destination_hash)
                ctx.message_router.set_outbound_propagation_node(
                    destination_hash_bytes,
                )
                with contextlib.suppress(Exception):
                    RNS.Transport.request_path(destination_hash_bytes)
            except Exception:
                # failed to set propagation node, clear it to ensure we don't use an old one by mistake
                self.remove_active_propagation_node(context=ctx)

        # stop using propagation node
        else:
            self.remove_active_propagation_node(context=ctx)

    # stops the in progress propagation node sync
    def stop_propagation_node_sync(self, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.message_router:
            return
        router = ctx.message_router
        with contextlib.suppress(Exception):
            router.cancel_propagation_node_requests()
        # cancel_propagation_node_requests resets via acknowledge_sync_completion,
        # but a blocked RNS.Identity.recall can leave the router in an active state.
        with contextlib.suppress(Exception):
            active_states = {
                router.PR_PATH_REQUESTED,
                router.PR_LINK_ESTABLISHING,
                router.PR_LINK_ESTABLISHED,
                router.PR_REQUEST_SENT,
                router.PR_RECEIVING,
                router.PR_RESPONSE_RECEIVED,
            }
            if router.propagation_transfer_state in active_states:
                router.propagation_transfer_state = router.PR_IDLE
                router.propagation_transfer_progress = 0.0

    async def _request_propagation_node_messages(self, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.message_router:
            return

        router = ctx.message_router

        def _request():
            try:
                router.request_messages_from_propagation_node(ctx.identity)
            except (EOFError, BrokenPipeError, ConnectionResetError, OSError):
                with contextlib.suppress(Exception):
                    router.propagation_transfer_state = router.PR_IDLE
                    router.propagation_transfer_progress = 0.0
            except Exception:
                logging.getLogger("meshchatx").exception(
                    "Propagation node message request failed",
                )

        await asyncio.to_thread(_request)
        await self.send_config_to_websocket_clients(context=ctx)

    def _get_propagation_sync_metrics(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return None

        key = ctx.identity_hash
        if key not in self._propagation_sync_metrics:
            self._propagation_sync_metrics[key] = {
                "started_at": None,
                "baseline_total_messages": 0,
                "baseline_delivered_messages": 0,
                "messages_stored": 0,
                "delivery_confirmations": 0,
                "messages_hidden": 0,
            }

        return self._propagation_sync_metrics[key]

    def _begin_propagation_sync_metrics(self, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return

        metrics = self._get_propagation_sync_metrics(context=ctx)
        if metrics is None:
            return

        metrics["started_at"] = datetime.now(UTC).isoformat()
        metrics["baseline_total_messages"] = ctx.database.messages.count_lxmf_messages()
        metrics["baseline_delivered_messages"] = (
            ctx.database.messages.count_lxmf_messages_by_state("delivered")
        )
        metrics["messages_stored"] = 0
        metrics["delivery_confirmations"] = 0
        metrics["messages_hidden"] = 0

    def _collect_propagation_sync_metrics(self, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return {
                "messages_stored": 0,
                "delivery_confirmations": 0,
                "messages_hidden": 0,
            }

        metrics = self._get_propagation_sync_metrics(context=ctx)
        if metrics is None:
            return {
                "messages_stored": 0,
                "delivery_confirmations": 0,
                "messages_hidden": 0,
            }
        if metrics["started_at"] is None:
            return {
                "messages_stored": 0,
                "delivery_confirmations": 0,
                "messages_hidden": 0,
            }

        if not ctx.message_router:
            return {
                "messages_stored": 0,
                "delivery_confirmations": 0,
                "messages_hidden": 0,
            }

        messages_received = ctx.message_router.propagation_transfer_last_result or 0
        current_total_messages = ctx.database.messages.count_lxmf_messages()
        current_delivered_messages = ctx.database.messages.count_lxmf_messages_by_state(
            "delivered",
        )

        messages_stored = max(
            current_total_messages - metrics["baseline_total_messages"],
            0,
        )
        delivery_confirmations = max(
            current_delivered_messages - metrics["baseline_delivered_messages"],
            0,
        )
        messages_hidden = max(
            messages_received - messages_stored - delivery_confirmations,
            0,
        )

        metrics["messages_stored"] = messages_stored
        metrics["delivery_confirmations"] = delivery_confirmations
        metrics["messages_hidden"] = messages_hidden

        return {
            "messages_stored": messages_stored,
            "delivery_confirmations": delivery_confirmations,
            "messages_hidden": messages_hidden,
        }

    # stops and removes the active propagation node
    def remove_active_propagation_node(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        self.stop_propagation_node_sync(context=ctx)
        if ctx.message_router:
            ctx.message_router.outbound_propagation_node = None
            # Force the transfer state back to idle so nothing remains stuck
            # after the outbound node is removed.
            with contextlib.suppress(Exception):
                ctx.message_router.propagation_transfer_state = (
                    ctx.message_router.PR_IDLE
                )

    # enables or disables the local lxmf propagation node
    def enable_local_propagation_node(self, enabled: bool = True, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.message_router:
            return
        try:
            if enabled:
                ctx.message_router.enable_propagation()
            else:
                ctx.message_router.disable_propagation()
        except Exception:
            print(
                f"failed to enable or disable propagation node for {ctx.identity_hash}",
            )

    def stop_local_propagation_node(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        self.enable_local_propagation_node(False, context=ctx)

    def restart_local_propagation_node(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        self.stop_local_propagation_node(context=ctx)
        self.enable_local_propagation_node(True, context=ctx)

    def get_local_propagation_node_stats(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return None

        router = ctx.message_router
        if not router:
            return None

        is_running = bool(getattr(router, "propagation_node", False))
        stats = None
        if is_running:
            with contextlib.suppress(Exception):
                stats = router.compile_stats()

        def _numeric(value, default=0):
            return value if isinstance(value, (int, float)) else default

        destination_hash_raw = getattr(
            router.propagation_destination,
            "hexhash",
            None,
        )
        if destination_hash_raw is None:
            destination_hash_raw = getattr(
                router.propagation_destination,
                "hash",
                None,
            )
        if isinstance(destination_hash_raw, bytes):
            destination_hash = destination_hash_raw.hex()
        elif isinstance(destination_hash_raw, str):
            destination_hash = destination_hash_raw
        else:
            destination_hash = None

        message_store = stats.get("messagestore", {}) if isinstance(stats, dict) else {}
        clients = stats.get("clients", {}) if isinstance(stats, dict) else {}
        peers = stats.get("peers", {}) if isinstance(stats, dict) else {}
        uptime = _numeric(stats.get("uptime", 0)) if isinstance(stats, dict) else 0
        peer_rx_bytes = 0
        peer_tx_bytes = 0
        if isinstance(peers, dict):
            for peer_stats in peers.values():
                if not isinstance(peer_stats, dict):
                    continue
                peer_rx_bytes += int(_numeric(peer_stats.get("rx_bytes", 0)))
                peer_tx_bytes += int(_numeric(peer_stats.get("tx_bytes", 0)))
        unpeered_rx_bytes = (
            int(_numeric(stats.get("unpeered_propagation_rx_bytes", 0)))
            if isinstance(stats, dict)
            else 0
        )
        delivery_limit = (
            _numeric(stats.get("delivery_limit", 0))
            if isinstance(stats, dict)
            else _numeric(getattr(router, "delivery_per_transfer_limit", 0))
        )
        propagation_limit = (
            _numeric(stats.get("propagation_limit", 0))
            if isinstance(stats, dict)
            else _numeric(getattr(router, "propagation_per_transfer_limit", 0))
        )
        sync_limit = (
            _numeric(stats.get("sync_limit", 0))
            if isinstance(stats, dict)
            else _numeric(getattr(router, "propagation_per_sync_limit", 0))
        )
        result = {
            "is_running": is_running,
            "identity_hash": ctx.identity.hash.hex(),
            "destination_hash": destination_hash,
            "uptime_seconds": int(uptime) if uptime else 0,
            "messagestore_count": message_store.get("count", 0),
            "messagestore_bytes": message_store.get("bytes", 0),
            "messagestore_limit_bytes": message_store.get("limit"),
            "client_messages_received": clients.get(
                "client_propagation_messages_received",
                0,
            ),
            "client_messages_served": clients.get(
                "client_propagation_messages_served",
                0,
            ),
            "rx_bytes": peer_rx_bytes + unpeered_rx_bytes,
            "tx_bytes": peer_tx_bytes,
            "unpeered_rx_bytes": unpeered_rx_bytes,
            "static_peers": stats.get("static_peers", 0)
            if isinstance(stats, dict)
            else 0,
            "discovered_peers": (
                stats.get("discovered_peers", 0) if isinstance(stats, dict) else 0
            ),
            "total_peers": stats.get("total_peers", 0)
            if isinstance(stats, dict)
            else 0,
            "max_peers": stats.get("max_peers") if isinstance(stats, dict) else None,
            "delivery_limit_bytes": int(delivery_limit * 1000),
            "propagation_limit_bytes": int(propagation_limit * 1000),
            "sync_limit_bytes": int(sync_limit * 1000),
            "target_stamp_cost": _numeric(
                (
                    stats.get("target_stamp_cost", 0)
                    if isinstance(stats, dict)
                    else getattr(router, "propagation_stamp_cost", 0)
                ),
            ),
            "inbound_delivery_count": 0,
            "inbound_deliveries": [],
            "max_inbound_syncs": int(
                getattr(router, "propagation_max_inbound_syncs", 0) or 0,
            ),
            "sequential_validation": bool(
                getattr(router, "propagation_sequential_validation", True),
            ),
            "static_peers_bypass_sequential": not bool(
                getattr(router, "propagation_static_peer_sequential", False),
            ),
        }
        inbound_deliveries = list_inbound_deliveries(router)
        result["inbound_deliveries"] = inbound_deliveries
        result["inbound_delivery_count"] = len(inbound_deliveries)
        return result

    def _get_reticulum_section(self):
        try:
            if hasattr(self, "reticulum") and self.reticulum:
                reticulum_config = self.reticulum.config["reticulum"]
            else:
                return {}
        except Exception:
            reticulum_config = None

        if not isinstance(reticulum_config, dict):
            reticulum_config = {}
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.config["reticulum"] = reticulum_config

        return reticulum_config

    @staticmethod
    def _parse_rns_config_bool(value, default=False):
        """Parse Reticulum config Yes/No / bool-ish values."""
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        text = str(value).strip().lower()
        if text in ("yes", "true", "1", "on"):
            return True
        if text in ("no", "false", "0", "off", ""):
            return False
        return bool(default)

    @staticmethod
    def _format_rns_config_bool(value):
        return "Yes" if bool(value) else "No"

    @staticmethod
    def _parse_rns_hash_list(value):
        """Parse a RNS config identity-hash list into lowercase hex strings."""
        items = []
        if value is None:
            return items
        if isinstance(value, (list, tuple)):
            raw_items = value
        else:
            raw_items = str(value).replace(",", " ").split()
        try:
            expected = int(RNS.Reticulum.TRUNCATED_HASHLENGTH) // 8 * 2
        except Exception:
            expected = 32
        if expected <= 0:
            expected = 32
        for item in raw_items:
            text = str(item).strip().lower()
            if not text:
                continue
            if len(text) != expected:
                raise ValueError(
                    f"Identity hash {text} must be {expected} hexadecimal characters",
                )
            try:
                bytes.fromhex(text)
            except ValueError as exc:
                raise ValueError(f"Invalid identity hash: {text}") from exc
            if text not in items:
                items.append(text)
        return items

    def _get_reticulum_rpc_key_hex(self):
        """Return the live or configured RPC key as lowercase hex, or None."""
        reticulum = getattr(self, "reticulum", None)
        if reticulum is not None:
            key = getattr(reticulum, "rpc_key", None)
            if isinstance(key, (bytes, bytearray)) and key:
                try:
                    return RNS.hexrep(key, delimit=False)
                except Exception:
                    return bytes(key).hex()
            if isinstance(key, str) and key.strip():
                return key.strip().lower()
        section = self._get_reticulum_section()
        raw = section.get("rpc_key")
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower()
        return None

    def _build_reticulum_instance_settings(self):
        """Sideband-parity shared-instance / RPC / hop-obfuscation settings."""
        section = self._get_reticulum_section()
        reticulum = getattr(self, "reticulum", None)
        share_default = True
        if reticulum is not None and hasattr(reticulum, "share_instance"):
            share_default = bool(reticulum.share_instance)
        share_instance = self._parse_rns_config_bool(
            section.get("share_instance"),
            default=share_default,
        )
        if "local_hops_delta" in section:
            local_hops_delta = self._parse_rns_config_bool(
                section.get("local_hops_delta"),
                default=False,
            )
        else:
            local_hops_delta = False
            if reticulum is not None and hasattr(RNS.Reticulum, "local_hops_delta"):
                try:
                    local_hops_delta = bool(RNS.Reticulum.local_hops_delta())
                except Exception:
                    pass

        shared_type_raw = section.get("shared_instance_type")
        shared_instance_type = None
        if isinstance(shared_type_raw, str) and shared_type_raw.strip():
            shared_instance_type = shared_type_raw.strip().lower()
        elif reticulum is not None:
            live_type = getattr(reticulum, "shared_instance_type", None)
            if isinstance(live_type, str) and live_type.strip():
                shared_instance_type = live_type.strip().lower()

        instance_name = section.get("instance_name")
        if not isinstance(instance_name, str) or not instance_name.strip():
            instance_name = "default"
        else:
            instance_name = instance_name.strip()

        is_connected = bool(
            reticulum is not None
            and getattr(reticulum, "is_connected_to_shared_instance", False),
        )
        rpc_key = self._get_reticulum_rpc_key_hex()
        rpc_snippet = None
        if rpc_key:
            type_line = shared_instance_type or "tcp"
            rpc_snippet = f"shared_instance_type = {type_line}\nrpc_key = {rpc_key}"

        return {
            "share_instance": share_instance,
            "local_hops_delta": local_hops_delta,
            "shared_instance_type": shared_instance_type,
            "instance_name": instance_name,
            "rpc_key": rpc_key,
            "rpc_config_snippet": rpc_snippet,
            "is_connected_to_shared_instance": is_connected,
            "enable_transport": self._parse_rns_config_bool(
                section.get("enable_transport"),
                default=bool(
                    reticulum is not None
                    and getattr(reticulum, "transport_enabled", lambda: False)(),
                ),
            ),
            "respond_to_probes": self._parse_rns_config_bool(
                section.get("respond_to_probes"),
                default=False,
            ),
            "enable_remote_management": self._parse_rns_config_bool(
                section.get("enable_remote_management"),
                default=False,
            ),
            "remote_management_allowed": self._safe_remote_management_allowed(
                section.get("remote_management_allowed"),
            ),
        }

    def _safe_remote_management_allowed(self, value):
        try:
            return self._parse_rns_hash_list(value)
        except ValueError:
            return []

    def _get_interfaces_section(self):
        try:
            if hasattr(self, "reticulum") and self.reticulum:
                interfaces = self.reticulum.config["interfaces"]
            else:
                return {}
        except Exception:
            interfaces = None

        if not isinstance(interfaces, dict):
            interfaces = {}
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.config["interfaces"] = interfaces

        return interfaces

    @staticmethod
    def _copy_interface_section(details):
        try:
            return copy.deepcopy(dict(details))
        except Exception:
            try:
                return copy.deepcopy(details)
            except Exception:
                return {}

    def _disk_interface_sections(self) -> dict:
        """Parse [[interface]] sections from the on-disk Reticulum config file.

        The Interfaces page reads reticulum.config in memory. The raw config
        editor reads the file. Those two can diverge after a raw save, a
        failed write, or an external edit, which hides a configured interface
        from the tiles.
        """
        try:
            path = self._reticulum_config_file_path()
        except Exception:
            path = None
        if not path or not os.path.isfile(path):
            return {}
        try:
            from RNS.vendor.configobj import ConfigObj

            cfg = ConfigObj(path)
        except Exception:
            return {}
        interfaces = cfg.get("interfaces")
        if not isinstance(interfaces, dict):
            return {}
        copied = {}
        for name, details in interfaces.items():
            if not isinstance(details, dict):
                continue
            copied[str(name)] = self._copy_interface_section(details)
        return copied

    def _sync_interfaces_from_disk(self, *, replace: bool = False) -> None:
        """Align the live interfaces map with the on-disk config file.

        replace False adds disk-only sections so tiles and delete/enable can
        see them. replace True makes the live map match the file (raw editor
        save or restore).
        """
        disk = self._disk_interface_sections()
        mem = self._get_interfaces_section()
        if replace:
            for name in list(mem.keys()):
                if name not in disk:
                    del mem[name]
        for name, details in disk.items():
            if replace or name not in mem:
                mem[name] = details

    def _get_interfaces_snapshot(self):
        snapshot = {}
        interfaces = self._get_interfaces_section()
        for name, interface in interfaces.items():
            try:
                snapshot[name] = copy.deepcopy(dict(interface))
            except Exception:
                try:
                    snapshot[name] = copy.deepcopy(interface)
                except Exception:
                    snapshot[name] = {}
        return snapshot

    def _sanitize_interfaces_section_names(self) -> None:
        """Rewrite interface section keys so ConfigObj can reload the config file."""
        interfaces = self._get_interfaces_section()
        if not isinstance(interfaces, dict) or not interfaces:
            return
        renamed: dict = {}
        changed = False
        for name, details in list(interfaces.items()):
            safe = InterfaceEditor.sanitize_interface_section_name(name)
            if not safe:
                safe = "Interface"
            if safe != name:
                changed = True
            # Avoid collisions after sanitizing two distinct names to the same key.
            final = safe
            suffix = 2
            while final in renamed:
                final = f"{safe} ({suffix})"
                suffix += 1
            if final != name:
                changed = True
            renamed[final] = details
        if changed:
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.config["interfaces"] = renamed

    def _verify_reticulum_config_reloadable(self) -> None:
        """Ensure the on-disk config still parses after write (ConfigObj quirk)."""
        from RNS.vendor.configobj import ConfigObj

        path = None
        try:
            path = self._api_reticulum_config_path()
        except Exception:
            path = None
        if not path:
            path = getattr(getattr(self, "reticulum", None), "configpath", None)
        if not path or not os.path.isfile(path):
            return
        ConfigObj(path)

    def _write_reticulum_config(self, *, rollback_interfaces=None):
        try:
            if hasattr(self, "reticulum") and self.reticulum:
                self._sanitize_interfaces_section_names()
                try:
                    i2p_support.repair_interfaces_dict(
                        self._get_interfaces_section(),
                        self._get_reticulum_section(),
                    )
                except Exception as i2p_exc:
                    print(f"I2P config repair before write failed: {i2p_exc}")
                self.reticulum.config.write()
                self._verify_reticulum_config_reloadable()
                return True
            return False
        except Exception as e:
            print(f"Failed to write Reticulum config: {e}")
            if (
                rollback_interfaces is not None
                and hasattr(self, "reticulum")
                and self.reticulum
            ):
                try:
                    self.reticulum.config["interfaces"] = rollback_interfaces
                except Exception as restore_exc:
                    print(
                        "Failed to restore Reticulum interfaces after write error: "
                        f"{restore_exc}",
                    )
            return False

    def _detect_failed_autointerfaces(self):
        """Return AutoInterface section names enabled in config but not running."""
        enabled_names = []
        try:
            interfaces = self._get_interfaces_section()
        except Exception:
            return []

        if not isinstance(interfaces, dict) or not interfaces:
            return []

        for name, section in interfaces.items():
            if not isinstance(section, dict):
                continue
            if str(section.get("type", "")).strip() != "AutoInterface":
                continue
            enabled_raw = (
                str(
                    section.get("enabled") or section.get("interface_enabled") or "",
                )
                .strip()
                .lower()
            )
            if enabled_raw in ("yes", "true", "1"):
                enabled_names.append(name)

        if not enabled_names:
            return []

        try:
            live = getattr(RNS.Transport, "interfaces", None) or []
            for iface in live:
                if iface.__class__.__name__ == "AutoInterface":
                    return []
        except Exception:
            return []

        return enabled_names

    def build_user_guidance_messages(self):
        guidance = []

        interfaces = self._get_interfaces_section()
        if len(interfaces) == 0:
            guidance.append(
                {
                    "id": "no_interfaces",
                    "title": "No Reticulum interfaces configured",
                    "description": "Add at least one Reticulum interface so MeshChat can talk to your radio or transport.",
                    "action_route": "/interfaces/add",
                    "action_label": "Add Interface",
                    "severity": "warning",
                },
            )

        failed_autointerfaces = self._detect_failed_autointerfaces()
        if failed_autointerfaces:
            failed_label = ", ".join(failed_autointerfaces)
            guidance.append(
                {
                    "id": "autointerface_bind_failed",
                    "title": "AutoInterface failed to start",
                    "description": (
                        f"AutoInterface '{failed_label}' is enabled in your "
                        "Reticulum config but did not come up at runtime. "
                        "The most common cause is a UDP port collision with "
                        "another local Reticulum application (for example "
                        "Sideband running on the same device on Android). "
                        "Open the interface and set a unique group_id, or "
                        "pick free discovery_port and data_port values, then "
                        "restart Reticulum."
                    ),
                    "action_route": "/interfaces",
                    "action_label": "Open Interfaces",
                    "severity": "warning",
                },
            )

        if (
            hasattr(self, "reticulum")
            and self.reticulum
            and not self.reticulum.transport_enabled()
        ):
            guidance.append(
                {
                    "id": "transport_disabled",
                    "title": "Transport mode is disabled",
                    "description": "Enable transport to allow MeshChat to relay traffic over your configured interfaces.",
                    "action_route": "/settings",
                    "action_label": "Open Settings",
                    "severity": "info",
                },
            )

        if not self.config.auto_announce_enabled.get():
            guidance.append(
                {
                    "id": "announce_disabled",
                    "title": "Auto announcements are turned off",
                    "description": "Automatic announces make it easier for other peers to discover you. Enable them if you want to stay visible.",
                    "action_route": "/settings",
                    "action_label": "Manage Announce Settings",
                    "severity": "info",
                },
            )

        return guidance

    # returns the latest message for the provided destination hash
    def get_conversation_latest_message(self, destination_hash: str):
        local_hash = self.identity.hash.hex()
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
            limit=1,
        )
        return messages[0] if messages else None

    # returns true if the conversation with the provided destination hash has any attachments
    def conversation_has_attachments(self, destination_hash: str):
        local_hash = self.identity.hash.hex()
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
        )
        for message in messages:
            if message_fields_have_attachments(message["fields"]):
                return True
        return False

    def search_destination_hashes_by_message(self, search_term: str):
        if search_term is None or search_term.strip() == "":
            return set()

        local_hash = self.local_lxmf_destination.hexhash
        search_term = search_term.strip()
        matches = set()

        query_results = self.message_handler.search_messages(local_hash, search_term)

        for message in query_results:
            if message["source_hash"] == local_hash:
                matches.add(message["destination_hash"])
            else:
                matches.add(message["source_hash"])

        # also check custom display names
        custom_names = (
            self.database.announces.get_announces()
        )  # Or more specific if needed
        for announce in custom_names:
            custom_name = self.database.announces.get_custom_display_name(
                announce["destination_hash"],
            )
            if custom_name and search_term.lower() in custom_name.lower():
                matches.add(announce["destination_hash"])

        return matches

    def on_new_voicemail_received(
        self,
        remote_hash,
        remote_name,
        duration,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return
        # Add system notification
        self.database.misc.add_notification(
            notification_type="telephone_voicemail",
            remote_hash=remote_hash,
            title="New Voicemail",
            content=f"New voicemail from {remote_name or remote_hash} ({duration}s)",
        )

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "new_voicemail",
                        "remote_identity_hash": remote_hash,
                        "remote_identity_name": remote_name,
                        "duration": duration,
                        "timestamp": time.time(),
                    },
                ),
            ),
        )

    # handle receiving a new audio call
    def on_incoming_telephone_call(self, caller_identity: RNS.Identity, context=None):
        ctx = context or self.current_context
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
        if self.is_destination_blocked(caller_hash, context=ctx):
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
            if not self._is_contact(caller_hash, context=ctx):
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
        caller_name = (self.get_name_for_identity_hash(ch) or "").strip() or "Mesh"
        is_contact = self._is_contact(ch, context=ctx)
        AsyncUtils.run_async(
            self.websocket_broadcast(
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

    def on_telephone_call_established(
        self,
        caller_identity: RNS.Identity,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return
        print(f"on_telephone_call_established: {caller_identity.hash.hex()}")
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_call_established",
                    },
                ),
            ),
        )

    def on_telephone_call_ended(self, caller_identity: RNS.Identity, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        # Stop voicemail recording if active
        ctx.voicemail_manager.stop_recording()

        print(
            f"on_telephone_call_ended: {caller_identity.hash.hex() if caller_identity else 'Unknown'}",
        )
        try:
            self.web_audio_bridge.on_call_ended()
        except Exception as e:
            logging.exception(f"Error in web_audio_bridge.on_call_ended: {e}")

        # Record call history
        if caller_identity:
            remote_identity_hash = caller_identity.hash.hex()
            remote_identity_name = self.get_name_for_identity_hash(remote_identity_hash)

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
                if not self.is_destination_blocked(remote_identity_hash, context=ctx):
                    ctx.database.misc.add_notification(
                        notification_type="telephone_missed_call",
                        remote_hash=remote_identity_hash,
                        title="Missed Call",
                        content=f"You missed a call from {remote_identity_name or remote_identity_hash}",
                    )

                    if not self.incoming_call_is_policy_filtered(
                        remote_identity_hash,
                        context=ctx,
                    ):
                        AsyncUtils.run_async(
                            self.websocket_broadcast(
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
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_call_ended",
                    },
                ),
            ),
        )

    def on_telephone_initiation_status(self, status, target_hash, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        target_name = None
        if target_hash:
            try:
                contact = ctx.database.contacts.get_contact_by_identity_hash(
                    target_hash,
                )
                if contact:
                    target_name = contact.name
            except Exception:
                pass

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_initiation_status",
                        "status": status,
                        "target_hash": target_hash,
                        "target_name": target_name,
                    },
                ),
            ),
        )

    def on_rrc_change(self, hub, context=None):
        """Broadcast an RRC hub state change to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rrc.change",
                        "hub_hash": hub.hub_hash.hex() if hub is not None else None,
                    },
                ),
            ),
        )

    def _rrc_mention_remote_hash(self, hub_hash_hex, room):
        from meshchatx.src.backend.rrc import protocol as rrc_protocol

        return f"{hub_hash_hex}:{rrc_protocol.normalize_room(room)}"

    def _maybe_add_rrc_mention_notification(self, hub, msg, context=None):
        if hub is None or not getattr(msg, "mention", False):
            return
        if msg.kind not in ("msg", "action"):
            return
        if not msg.room:
            return
        ctx = context or self.current_context
        if ctx is None:
            return
        from meshchatx.src.backend.rrc import protocol as rrc_protocol

        room = rrc_protocol.normalize_room(msg.room)
        hub_hash = hub.hub_hash.hex()
        remote_hash = self._rrc_mention_remote_hash(hub_hash, room)
        hub_label = (
            hub.get_display_name()
            if hasattr(hub, "get_display_name")
            else (hub.name or hub_hash[:12])
        )
        nick = msg.nick if isinstance(msg.nick, str) and msg.nick else None
        if not nick and isinstance(msg.src, (bytes, bytearray)):
            nick = msg.src.hex()[:12]
        nick = nick or "Someone"
        preview = (msg.text or "").strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."
        title = f"#{room} · {hub_label}"
        content = f"{nick}: {preview}" if preview else f"{nick} mentioned you"
        ctx.database.misc.dismiss_unviewed_notifications(
            notification_type="rrc_mention",
            remote_hash=remote_hash,
        )
        ctx.database.misc.add_notification(
            "rrc_mention",
            remote_hash,
            title,
            content,
        )

    def _mark_rrc_mention_notifications_viewed(self, hub_hash_hex, room, context=None):
        ctx = context or self.current_context
        if ctx is None or not room:
            return
        with contextlib.suppress(ValueError):
            ctx.database.misc.dismiss_unviewed_notifications(
                notification_type="rrc_mention",
                remote_hash=self._rrc_mention_remote_hash(hub_hash_hex, room),
            )

    def on_rrc_message(self, hub, msg, context=None):
        """Broadcast a new RRC message to connected clients."""
        with contextlib.suppress(Exception):
            self._maybe_add_rrc_mention_notification(hub, msg, context=context)
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rrc.message",
                        "hub_hash": hub.hub_hash.hex() if hub is not None else None,
                        "room": msg.room,
                        "message": msg.to_dict(),
                        "mention": bool(getattr(msg, "mention", False)),
                    },
                ),
            ),
        )

    def on_rrc_server_change(self, hub, context=None):
        """Broadcast a hosted RRC hub state change to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rrc.server.change",
                        "hub_id": hub.hub_id if hub is not None else None,
                    },
                ),
            ),
        )

    def on_rnsh_change(self, session, context=None):
        """Broadcast an RNSh session state change to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rnsh.session.change",
                        "session_id": session.session_id
                        if session is not None
                        else None,
                    },
                ),
            ),
        )

    def on_rnsh_output(self, session, chunk, context=None):
        """Broadcast RNSh output chunks to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rnsh.output",
                        "session_id": session.session_id
                        if session is not None
                        else None,
                        "chunk": chunk,
                    },
                ),
            ),
        )

    def on_rnx_change(self, session, context=None):
        """Broadcast an RNX session state change to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rnx.session.change",
                        "session_id": session.session_id
                        if session is not None
                        else None,
                    },
                ),
            ),
        )

    def on_rnx_output(self, session, chunk, context=None):
        """Broadcast RNX output chunks to connected clients."""
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "rnx.output",
                        "session_id": session.session_id
                        if session is not None
                        else None,
                        "chunk": chunk,
                    },
                ),
            ),
        )

    # web server has shutdown, likely ctrl+c, but if we don't do the following, the script never exits
    async def shutdown(self, app):
        # Always flush SQLite first. Signal handlers may have already done this.
        with contextlib.suppress(Exception):
            from meshchatx.src.backend.lifecycle.signal_shutdown import (
                durable_flush_all_databases,
            )

            durable_flush_all_databases(self)

        for identity_hash in list(self.contexts.keys()):
            ctx = self.contexts.get(identity_hash)
            if ctx is None:
                continue
            bh = getattr(ctx, "bot_handler", None)
            if bh is not None:
                with contextlib.suppress(Exception):
                    bh.stop_all()

        if hasattr(self, "page_node_manager"):
            self.page_node_manager.teardown()

        for identity_hash in list(self.contexts.keys()):
            ctx = self.contexts.get(identity_hash)
            if ctx is None:
                continue
            try:
                ctx.teardown()
            except Exception:
                pass
        self.contexts.clear()
        self.current_context = None

        if hasattr(self, "_health_monitor") and self._health_monitor is not None:
            with contextlib.suppress(Exception):
                self._health_monitor.stop()

        if self._mem_diag is not None:
            with contextlib.suppress(Exception):
                self._mem_diag.stop()

        # force close websocket clients (copy: close() may touch the client list)
        for websocket_client in list(self.websocket_clients):
            try:
                await websocket_client.close(code=WSCloseCode.GOING_AWAY)
            except Exception:
                pass

        # stop reticulum
        try:
            RNS.Transport.detach_interfaces()
        except Exception:
            pass

        if hasattr(self, "reticulum") and self.reticulum:
            try:
                self.reticulum.exit_handler()
            except Exception:
                pass

        try:
            RNS.exit()
        except Exception:
            pass

    def exit_app(self, code=0):
        sys.exit(code)

    def _require_identity_context_ready(self):
        """Return an HTTP 503 response when identity/DB is not ready yet."""
        if not self.current_context or not getattr(
            self.current_context,
            "running",
            False,
        ):
            return web.json_response(
                {
                    "message": "Identity context is still starting. Retry shortly.",
                    "stage": self._startup_stage,
                    "network_ready": bool(self._network_ready),
                },
                status=503,
            )
        if self.database is None or self.message_handler is None:
            return web.json_response(
                {
                    "message": "Database is still starting. Retry shortly.",
                    "stage": self._startup_stage,
                    "network_ready": bool(self._network_ready),
                },
                status=503,
            )
        if self.local_lxmf_destination is None:
            return web.json_response(
                {
                    "message": "Local LXMF destination is still starting. Retry shortly.",
                    "stage": self._startup_stage,
                    "network_ready": bool(self._network_ready),
                },
                status=503,
            )
        return None

    def _require_rns_tool_handler(self, handler, tool_name: str):
        """Return 503 when an RNS tool handler is unavailable (e.g. mid-reload)."""
        if handler is None:
            return web.json_response(
                {
                    "message": f"{tool_name} is unavailable while the RNS stack is reloading.",
                    "stage": self._startup_stage,
                    "network_ready": bool(self._network_ready),
                },
                status=503,
            )
        reticulum = getattr(handler, "reticulum", None)
        if reticulum is None and not hasattr(self, "reticulum"):
            return web.json_response(
                {
                    "message": f"{tool_name} is unavailable while the RNS stack is reloading.",
                    "stage": self._startup_stage,
                    "network_ready": bool(self._network_ready),
                },
                status=503,
            )
        return None

    def _require_outbound_http(self, feature: str) -> None:
        if self.config:
            ensure_outbound_http_allowed(self.config, feature=feature)

    def _landlock_status_dict(self) -> dict:
        return {
            "landlock_kernel_supported": landlock_kernel_supported(),
            "landlock_requested": landlock_requested(),
            "landlock_auto_enabled": landlock_auto_enabled(),
            "landlock_disabled_by_env": landlock_disabled_by_env(),
            "landlock_active": self.landlock_active,
            "appcontainer_supported": appcontainer_supported(),
            "appcontainer_requested": appcontainer_requested(),
            "appcontainer_auto_enabled": appcontainer_auto_enabled(),
            "appcontainer_disabled_by_env": appcontainer_disabled_by_env(),
            "appcontainer_active": self.appcontainer_active,
            "fs_sandbox_active": bool(self.landlock_active or self.appcontainer_active),
            "seccomp_kernel_supported": seccomp_kernel_supported(),
            "seccomp_requested": seccomp_requested(),
            "seccomp_auto_enabled": seccomp_auto_enabled(),
            "seccomp_disabled_by_env": seccomp_disabled_by_env(),
            "seccomp_active": self.seccomp_active,
        }

    @property
    def fs_sandbox_active(self) -> bool:
        return bool(self.landlock_active or self.appcontainer_active)

    def get_routes(self):
        routes = web.RouteTableDef()
        self._define_routes(routes)
        return routes

    def _define_routes(self, routes):
        from meshchatx.src.backend.http.register import register_all_routes

        (
            sqlite_unavailable_middleware,
            auth_middleware,
            mime_type_middleware,
            security_middleware,
            csrf_middleware,
            ip_allowlist_middleware,
            demo_mode_middleware,
        ) = register_all_routes(routes, self)

        return (
            sqlite_unavailable_middleware,
            auth_middleware,
            mime_type_middleware,
            security_middleware,
            csrf_middleware,
            ip_allowlist_middleware,
            demo_mode_middleware,
        )

    def _encrypted_cookie_storage(self, use_https: bool) -> EncryptedCookieStorage:
        try:
            secret_key_bytes = base64.urlsafe_b64decode(self.session_secret_key + "===")
            if len(secret_key_bytes) < 32:
                secret_key_bytes = secret_key_bytes.ljust(32, b"\0")
            elif len(secret_key_bytes) > 32:
                secret_key_bytes = secret_key_bytes[:32]
        except Exception:
            secret_key_bytes = hashlib.sha256(
                self.session_secret_key.encode("utf-8"),
            ).digest()
        return EncryptedCookieStorage(
            secret_key_bytes,
            secure=use_https,
            httponly=True,
            samesite="Lax",
        )

    def _enforce_login_access(self, request, path: str):
        if not self.database:
            return None
        ip = _request_client_ip(request, get_trusted_proxy_cidrs(self.storage_dir))
        ua = request.headers.get("User-Agent", "") or ""
        ua_h = user_agent_hash(ua)
        id_hash = self.identity.hash.hex()
        dao = self.database.access_attempts
        trusted = dao.is_trusted(id_hash, ip, ua_h)
        now = time.time()
        if trusted:
            if (
                dao.count_login_attempts_ip_ua(
                    ip,
                    ua_h,
                    path,
                    now - WINDOW_RATE_TRUSTED_S,
                )
                >= MAX_TRUSTED_LOGIN_PER_WINDOW
            ):
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    path,
                    request.method,
                    "rate_limited",
                    "trusted_window",
                )
                return web.json_response(
                    {"error": "Too many requests. Try again later."},
                    status=429,
                )
        else:
            if (
                dao.count_login_attempts_ip(ip, path, now - WINDOW_RATE_UNTRUSTED_S)
                >= MAX_UNTRUSTED_LOGIN_PER_WINDOW
            ):
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    path,
                    request.method,
                    "rate_limited",
                    "ip_window",
                )
                return web.json_response(
                    {"error": "Too many requests. Try again later."},
                    status=429,
                )
            if (
                dao.count_lockout_failures(id_hash, ip, now - WINDOW_LOCKOUT_S)
                >= MAX_FAILED_BEFORE_LOCKOUT
            ):
                dao.insert(
                    id_hash,
                    ip,
                    ua,
                    path,
                    request.method,
                    "lockout",
                    "failures",
                )
                return web.json_response(
                    {
                        "error": "Too many failed login attempts from this address. Try again later.",
                    },
                    status=429,
                )
        return None

    def run(self, host, port, launch_browser: bool, enable_https: bool = True):
        # create route table
        routes = web.RouteTableDef()
        (
            sqlite_unavailable_middleware,
            auth_middleware,
            mime_type_middleware,
            security_middleware,
            csrf_middleware,
            ip_allowlist_middleware,
            demo_mode_middleware,
        ) = self._define_routes(routes)

        ssl_context = None
        use_https = enable_https
        self.listen_host = host
        self.listen_port = port
        self.use_https = use_https
        if enable_https:
            custom_ssl = bool(self.ssl_cert_path and self.ssl_key_path)
            if custom_ssl:
                cert_path = os.path.abspath(self.ssl_cert_path)
                key_path = os.path.abspath(self.ssl_key_path)
            else:
                cert_dir = os.path.join(self.storage_path, "ssl")
                cert_path = os.path.join(cert_dir, "cert.pem")
                key_path = os.path.join(cert_dir, "key.pem")

            try:
                if custom_ssl:
                    if not os.path.isfile(cert_path) or not os.path.isfile(key_path):
                        msg = f"Custom SSL files not found (cert={cert_path!r}, key={key_path!r})"
                        raise FileNotFoundError(msg)
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ssl_context.load_cert_chain(cert_path, key_path)
                    print(
                        f"HTTPS enabled with custom certificate at {cert_path}",
                        flush=True,
                    )
                else:
                    generate_ssl_certificate(cert_path, key_path)
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ssl_context.load_cert_chain(cert_path, key_path)
                    print(f"HTTPS enabled with certificate at {cert_path}", flush=True)
            except Exception as e:
                if custom_ssl:
                    print(f"Failed to load custom SSL certificate: {e}")
                else:
                    print(f"Failed to generate SSL certificate: {e}")
                print("Falling back to HTTP")
                use_https = False

        # session secret for encrypted cookies (generate once and store in shared storage)
        session_secret_path = os.path.join(self.storage_dir, "session_secret")
        self.session_secret_key = None

        if os.path.exists(session_secret_path):
            try:
                with open(session_secret_path) as f:
                    self.session_secret_key = f.read().strip()
            except Exception as e:
                print(f"Failed to read session secret from {session_secret_path}: {e}")

        if not self.session_secret_key:
            # try to migrate from current identity config if available
            if self.config is not None:
                self.session_secret_key = self.config.auth_session_secret.get()
            if not self.session_secret_key:
                self.session_secret_key = secrets.token_urlsafe(32)

            try:
                with open(session_secret_path, "w") as f:
                    f.write(self.session_secret_key)
            except Exception as e:
                print(f"Failed to write session secret to {session_secret_path}: {e}")

        # ensure it's also in the current config for consistency when identity is ready
        if self.config is not None:
            self.config.auth_session_secret.set(self.session_secret_key)

        # called when web app has started
        async def on_startup(app):
            # remember main event loop
            AsyncUtils.set_main_loop(asyncio.get_event_loop())

            if not self._network_ready:
                self.start_network_setup_in_background()

            # auto launch web browser
            if launch_browser:
                try:
                    protocol = "https" if use_https else "http"
                    webbrowser.open(f"{protocol}://127.0.0.1:{port}")
                except Exception:
                    print("failed to launch web browser")

            # start memory diagnostics periodic snapshot task
            if self._mem_diag and self._mem_diag.enabled:
                asyncio.create_task(self._memory_diag_snapshot_loop())

        # create and run web app
        app = web.Application(
            client_max_size=1024 * 1024 * 256,
        )  # allow large message exports with embedded attachments

        # setup session storage
        # aiohttp_session.setup must be called before other middlewares that use sessions
        setup_session(
            app,
            self._encrypted_cookie_storage(use_https),
        )

        # add other middlewares
        app.middlewares.extend(
            [
                sqlite_unavailable_middleware,
                auth_middleware,
                mime_type_middleware,
                security_middleware,
                csrf_middleware,
                ip_allowlist_middleware,
                demo_mode_middleware,
            ],
        )

        app.add_routes(routes)

        async def robots_txt_handler(_request):
            return web.Response(
                text="User-agent: *\nDisallow: /\n",
                content_type="text/plain; charset=utf-8",
            )

        app.router.add_get("/robots.txt", robots_txt_handler)

        # serve anything else from public folder
        # we use add_static here as it's more robust for serving directories
        public_dir = self.get_public_path()

        # Serve Reticulum docs from user-uploaded storage with a fallback to the
        # bundled offline copy shipped under <public>/reticulum-docs-bundled/current.
        # No remote network fallback exists, so users supply replacements via upload.
        async def reticulum_docs_handler(request):
            dm = self.docs_manager
            if dm is None:
                return web.json_response(
                    {"error": "Documentation unavailable"},
                    status=503,
                )
            path = request.match_info.get("filename", "manual/index.html")
            if not path:
                path = "manual/index.html"
            if path.endswith("/"):
                path += "index.html"

            resolved = dm.find_docs_file(path)
            if resolved is None:
                return web.json_response(
                    {"error": "Documentation not found"},
                    status=404,
                )
            return web.FileResponse(resolved)

        app.router.add_get("/reticulum-docs/{filename:.*}", reticulum_docs_handler)

        dm = self.docs_manager
        if (
            dm
            and dm.meshchatx_docs_dir
            and os.path.exists(dm.meshchatx_docs_dir)
            and not dm.meshchatx_docs_dir.startswith(public_dir)
        ):
            app.router.add_static(
                "/meshchatx-docs/",
                dm.meshchatx_docs_dir,
                name="meshchatx_docs_storage",
                follow_symlinks=True,
            )

        if os.path.exists(public_dir):
            app.router.add_static("/", public_dir, name="static", follow_symlinks=True)
        else:
            print(f"Warning: Static files directory not found at {public_dir}")

        app.on_shutdown.append(
            self.shutdown,
        )  # need to force close websockets and stop reticulum now
        app.on_startup.append(on_startup)

        protocol = "https" if use_https else "http"
        print(f"Starting web server on {protocol}://{host}:{port}", flush=True)

        # Start memory diagnostics if enabled
        if self._memory_diag_enabled:
            from meshchatx.src.backend.diagnostics import MemoryDiagnostics

            self._mem_diag = MemoryDiagnostics()
            self._mem_diag.start()
            print(
                "[mem_diag] Memory diagnostics enabled — "
                "see /api/v1/diagnostics/memory for reports",
            )

        if use_https and ssl_context:
            web.run_app(app, host=host, port=port, ssl_context=ssl_context)
        else:
            web.run_app(app, host=host, port=port)

    # auto backup loop
    async def auto_backup_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # wait 5 minutes before first backup
        await asyncio.sleep(300)

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                if not self.emergency:
                    print(
                        f"Performing scheduled auto-backup for {ctx.identity_hash}...",
                    )
                    max_count = ctx.config.backup_max_count.get()
                    ctx.database.backup_database(ctx.storage_path, max_count=max_count)
            except Exception as e:
                print(f"Auto-backup failed: {e}")

            # Sleep for 12 hours
            await asyncio.sleep(12 * 3600)

    async def local_message_retention_loop(self, session_id, context=None):
        from meshchatx.src.backend import local_message_retention as lmr

        ctx = context or self.current_context
        if not ctx:
            return
        await asyncio.sleep(lmr.LOCAL_RETENTION_STARTUP_GRACE_SECONDS)
        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                if not ctx.config.local_message_auto_delete_enabled.get():
                    await asyncio.sleep(300)
                    continue
                now = time.time()
                if not interval_action_due(
                    True,
                    ctx.config.local_message_auto_delete_last_run_at.get(),
                    lmr.RETENTION_CHECK_INTERVAL_SECONDS,
                    now,
                ):
                    await asyncio.sleep(60)
                    continue
                v = ctx.config.local_message_auto_delete_value.get() or 30
                u = ctx.config.local_message_auto_delete_unit.get() or "days"
                if ctx.message_router is not None:

                    def _cancel(h):
                        try:
                            ctx.message_router.cancel_outbound(h)
                        except Exception:
                            pass

                else:
                    _cancel = None
                lmr.apply_local_message_retention(
                    ctx.database.messages,
                    _cancel,
                    value=int(v),
                    unit=str(u),
                    now=now,
                )
                ctx.config.local_message_auto_delete_last_run_at.set(int(now))
            except Exception as e:
                print(f"local_message_retention_loop failed: {e}")
            await asyncio.sleep(60)

    async def telemetry_tracking_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                # Only run if telemetry is enabled globally
                if not ctx.config.telemetry_enabled.get():
                    await asyncio.sleep(60)
                    continue

                # Get all tracked peers
                tracked_peers = ctx.database.telemetry.get_tracked_peers()
                now = time.time()

                for peer in tracked_peers:
                    dest_hash = peer["destination_hash"]
                    interval = peer.get("interval_seconds", 60)
                    last_req = peer.get("last_request_at")

                    if last_req is None or now - last_req >= interval:
                        print(f"Sending telemetry request to tracked peer: {dest_hash}")
                        # Send telemetry request
                        await self.send_message(
                            destination_hash=dest_hash,
                            content="",
                            commands=[{SidebandCommands.TELEMETRY_REQUEST: 0}],
                            delivery_method="opportunistic",
                            no_display=False,
                            context=ctx,
                        )
                        # Update last request time
                        ctx.database.telemetry.update_last_request_at(dest_hash, now)

            except Exception as e:
                print(f"Telemetry tracking loop error: {e}")

            # Check every 10 seconds
            await asyncio.sleep(10)

    # handle announcing
    async def announce(self, context=None):
        if self.demo_mode:
            return
        ctx = context or self.current_context
        if not ctx:
            return

        # update last announced at timestamp
        ctx.config.last_announced_at.set(int(time.time()))

        # send announce for lxmf (ensuring name is updated before announcing)
        ctx.local_lxmf_destination.display_name = ctx.config.display_name.get()
        ctx.message_router.announce(destination_hash=ctx.local_lxmf_destination.hash)

        # send announce for local propagation node (if enabled)
        if ctx.config.lxmf_local_propagation_node_enabled.get():
            ctx.message_router.announce_propagation_node()

        # send announce for telephone (can be disabled to reduce unsolicited
        # incoming telephony link attempts from public lxst.telephony announces)
        if ctx.config.telephone_announce_enabled.get():
            ctx.telephone_manager.announce(display_name=ctx.config.display_name.get())

        # tell websocket clients we just announced
        await self.send_announced_to_websocket_clients(context=ctx)

    # handle syncing propagation nodes
    async def sync_propagation_nodes(self, context=None, force=False):
        ctx = context or self.current_context
        if not ctx:
            return False

        router = ctx.message_router
        if not router:
            return False

        outbound_node = router.get_outbound_propagation_node()
        if outbound_node is None:
            return False

        state = router.propagation_transfer_state
        if propagation_sync_idle_like(state):
            if state == router.PR_COMPLETE:
                with contextlib.suppress(Exception):
                    router.propagation_transfer_state = router.PR_IDLE
                    router.propagation_transfer_progress = 0.0
        elif not force:
            return False
        else:
            self.stop_propagation_node_sync(context=ctx)
            settle_deadline = time.monotonic() + 5.0
            while time.monotonic() < settle_deadline:
                if router.propagation_transfer_state == router.PR_IDLE:
                    break
                await asyncio.sleep(0.2)
            else:
                with contextlib.suppress(Exception):
                    router.propagation_transfer_state = router.PR_IDLE

        self._begin_propagation_sync_metrics(context=ctx)

        ctx.config.lxmf_preferred_propagation_node_last_synced_at.set(int(time.time()))
        local_propagation_destination = getattr(
            router,
            "propagation_destination",
            None,
        )
        local_propagation_hash = getattr(local_propagation_destination, "hash", None)
        if (
            isinstance(outbound_node, (bytes, bytearray))
            and isinstance(local_propagation_hash, (bytes, bytearray))
            and bytes(outbound_node) == bytes(local_propagation_hash)
        ):
            # Local node selected as preferred: no transport path lookup is needed.
            # Mark sync as complete immediately to avoid getting stuck in PR_PATH_REQUESTED.
            with contextlib.suppress(Exception):
                router.propagation_transfer_state = router.PR_COMPLETE
                router.propagation_transfer_progress = 1.0
                router.propagation_transfer_last_result = 0
            await self.send_config_to_websocket_clients(context=ctx)
            return True

        # Kick off the LXMF request on a worker thread. Identity.recall and link
        # setup can block on multiprocessing pipes. Running inline would stall the
        # HTTP handler and race with cancel_propagation_node_requests (EOFError).
        asyncio.create_task(self._request_propagation_node_messages(context=ctx))

        await self.send_config_to_websocket_clients(context=ctx)
        return True

    # helper to parse boolean from possible string or bool
    @staticmethod
    def _parse_bool(value):
        if value is None:
            return False
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    # Coerce untrusted config input to int. Returns None when the value
    # cannot be converted so update_config can skip or fall back instead of
    # raising on None/strings/lists received via the websocket API.
    @staticmethod
    def _coerce_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_optional_hex_color(value):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            if len(trimmed) == 7 and trimmed.startswith("#"):
                try:
                    int(trimmed[1:], 16)
                    return trimmed
                except ValueError:
                    return None
        return None

    async def update_config(self, data):
        # update display name in config
        if "display_name" in data and data["display_name"] != "":
            self.config.display_name.set(data["display_name"])
            # Update identity metadata cache
            self.update_identity_metadata_cache()

        # update theme in config
        if "theme" in data and data["theme"] != "":
            theme = data["theme"]
            if theme not in ("light", "dark", "system"):
                theme = "light"
            self.config.theme.set(theme)

        if "theme_preset" in data:
            preset = data["theme_preset"]
            if preset == "hister":
                preset = "neo_brutalist"
            if preset not in (
                "default",
                "high_contrast",
                "oled",
                "solarized",
                "nord",
                "gruvbox",
                "catppuccin",
                "dracula",
                "rose_pine",
                "forest",
                "midnight",
                "warm_paper",
                "tokyo",
                "atom_one",
                "neo_brutalist",
                "custom",
            ):
                preset = "default"
            self.config.theme_preset.set(preset)

        if "accent_color" in data:
            self.config.accent_color.set(
                self._normalize_optional_hex_color(data["accent_color"]),
            )

        if "custom_canvas_color" in data:
            self.config.custom_canvas_color.set(
                self._normalize_optional_hex_color(data["custom_canvas_color"]),
            )

        if "custom_surface_color" in data:
            self.config.custom_surface_color.set(
                self._normalize_optional_hex_color(data["custom_surface_color"]),
            )

        # update language in config
        if "language" in data and data["language"] != "":
            self.config.language.set(data["language"])

        # update auto announce interval
        if "auto_announce_interval_seconds" in data:
            # auto auto announce interval
            auto_announce_interval_seconds = self._coerce_int(
                data["auto_announce_interval_seconds"],
            )
            if auto_announce_interval_seconds is None:
                auto_announce_interval_seconds = (
                    self.config.auto_announce_interval_seconds.get()
                )
            self.config.auto_announce_interval_seconds.set(
                auto_announce_interval_seconds,
            )

            # enable or disable auto announce based on interval
            if auto_announce_interval_seconds > 0:
                self.config.auto_announce_enabled.set(True)
            else:
                self.config.auto_announce_enabled.set(False)

        if "auto_resend_failed_messages_when_announce_received" in data:
            value = self._parse_bool(
                data["auto_resend_failed_messages_when_announce_received"],
            )
            self.config.auto_resend_failed_messages_when_announce_received.set(value)

        if "allow_auto_resending_failed_messages_with_attachments" in data:
            value = self._parse_bool(
                data["allow_auto_resending_failed_messages_with_attachments"],
            )
            self.config.allow_auto_resending_failed_messages_with_attachments.set(value)

        if "auto_send_failed_messages_to_propagation_node" in data:
            value = self._parse_bool(
                data["auto_send_failed_messages_to_propagation_node"],
            )
            self.config.auto_send_failed_messages_to_propagation_node.set(value)

        if "delivery_helptips_enabled" in data:
            value = self._parse_bool(data["delivery_helptips_enabled"])
            self.config.delivery_helptips_enabled.set(value)

        if "lxmf_delivery_transfer_limit_in_bytes" in data:
            value = self._coerce_int(data["lxmf_delivery_transfer_limit_in_bytes"])
            if value is None:
                value = self.config.lxmf_delivery_transfer_limit_in_bytes.get()
            value = max(1000, min(value, 1000 * 1000 * 1000))
            self.config.lxmf_delivery_transfer_limit_in_bytes.set(value)
            self.message_router.delivery_per_transfer_limit = value / 1000

        if "lxmf_propagation_transfer_limit_in_bytes" in data:
            value = self._coerce_int(data["lxmf_propagation_transfer_limit_in_bytes"])
            if value is None:
                value = self.config.lxmf_propagation_transfer_limit_in_bytes.get()
            value = max(1000, min(value, 1000 * 1000 * 100))
            self.config.lxmf_propagation_transfer_limit_in_bytes.set(value)
            self.message_router.propagation_per_transfer_limit = value / 1000
            if self.config.lxmf_local_propagation_node_enabled.get():
                self.message_router.announce_propagation_node()

        if "lxmf_propagation_sync_limit_in_bytes" in data:
            value = self._coerce_int(data["lxmf_propagation_sync_limit_in_bytes"])
            if value is None:
                value = self.config.lxmf_propagation_sync_limit_in_bytes.get()
            value = max(1000, min(value, 1000 * 1000 * 500))
            self.config.lxmf_propagation_sync_limit_in_bytes.set(value)
            self.message_router.propagation_per_sync_limit = value / 1000

        if "show_suggested_community_interfaces" in data:
            value = self._parse_bool(data["show_suggested_community_interfaces"])
            self.config.show_suggested_community_interfaces.set(value)

        _announce_int_fields = [
            ("announce_max_stored_lxmf_delivery", 1, 1_000_000),
            ("announce_max_stored_nomadnetwork_node", 1, 1_000_000),
            ("announce_max_stored_lxmf_propagation", 1, 1_000_000),
            ("announce_max_stored_map_data", 1, 1_000_000),
            ("announce_fetch_limit_lxmf_delivery", 1, 100_000),
            ("announce_fetch_limit_nomadnetwork_node", 1, 100_000),
            ("announce_fetch_limit_lxmf_propagation", 1, 100_000),
            ("announce_fetch_limit_map_data", 1, 100_000),
            ("announce_search_max_fetch", 100, 10_000),
            ("discovered_interfaces_max_return", 1, 50_000),
        ]
        for key, lo, hi in _announce_int_fields:
            if key not in data:
                continue
            val = data[key]
            if val is None or val == "":
                getattr(self.config, key).set(None)
                continue
            try:
                v = int(val)
                v = max(lo, min(hi, v))
                getattr(self.config, key).set(v)
            except (TypeError, ValueError):
                getattr(self.config, key).set(None)

        if "lxmf_preferred_propagation_node_destination_hash" in data:
            # update config value
            value = data["lxmf_preferred_propagation_node_destination_hash"]
            self.config.lxmf_preferred_propagation_node_destination_hash.set(value)

            # update active propagation node
            self.set_active_propagation_node(value)

        if "lxmf_preferred_propagation_node_auto_select" in data:
            value = self._parse_bool(
                data["lxmf_preferred_propagation_node_auto_select"],
            )
            self.config.lxmf_preferred_propagation_node_auto_select.set(value)

        # update inbound stamp cost (for direct delivery messages)
        if "lxmf_inbound_stamp_cost" in data:
            value = self._coerce_int(data["lxmf_inbound_stamp_cost"])
            if value is None:
                value = self.config.lxmf_inbound_stamp_cost.get()
            # 0 disables inbound stamps, and otherwise clamp to 1-254 (LXMF/LXMRouter)
            if value < 0:
                value = 0
            elif value >= 255:
                value = 254
            # If block strangers is active, store the desired value for later restore
            # but keep the enforced max cost active
            if self.config.block_all_from_strangers.get():
                self.config.lxmf_inbound_stamp_cost_before_block.set(value)
            else:
                self.config.lxmf_inbound_stamp_cost.set(value)
                # update the inbound stamp cost on the delivery destination
                self.message_router.set_inbound_stamp_cost(
                    self.local_lxmf_destination.hash,
                    value,
                )
                if value > 0:
                    self.message_router.enforce_stamps()
                elif hasattr(self.message_router, "ignore_stamps"):
                    self.message_router.ignore_stamps()
                # re-announce to update the stamp cost in announces
                self.local_lxmf_destination.display_name = (
                    self.config.display_name.get()
                )
                self.message_router.announce(
                    destination_hash=self.local_lxmf_destination.hash,
                )

        # update propagation node stamp cost (for messages propagated through your node)
        if "lxmf_propagation_node_stamp_cost" in data:
            value = self._coerce_int(data["lxmf_propagation_node_stamp_cost"])
            if value is None:
                value = self.config.lxmf_propagation_node_stamp_cost.get()
            # validate stamp cost (must be at least 13, per LXMF minimum)
            if value < 13:
                value = 13
            elif value >= 255:
                value = 254
            self.config.lxmf_propagation_node_stamp_cost.set(value)
            # update the propagation stamp cost on the router
            self.message_router.propagation_stamp_cost = value
            # re-announce propagation node if enabled
            if self.config.lxmf_local_propagation_node_enabled.get():
                self.message_router.announce_propagation_node()

        if "lxmf_propagation_sequential_validation" in data:
            value = self._parse_bool(
                data["lxmf_propagation_sequential_validation"],
            )
            self.config.lxmf_propagation_sequential_validation.set(value)
            if self.message_router is not None:
                self.message_router.propagation_sequential_validation = value

        if "lxmf_propagation_static_peers_bypass_sequential" in data:
            value = self._parse_bool(
                data["lxmf_propagation_static_peers_bypass_sequential"],
            )
            self.config.lxmf_propagation_static_peers_bypass_sequential.set(value)
            if self.message_router is not None:
                self.message_router.propagation_static_peer_sequential = not value

        if "lxmf_propagation_max_inbound_syncs" in data:
            value = self._coerce_int(data["lxmf_propagation_max_inbound_syncs"])
            if value is None:
                value = self.config.lxmf_propagation_max_inbound_syncs.get()
            if value < 1:
                value = 1
            elif value > 64:
                value = 64
            self.config.lxmf_propagation_max_inbound_syncs.set(value)
            if self.message_router is not None:
                self.message_router.propagation_max_inbound_syncs = value

        # update auto sync interval
        if "lxmf_preferred_propagation_node_auto_sync_interval_seconds" in data:
            value = self._coerce_int(
                data["lxmf_preferred_propagation_node_auto_sync_interval_seconds"],
            )
            if value is None:
                value = self.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
            self.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set(
                value,
            )

        if "lxmf_local_propagation_node_enabled" in data:
            # update config value
            value = self._parse_bool(data["lxmf_local_propagation_node_enabled"])
            self.config.lxmf_local_propagation_node_enabled.set(value)

            # enable or disable local propagation node
            self.enable_local_propagation_node(value)

        # update lxmf user icon name in config
        if "lxmf_user_icon_name" in data:
            self.config.lxmf_user_icon_name.set(data["lxmf_user_icon_name"])
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update lxmf user icon foreground colour in config
        if "lxmf_user_icon_foreground_colour" in data:
            self.config.lxmf_user_icon_foreground_colour.set(
                data["lxmf_user_icon_foreground_colour"],
            )
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update lxmf user icon background colour in config
        if "lxmf_user_icon_background_colour" in data:
            self.config.lxmf_user_icon_background_colour.set(
                data["lxmf_user_icon_background_colour"],
            )
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update archiver settings
        if "page_archiver_enabled" in data:
            self.config.page_archiver_enabled.set(
                self._parse_bool(data["page_archiver_enabled"]),
            )

        if "page_archiver_max_versions" in data:
            value = self._coerce_int(data["page_archiver_max_versions"])
            if value is not None:
                self.config.page_archiver_max_versions.set(value)

        if "archives_max_storage_gb" in data:
            value = self._coerce_int(data["archives_max_storage_gb"])
            if value is not None:
                self.config.archives_max_storage_gb.set(value)

        if "backup_max_count" in data:
            try:
                value = int(data["backup_max_count"])
            except (TypeError, ValueError):
                value = self.config.backup_max_count.default_value
            value = max(1, min(value, 50))
            self.config.backup_max_count.set(value)

        # update crawler settings
        if "crawler_enabled" in data:
            self.config.crawler_enabled.set(self._parse_bool(data["crawler_enabled"]))

        if "crawler_max_retries" in data:
            try:
                value = int(data["crawler_max_retries"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_retries.default_value
            self.config.crawler_max_retries.set(value)

        if "crawler_retry_delay_seconds" in data:
            try:
                value = int(data["crawler_retry_delay_seconds"])
            except (TypeError, ValueError):
                value = self.config.crawler_retry_delay_seconds.default_value
            self.config.crawler_retry_delay_seconds.set(value)

        if "crawler_max_concurrent" in data:
            try:
                value = int(data["crawler_max_concurrent"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_concurrent.default_value
            self.config.crawler_max_concurrent.set(value)

        if "crawler_max_hops" in data:
            try:
                value = int(data["crawler_max_hops"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_hops.default_value
            self.config.crawler_max_hops.set(max(1, min(16, value)))

        if "crawler_max_rtt_ms" in data:
            try:
                value = int(data["crawler_max_rtt_ms"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_rtt_ms.default_value
            self.config.crawler_max_rtt_ms.set(max(100, min(60000, value)))

        if "crawler_max_depth" in data:
            try:
                value = int(data["crawler_max_depth"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_depth.default_value
            self.config.crawler_max_depth.set(max(0, min(2, value)))

        if "crawler_max_pages_per_node" in data:
            try:
                value = int(data["crawler_max_pages_per_node"])
            except (TypeError, ValueError):
                value = self.config.crawler_max_pages_per_node.default_value
            self.config.crawler_max_pages_per_node.set(max(1, min(20, value)))

        if "crawler_requests_per_day_per_node" in data:
            try:
                value = int(data["crawler_requests_per_day_per_node"])
            except (TypeError, ValueError):
                value = self.config.crawler_requests_per_day_per_node.default_value
            self.config.crawler_requests_per_day_per_node.set(max(1, min(3, value)))

        if "crawler_refresh_days" in data:
            try:
                value = int(data["crawler_refresh_days"])
            except (TypeError, ValueError):
                value = self.config.crawler_refresh_days.default_value
            self.config.crawler_refresh_days.set(max(1, min(365, value)))

        if "auth_enabled" in data:
            value = self._parse_bool(data["auth_enabled"])
            self.config.auth_enabled.set(value)

            # if disabling auth, also remove the password hash from config
            if not value:
                self.config.auth_password_hash.set(None)

        if "privacy_mode_enabled" in data:
            self.config.privacy_mode_enabled.set(
                self._parse_bool(data["privacy_mode_enabled"]),
            )

        if "multi_session_warning_enabled" in data:
            self.config.multi_session_warning_enabled.set(
                self._parse_bool(data["multi_session_warning_enabled"]),
            )

        # update map settings
        if "map_offline_enabled" in data:
            self.config.map_offline_enabled.set(
                self._parse_bool(data["map_offline_enabled"]),
            )

        if "map_default_lat" in data:
            self.config.map_default_lat.set(str(data["map_default_lat"]))

        if "map_default_lon" in data:
            self.config.map_default_lon.set(str(data["map_default_lon"]))

        if "map_default_zoom" in data:
            try:
                value = int(data["map_default_zoom"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                self.config.map_default_zoom.set(value)

        if "map_mbtiles_dir" in data:
            self.config.map_mbtiles_dir.set(data["map_mbtiles_dir"])

        if "map_tile_cache_enabled" in data:
            self.config.map_tile_cache_enabled.set(
                self._parse_bool(data["map_tile_cache_enabled"]),
            )

        if "map_tile_server_url" in data:
            self.config.map_tile_server_url.set(data["map_tile_server_url"])

        if "map_nominatim_api_url" in data:
            self.config.map_nominatim_api_url.set(data["map_nominatim_api_url"])

        for overlay_key in CONFIG_CLAMPS:
            if overlay_key in data:
                try:
                    value = int(data[overlay_key])
                except (TypeError, ValueError):
                    continue
                getattr(self.config, overlay_key).set(
                    clamp_overlay_config_value(overlay_key, value),
                )

        # update location settings
        if "location_source" in data:
            self.config.location_source.set(data["location_source"])

        if "location_manual_lat" in data:
            self.config.location_manual_lat.set(str(data["location_manual_lat"]))

        if "location_manual_lon" in data:
            self.config.location_manual_lon.set(str(data["location_manual_lon"]))

        if "location_manual_alt" in data:
            self.config.location_manual_alt.set(str(data["location_manual_alt"]))

        if "telemetry_enabled" in data:
            self.config.telemetry_enabled.set(
                self._parse_bool(data["telemetry_enabled"]),
            )

        if "nomad_render_markdown_enabled" in data:
            self.config.nomad_render_markdown_enabled.set(
                self._parse_bool(data["nomad_render_markdown_enabled"]),
            )

        if "nomad_render_html_enabled" in data:
            self.config.nomad_render_html_enabled.set(
                self._parse_bool(data["nomad_render_html_enabled"]),
            )

        if "nomad_render_plaintext_enabled" in data:
            self.config.nomad_render_plaintext_enabled.set(
                self._parse_bool(data["nomad_render_plaintext_enabled"]),
            )

        if "nomad_micron_wasm_enabled" in data:
            self.config.nomad_micron_wasm_enabled.set(
                self._parse_bool(data["nomad_micron_wasm_enabled"]),
            )
            if not self.config.nomad_micron_wasm_enabled.get():
                self.config.nomad_micron_default_engine.set("js")

        if "nomad_micron_default_engine" in data:
            if self.config.nomad_micron_wasm_enabled.get():
                raw = str(data["nomad_micron_default_engine"] or "").strip().lower()
                self.config.nomad_micron_default_engine.set(
                    "wasm" if raw == "wasm" else "js",
                )

        if "nomad_default_page_path" in data:
            from meshchatx.src.backend.page_node import is_allowed_page_filename

            raw = data["nomad_default_page_path"]
            if raw is None or str(raw).strip() == "":
                self.config.nomad_default_page_path.set("/page/index.mu")
            else:
                s = str(raw).strip()
                if s.startswith("/page/"):
                    base = s[6:]
                    if (
                        base
                        and "/" not in base
                        and ".." not in base
                        and is_allowed_page_filename(base)
                    ):
                        self.config.nomad_default_page_path.set(s)

        if "local_message_auto_delete_enabled" in data:
            self.config.local_message_auto_delete_enabled.set(
                self._parse_bool(data["local_message_auto_delete_enabled"]),
            )
        if "message_blocklist_enabled" in data:
            self.config.message_blocklist_enabled.set(
                self._parse_bool(data["message_blocklist_enabled"]),
            )
        if (
            "local_message_auto_delete_value" in data
            or "local_message_auto_delete_unit" in data
        ):
            from meshchatx.src.backend.local_message_retention import (
                MAX_VALUE_DAYS,
                MAX_VALUE_MONTHS,
                normalize_unit,
            )

            u_str = str(
                data.get("local_message_auto_delete_unit")
                or self.config.local_message_auto_delete_unit.get()
                or "days",
            )
            u_norm = normalize_unit(u_str)
            if "local_message_auto_delete_unit" in data:
                self.config.local_message_auto_delete_unit.set(u_norm)
            v_raw = data.get(
                "local_message_auto_delete_value",
                self.config.local_message_auto_delete_value.get(),
            )
            try:
                v = int(v_raw)
            except (TypeError, ValueError):
                v = 30
            v = max(1, v)
            v = min(v, MAX_VALUE_MONTHS if u_norm == "months" else MAX_VALUE_DAYS)
            self.config.local_message_auto_delete_value.set(v)

        if "block_attachments_from_strangers" in data:
            self.config.block_attachments_from_strangers.set(
                self._parse_bool(data["block_attachments_from_strangers"]),
            )

        if "block_all_from_strangers" in data:
            new_value = self._parse_bool(data["block_all_from_strangers"])
            old_value = self.config.block_all_from_strangers.get()
            self.config.block_all_from_strangers.set(new_value)
            if new_value and not old_value:
                # Enabling block strangers: save current stamp cost and set to max
                current_cost = self.config.lxmf_inbound_stamp_cost.get()
                if not isinstance(current_cost, int):
                    current_cost = 0
                if current_cost < 0:
                    current_cost = 0
                elif current_cost > 254:
                    current_cost = 254
                self.config.lxmf_inbound_stamp_cost_before_block.set(current_cost)
                self.config.lxmf_inbound_stamp_cost.set(254)
                if self.message_router and self.local_lxmf_destination:
                    self.message_router.set_inbound_stamp_cost(
                        self.local_lxmf_destination.hash,
                        254,
                    )
                    self.message_router.enforce_stamps()
                    self.local_lxmf_destination.display_name = (
                        self.config.display_name.get()
                    )
                    self.message_router.announce(
                        destination_hash=self.local_lxmf_destination.hash,
                    )
            elif not new_value and old_value:
                # Disabling block strangers: restore previous stamp cost.
                # Zero is a valid prior cost (stamps off). Only fall back to 8
                # when no prior cost was saved (sentinel outside 0..254).
                saved = self.config.lxmf_inbound_stamp_cost_before_block.get()
                if isinstance(saved, int) and 0 <= saved <= 254:
                    restore_cost = saved
                else:
                    restore_cost = 8
                self.config.lxmf_inbound_stamp_cost.set(restore_cost)
                self.config.lxmf_inbound_stamp_cost_before_block.set(-1)
                if self.message_router and self.local_lxmf_destination:
                    self.message_router.set_inbound_stamp_cost(
                        self.local_lxmf_destination.hash,
                        restore_cost,
                    )
                    if restore_cost > 0:
                        self.message_router.enforce_stamps()
                    elif hasattr(self.message_router, "ignore_stamps"):
                        self.message_router.ignore_stamps()
                    self.local_lxmf_destination.display_name = (
                        self.config.display_name.get()
                    )
                    self.message_router.announce(
                        destination_hash=self.local_lxmf_destination.hash,
                    )
            self.sync_telephone_call_policy()

        # update flood protection settings
        if "lxmf_flood_protection_enabled" in data:
            self.config.lxmf_flood_protection_enabled.set(
                self._parse_bool(data["lxmf_flood_protection_enabled"]),
            )
        if "lxmf_flood_threshold_per_minute" in data:
            try:
                value = int(data["lxmf_flood_threshold_per_minute"])
                value = max(1, min(value, 1000))
                self.config.lxmf_flood_threshold_per_minute.set(value)
            except (TypeError, ValueError):
                pass
        if "lxmf_flood_max_stamp_cost" in data:
            try:
                value = int(data["lxmf_flood_max_stamp_cost"])
                value = max(1, min(value, 254))
                self.config.lxmf_flood_max_stamp_cost.set(value)
            except (TypeError, ValueError):
                pass
        if "lxmf_flood_cooldown_seconds" in data:
            try:
                value = int(data["lxmf_flood_cooldown_seconds"])
                value = max(30, min(value, 3600))
                self.config.lxmf_flood_cooldown_seconds.set(value)
            except (TypeError, ValueError):
                pass

        if "show_unknown_contact_banner" in data:
            self.config.show_unknown_contact_banner.set(
                self._parse_bool(data["show_unknown_contact_banner"]),
            )

        if "warn_on_stranger_links" in data:
            self.config.warn_on_stranger_links.set(
                self._parse_bool(data["warn_on_stranger_links"]),
            )

        # update banishment settings
        if "banished_effect_enabled" in data:
            self.config.banished_effect_enabled.set(
                self._parse_bool(data["banished_effect_enabled"]),
            )

        if "banished_text" in data:
            self.config.banished_text.set(data["banished_text"])

        if "banished_color" in data:
            self.config.banished_color.set(data["banished_color"])

        if "message_font_size" in data:
            try:
                value = int(data["message_font_size"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                self.config.message_font_size.set(value)

        if "messages_sidebar_position" in data:
            raw = data["messages_sidebar_position"]
            if raw is not None:
                s = str(raw).strip().lower()
                if s in ("left", "right"):
                    self.config.messages_sidebar_position.set(s)

        if "app_sidebar_layout" in data:
            raw = data["app_sidebar_layout"]
            if raw is not None:
                s = str(raw).strip().lower()
                if s in ("grouped", "classic"):
                    self.config.app_sidebar_layout.set(s)

        if "message_icon_size" in data:
            try:
                value = int(data["message_icon_size"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                value = max(12, min(value, 96))
                self.config.message_icon_size.set(value)

        if "ui_transparency" in data:
            try:
                value = int(data["ui_transparency"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                self.config.ui_transparency.set(max(0, min(value, 100)))

        if "ui_glass_enabled" in data:
            self.config.ui_glass_enabled.set(
                self._parse_bool(data["ui_glass_enabled"]),
            )

        if "messages_multi_pane_enabled" in data:
            self.config.messages_multi_pane_enabled.set(
                self._parse_bool(data["messages_multi_pane_enabled"]),
            )

        if "nomad_tabs_enabled" in data:
            self.config.nomad_tabs_enabled.set(
                self._parse_bool(data["nomad_tabs_enabled"]),
            )
        if "rrc_enabled" in data:
            self.config.rrc_enabled.set(self._parse_bool(data["rrc_enabled"]))
        if "rrc_unread_badges_enabled" in data:
            self.config.rrc_unread_badges_enabled.set(
                self._parse_bool(data["rrc_unread_badges_enabled"]),
            )

        if "message_outbound_bubble_color" in data:
            self.config.message_outbound_bubble_color.set(
                data["message_outbound_bubble_color"],
            )

        if "message_inbound_bubble_color" in data:
            self.config.message_inbound_bubble_color.set(
                data["message_inbound_bubble_color"],
            )

        if "message_failed_bubble_color" in data:
            self.config.message_failed_bubble_color.set(
                data["message_failed_bubble_color"],
            )

        if "message_waiting_bubble_color" in data:
            self.config.message_waiting_bubble_color.set(
                data["message_waiting_bubble_color"],
            )

        # update desktop settings
        if "desktop_open_calls_in_separate_window" in data:
            self.config.desktop_open_calls_in_separate_window.set(
                self._parse_bool(data["desktop_open_calls_in_separate_window"]),
            )

        if "desktop_hardware_acceleration_enabled" in data:
            enabled = self._parse_bool(data["desktop_hardware_acceleration_enabled"])
            self.config.desktop_hardware_acceleration_enabled.set(enabled)

            # write flag for electron to read on next launch
            try:
                disable_gpu_file = os.path.join(self.storage_dir, "disable-gpu")
                if not enabled:
                    with open(disable_gpu_file, "w") as f:
                        f.write("true")
                elif os.path.exists(disable_gpu_file):
                    os.remove(disable_gpu_file)
            except Exception as e:
                print(f"Failed to update GPU disable flag: {e}")

        if "blackhole_integration_enabled" in data:
            value = self._parse_bool(data["blackhole_integration_enabled"])
            self.config.blackhole_integration_enabled.set(value)

        for _k in (
            "announce_store_lxmf_delivery",
            "announce_store_lxst_telephony",
            "announce_store_nomadnetwork_node",
            "announce_store_lxmf_propagation",
            "announce_store_map_data",
        ):
            if _k in data:
                getattr(self.config, _k).set(self._parse_bool(data[_k]))

        # update csp extra sources
        if "csp_extra_connect_src" in data:
            self.config.csp_extra_connect_src.set(data["csp_extra_connect_src"])
        if "csp_extra_img_src" in data:
            self.config.csp_extra_img_src.set(data["csp_extra_img_src"])
        if "csp_extra_frame_src" in data:
            self.config.csp_extra_frame_src.set(data["csp_extra_frame_src"])
        if "csp_extra_script_src" in data:
            self.config.csp_extra_script_src.set(data["csp_extra_script_src"])
        if "csp_extra_style_src" in data:
            self.config.csp_extra_style_src.set(data["csp_extra_style_src"])

        # update voicemail settings
        if "voicemail_enabled" in data:
            self.config.voicemail_enabled.set(
                self._parse_bool(data["voicemail_enabled"]),
            )

        if "voicemail_greeting" in data:
            self.config.voicemail_greeting.set(data["voicemail_greeting"])

        if "voicemail_auto_answer_delay_seconds" in data:
            value = self._coerce_int(data["voicemail_auto_answer_delay_seconds"])
            if value is not None:
                self.config.voicemail_auto_answer_delay_seconds.set(value)

        if "voicemail_max_recording_seconds" in data:
            value = self._coerce_int(data["voicemail_max_recording_seconds"])
            if value is not None:
                self.config.voicemail_max_recording_seconds.set(value)

        if "voicemail_tts_speed" in data:
            value = self._coerce_int(data["voicemail_tts_speed"])
            if value is not None:
                self.config.voicemail_tts_speed.set(value)

        if "voicemail_tts_pitch" in data:
            value = self._coerce_int(data["voicemail_tts_pitch"])
            if value is not None:
                self.config.voicemail_tts_pitch.set(value)

        if "voicemail_tts_voice" in data:
            self.config.voicemail_tts_voice.set(data["voicemail_tts_voice"])

        if "voicemail_tts_word_gap" in data:
            value = self._coerce_int(data["voicemail_tts_word_gap"])
            if value is not None:
                self.config.voicemail_tts_word_gap.set(value)

        # update ringtone settings
        if "custom_ringtone_enabled" in data:
            self.config.custom_ringtone_enabled.set(
                self._parse_bool(data["custom_ringtone_enabled"]),
            )
        if "ringtone_preferred_id" in data:
            value = self._coerce_int(data["ringtone_preferred_id"])
            if value is not None:
                self.config.ringtone_preferred_id.set(value)
        if "ringtone_volume" in data:
            value = self._coerce_int(data["ringtone_volume"])
            if value is not None:
                self.config.ringtone_volume.set(value)

        if "notification_sound_enabled" in data:
            self.config.notification_sound_enabled.set(
                self._parse_bool(data["notification_sound_enabled"]),
            )
        if "notification_sound_preferred_id" in data:
            value = self._coerce_int(data["notification_sound_preferred_id"])
            if value is not None:
                self.config.notification_sound_preferred_id.set(value)
        if "notification_sound_volume" in data:
            value = self._coerce_int(data["notification_sound_volume"])
            if value is not None:
                self.config.notification_sound_volume.set(value)

        if "do_not_disturb_enabled" in data:
            self.config.do_not_disturb_enabled.set(
                self._parse_bool(data["do_not_disturb_enabled"]),
            )
            self.sync_telephone_call_policy()

        if "telephone_enabled" in data:
            value = self._parse_bool(data["telephone_enabled"])
            self.config.telephone_enabled.set(value)
            if (
                not value
                and self.telephone_manager
                and self.telephone_manager.telephone
            ):
                self.telephone_manager.teardown()
            elif value and self.telephone_manager:
                self.telephone_manager.init_telephone()
                self.sync_telephone_call_policy()

        if "telephone_allow_calls_from_contacts_only" in data:
            self.config.telephone_allow_calls_from_contacts_only.set(
                self._parse_bool(data["telephone_allow_calls_from_contacts_only"]),
            )
            self.sync_telephone_call_policy()

        if "telephone_announce_enabled" in data:
            self.config.telephone_announce_enabled.set(
                self._parse_bool(data["telephone_announce_enabled"]),
            )

        if "call_recording_enabled" in data:
            value = self._parse_bool(data["call_recording_enabled"])
            self.config.call_recording_enabled.set(value)
            # if a call is active, start or stop recording immediately
            if (
                self.telephone_manager
                and self.telephone_manager.telephone
                and self.telephone_manager.telephone.active_call
            ):
                if value:
                    self.telephone_manager.start_recording()
                else:
                    self.telephone_manager.stop_recording()

        if "telephone_tone_generator_enabled" in data:
            self.config.telephone_tone_generator_enabled.set(
                self._parse_bool(data["telephone_tone_generator_enabled"]),
            )

        if "telephone_tone_generator_volume" in data:
            value = self._coerce_int(data["telephone_tone_generator_volume"])
            if value is not None:
                self.config.telephone_tone_generator_volume.set(value)

        if "telephone_audio_profile_id" in data:
            profile_id = self._coerce_int(data["telephone_audio_profile_id"])
            if profile_id is None:
                profile_id = self.config.telephone_audio_profile_id.get()
            self.config.telephone_audio_profile_id.set(profile_id)
            if self.telephone_manager:
                await asyncio.to_thread(
                    self.telephone_manager.apply_preferred_profile,
                    profile_id,
                )

        if "telephone_call_mode_id" in data:
            mode_id = self._coerce_int(data["telephone_call_mode_id"])
            if mode_id is None:
                mode_id = self.config.telephone_call_mode_id.get()
            self.config.telephone_call_mode_id.set(mode_id)
            if self.telephone_manager:
                await asyncio.to_thread(
                    self.telephone_manager.apply_preferred_mode,
                    mode_id,
                )

        if "telephone_web_audio_enabled" in data:
            self.config.telephone_web_audio_enabled.set(
                self._parse_bool(data["telephone_web_audio_enabled"]),
            )

        if "telephone_web_audio_allow_fallback" in data:
            self.config.telephone_web_audio_allow_fallback.set(
                self._parse_bool(data["telephone_web_audio_allow_fallback"]),
            )

        if "translator_argos_enabled" in data:
            v = self._parse_bool(data["translator_argos_enabled"])
            self.config.translator_argos_enabled.set(v)
            if hasattr(self, "translator_handler"):
                self.translator_handler.translator_argos_enabled = v

        if "translator_libretranslate_enabled" in data:
            v = self._parse_bool(data["translator_libretranslate_enabled"])
            self.config.translator_libretranslate_enabled.set(v)
            if hasattr(self, "translator_handler"):
                self.translator_handler.translator_libretranslate_enabled = v

        if "translator_enabled" in data:
            v = self._parse_bool(data["translator_enabled"])
            self.config.translator_argos_enabled.set(v)
            self.config.translator_libretranslate_enabled.set(v)
            if hasattr(self, "translator_handler"):
                th = self.translator_handler
                th.translator_argos_enabled = v
                th.translator_libretranslate_enabled = v

        if "libretranslate_url" in data:
            value = data["libretranslate_url"]
            self.config.libretranslate_url.set(value)
            if hasattr(self, "translator_handler"):
                self.translator_handler.libretranslate_url = value

        if "libretranslate_api_key" in data:
            from meshchatx.src.backend.translator_handler import (
                _normalize_optional_libretranslate_api_key,
            )

            raw = data["libretranslate_api_key"]
            if raw is None or raw == "":
                norm = None
            else:
                norm = _normalize_optional_libretranslate_api_key(str(raw))

            self.config.libretranslate_api_key.set(norm)
            if hasattr(self, "translator_handler"):
                self.translator_handler.libretranslate_api_key = norm

        # send config to websocket clients
        await self.send_config_to_websocket_clients()
        if "multi_session_warning_enabled" in data:
            await self.send_active_sessions_to_websocket_clients()

    # converts nomadnetwork page variables from a string to a map
    # converts: "field1=123|field2=456"
    # to the following map:
    # - var_field1: 123
    # - var_field2: 456
    def archive_page(
        self,
        destination_hash: str,
        page_path: str,
        content: str,
        is_manual: bool = False,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return None
        return ctx.nomadnet_manager.archive_page(
            destination_hash,
            page_path,
            content,
            is_manual,
        )

    def get_archived_page_versions(self, destination_hash: str, page_path: str):
        return self.nomadnet_manager.get_archived_page_versions(
            destination_hash,
            page_path,
        )

    def flush_all_archived_pages(self):
        return self.nomadnet_manager.flush_all_archived_pages()

    async def _websocket_session_authorized(self, client) -> bool:
        if not self.auth_enabled:
            return True
        request = getattr(client, "_meshchatx_request", None)
        if request is None:
            request = getattr(client, "request", None)
        if request is None:
            return False
        try:
            session = await get_session(request)
        except Exception:
            return False
        identity_hash = self.identity.hash.hex() if self.identity else None
        return bool(
            session.get("authenticated", False)
            and identity_hash
            and session.get("identity_hash") == identity_hash,
        )

    # handle data received from websocket client
    async def on_websocket_data_received(self, client, data):
        from meshchatx.src.backend.http.ws.dispatch import dispatch_websocket_data

        await dispatch_websocket_data(self, client, data)

    def _track_rns_link_task(self, client, task: asyncio.Task) -> None:
        bucket = self._rns_link_tasks.get(client)
        if bucket is None:
            bucket = set()
            self._rns_link_tasks[client] = bucket
        bucket.add(task)
        task.add_done_callback(lambda t, c=client: self._untrack_rns_link_task(c, t))

    def _untrack_rns_link_task(self, client, task: asyncio.Task) -> None:
        bucket = self._rns_link_tasks.get(client)
        if not bucket:
            return
        bucket.discard(task)
        if not bucket:
            self._rns_link_tasks.pop(client, None)

    def _cancel_rns_link_tasks_for_client(self, client) -> None:
        bucket = self._rns_link_tasks.pop(client, None)
        if bucket:
            for task in bucket:
                if not task.done():
                    task.cancel()
        stale_keys = [k for k in self._rns_request_receipts if k[0] is client]
        for key in stale_keys:
            self._rns_request_receipts.pop(key, None)

    @staticmethod
    def _rns_link_parse_dest_aspect(data):
        dest_hex = data.get("destination_hash")
        aspect = data.get("aspect")
        if not dest_hex or not aspect:
            return None, None, "missing_destination_or_aspect"
        dest = hex_identifier_to_bytes(dest_hex if isinstance(dest_hex, str) else None)
        if dest is None or len(dest) != 16:
            return None, None, "invalid_destination_hash"
        return dest, aspect, None

    @staticmethod
    async def _rns_link_send(client, payload):
        try:
            await client.send_str(json.dumps(payload))
        except Exception as e:
            print(f"rns.link reply failed: {e}")

    async def _handle_rns_link_open(self, client, data):
        request_id = data.get("request_id")
        dest_hash, aspect, err = self._rns_link_parse_dest_aspect(data)
        if err:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.open",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": err,
                },
            )
            return
        auto_identify = bool(data.get("auto_identify", False))

        def on_phase(phase):
            AsyncUtils.run_async(
                self._rns_link_send(
                    client,
                    {
                        "type": "rns.link.open",
                        "request_id": request_id,
                        "status": "phase",
                        "phase": phase,
                        "destination_hash": dest_hash.hex(),
                        "aspect": aspect,
                    },
                ),
            )

        link, identified, failure_reason = await self.rns_link_manager.open_link(
            dest_hash,
            aspect,
            auto_identify=auto_identify,
            on_phase=on_phase,
        )
        if link is None:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.open",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": failure_reason or "unknown",
                    "destination_hash": dest_hash.hex(),
                    "aspect": aspect,
                },
            )
            return
        await self._rns_link_send(
            client,
            {
                "type": "rns.link.open",
                "request_id": request_id,
                "status": "success",
                "identified": identified,
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )

    async def _handle_rns_link_identify(self, client, data):
        request_id = data.get("request_id")
        dest_hash, aspect, err = self._rns_link_parse_dest_aspect(data)
        if err:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.identify",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": err,
                },
            )
            return
        ok, failure_reason = self.rns_link_manager.identify(dest_hash, aspect)
        await self._rns_link_send(
            client,
            {
                "type": "rns.link.identify",
                "request_id": request_id,
                "status": "success" if ok else "failure",
                "failure_reason": failure_reason,
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )

    async def _handle_rns_link_request(self, client, data):
        import base64

        request_id = data.get("request_id")
        dest_hash, aspect, err = self._rns_link_parse_dest_aspect(data)
        if err:
            await self._rns_link_send(
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
            await self._rns_link_send(
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
            await self._rns_link_send(
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
                await self._rns_link_send(
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
                self._rns_link_send(
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

        link, _identified, failure_reason = await self.rns_link_manager.open_link(
            dest_hash,
            aspect,
            auto_identify=False,
            on_phase=on_phase,
        )
        if link is None:
            await self._rns_link_send(
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
            self._rns_request_receipts.pop((client, request_id), None)
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
                self._rns_link_send(
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
            self._rns_request_receipts.pop((client, request_id), None)
            AsyncUtils.run_async(
                self._rns_link_send(
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
                self._rns_link_send(
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
            receipt = self.rns_link_manager.request(
                dest_hash,
                aspect,
                path,
                link_request_data,
                response_callback=on_response,
                failed_callback=on_failed,
                progress_callback=on_progress,
                timeout=timeout,
            )
            self._rns_request_receipts[(client, request_id)] = receipt
        except Exception as e:
            await self._rns_link_send(
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

    async def _handle_rns_link_send(self, client, data):
        import base64

        request_id = data.get("request_id")
        dest_hash, aspect, err = self._rns_link_parse_dest_aspect(data)
        if err:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.send",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": err,
                },
            )
            return
        payload_b64 = data.get("payload_b64", "")
        try:
            payload = (
                base64.b64decode(payload_b64, validate=True) if payload_b64 else b""
            )
        except Exception:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.send",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": "invalid_payload_b64",
                },
            )
            return
        ok, failure_reason = self.rns_link_manager.send_packet(
            dest_hash,
            aspect,
            payload,
        )
        await self._rns_link_send(
            client,
            {
                "type": "rns.link.send",
                "request_id": request_id,
                "status": "success" if ok else "failure",
                "failure_reason": failure_reason,
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )

    async def _handle_rns_link_close(self, client, data):
        request_id = data.get("request_id")
        dest_hash, aspect, err = self._rns_link_parse_dest_aspect(data)
        if err:
            await self._rns_link_send(
                client,
                {
                    "type": "rns.link.close",
                    "request_id": request_id,
                    "status": "failure",
                    "failure_reason": err,
                },
            )
            return
        ok = self.rns_link_manager.close(dest_hash, aspect)
        await self._rns_link_send(
            client,
            {
                "type": "rns.link.close",
                "request_id": request_id,
                "status": "success" if ok else "failure",
                "failure_reason": None if ok else "no_active_link",
                "destination_hash": dest_hash.hex(),
                "aspect": aspect,
            },
        )

    def _broadcast_to_websocket_clients(self, payload: dict) -> None:
        """Thread-safe fire-and-forget broadcast from RNS callback threads."""
        try:
            AsyncUtils.run_async(self.websocket_broadcast(json.dumps(payload)))
        except Exception as e:
            print(f"websocket broadcast failed: {e}")

    def _on_rns_link_broadcast(self, payload: dict) -> None:
        self._broadcast_to_websocket_clients(payload)
        if payload.get("type") == "rns.link.event":
            plugin_manager = getattr(self, "plugin_manager", None)
            if plugin_manager is not None:
                plugin_manager.on_rns_link_event(payload)

    async def _websocket_broadcast_coalesced(self, payload: dict) -> None:
        await self.websocket_broadcast(payload, _skip_coalesce=True)

    async def websocket_broadcast(self, data, *, _skip_coalesce: bool = False):
        from meshchatx.src.backend.websocket_runtime import (
            WS_BROADCAST_SEND_TIMEOUT_SEC,
            client_allows_topic,
            topic_for_type,
            touch_client_activity,
        )

        payload_obj = None
        if isinstance(data, dict):
            payload_obj = data
        elif isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    payload_obj = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                payload_obj = None
        elif isinstance(data, list):
            data = json.dumps(data)

        if payload_obj is not None and not _skip_coalesce:
            coalesce = getattr(self, "_ws_coalesce", None)
            if coalesce is not None and coalesce.offer(dict(payload_obj)):
                return

        if payload_obj is not None:
            seq_state = getattr(self, "ws_seq_state", None)
            if seq_state is not None:
                await seq_state.stamp(payload_obj)
            data = json.dumps(payload_obj)
        elif not isinstance(data, str):
            data = json.dumps(data)

        msg_type = payload_obj.get("type") if payload_obj else None
        topic = topic_for_type(msg_type if isinstance(msg_type, str) else None)

        # Serialize list mutation. Fan-out sends run in parallel so one slow
        # client does not stall every other socket.
        sessions_changed = False
        async with self._websocket_broadcast_lock:
            clients = list(self.websocket_clients)
            targets = [c for c in clients if client_allows_topic(c, topic)]

            async def _send_one(websocket_client):
                try:
                    await asyncio.wait_for(
                        websocket_client.send_str(data),
                        timeout=WS_BROADCAST_SEND_TIMEOUT_SEC,
                    )
                    touch_client_activity(websocket_client)
                    counters = getattr(self, "ws_counters", None)
                    if counters is not None:
                        counters.msgs_out += 1
                    return None
                except Exception as e:
                    print(f"Failed to broadcast to websocket client: {e}")
                    counters = getattr(self, "ws_counters", None)
                    if counters is not None:
                        counters.broadcast_failures += 1
                        if isinstance(e, (TimeoutError, asyncio.TimeoutError)):
                            counters.slow_drops += 1
                    return websocket_client

            results = await asyncio.gather(
                *[_send_one(c) for c in targets],
                return_exceptions=True,
            )
            dead = []
            for item in results:
                if isinstance(item, BaseException):
                    continue
                if item is not None:
                    dead.append(item)
            for client in dead:
                try:
                    self.websocket_clients.remove(client)
                except ValueError:
                    pass
                if self._detach_active_session(client):
                    sessions_changed = True
                try:
                    await client.close(code=WSCloseCode.GOING_AWAY)
                except Exception:
                    pass
        if sessions_changed:
            await self.send_active_sessions_to_websocket_clients()

    async def on_websocket_binary_received(self, client, data: bytes):
        """Optional binary rns.link frames (msgpack). JSON path remains default."""
        if not getattr(client, "_meshchatx_binary_rns_link", False):
            return
        if not data or len(data) < 2:
            return
        try:
            import msgpack
        except ImportError:
            return
        try:
            decoded = msgpack.unpackb(data, raw=False)
        except Exception:
            from meshchatx.src.backend.websocket_runtime import send_ws_error

            await send_ws_error(
                client,
                message="Invalid binary frame",
                code="invalid_binary",
            )
            return
        if isinstance(decoded, dict):
            await self.on_websocket_data_received(client, decoded)

    def _detach_active_session(self, websocket_response) -> bool:
        session_id = getattr(websocket_response, "_meshchatx_session_id", None)
        if not session_id:
            return False
        try:
            delattr(websocket_response, "_meshchatx_session_id")
        except Exception:
            pass
        return self.active_sessions.remove(session_id)

    def get_active_sessions_payload(self) -> dict:
        snap = self.active_sessions.snapshot()
        warning_enabled = True
        try:
            cfg = getattr(self, "config", None)
            if cfg is not None and hasattr(cfg, "multi_session_warning_enabled"):
                warning_enabled = bool(cfg.multi_session_warning_enabled.get())
        except Exception:
            warning_enabled = True
        count = int(snap.get("count") or 0)
        sessions = list(snap.get("sessions") or [])
        return {
            "count": count,
            "sessions": sessions,
            "warning": should_warn_multi_session(count, warning_enabled, sessions),
            "warning_enabled": warning_enabled,
        }

    async def send_active_sessions_to_websocket_clients(self):
        payload = self.get_active_sessions_payload()
        payload["type"] = "app.sessions.updated"
        await self.websocket_broadcast(json.dumps(payload))

    # broadcasts config to all websocket clients
    async def send_config_to_websocket_clients(self, context=None, changed_keys=None):
        ctx = context or self.current_context
        if not ctx:
            return
        config_dict = self.get_config_dict(context=ctx)
        await self.websocket_broadcast(
            {
                "type": "config",
                "config": config_dict,
            },
        )
        keys = changed_keys
        if keys is None:
            keys = list(config_dict.keys()) if isinstance(config_dict, dict) else []
        await self.websocket_broadcast(
            {
                "type": "config.changed",
                "keys": keys,
            },
        )

    # broadcasts to all websocket clients that we just announced
    async def send_announced_to_websocket_clients(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        await self.websocket_broadcast(
            json.dumps(
                {
                    "type": "announced",
                    "identity_hash": ctx.identity_hash,
                    "last_announced_at": ctx.config.last_announced_at.get(),
                },
            ),
        )

    async def _broadcast_blocked_destinations(self):
        try:
            blocked = self.database.misc.get_blocked_destinations()
            blocked_list = [
                {
                    "destination_hash": b["destination_hash"],
                    "created_at": b["created_at"],
                }
                for b in blocked
            ]
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "blocked_destinations",
                        "blocked_destinations": blocked_list,
                    },
                ),
            )
        except Exception as e:
            print(f"_broadcast_blocked_destinations: failed: {e}")

    # returns a dictionary of config
    def get_config_dict(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return {}
        return {
            "display_name": ctx.config.display_name.get(),
            "identity_hash": ctx.identity.hash.hex(),
            "identity_public_key": ctx.identity.get_public_key().hex(),
            "lxmf_address_hash": ctx.local_lxmf_destination.hexhash,
            "telephone_address_hash": ctx.telephone_manager.telephone.destination.hexhash
            if ctx.telephone_manager.telephone
            else None,
            "is_transport_enabled": (
                self.reticulum.transport_enabled()
                if hasattr(self, "reticulum") and self.reticulum
                else False
            ),
            "auto_announce_enabled": ctx.config.auto_announce_enabled.get(),
            "auto_announce_interval_seconds": ctx.config.auto_announce_interval_seconds.get(),
            "last_announced_at": ctx.config.last_announced_at.get(),
            "theme": ctx.config.theme.get(),
            "theme_preset": ctx.config.theme_preset.get(),
            "accent_color": ctx.config.accent_color.get(),
            "custom_canvas_color": ctx.config.custom_canvas_color.get(),
            "custom_surface_color": ctx.config.custom_surface_color.get(),
            "language": ctx.config.language.get(),
            "auto_resend_failed_messages_when_announce_received": ctx.config.auto_resend_failed_messages_when_announce_received.get(),
            "allow_auto_resending_failed_messages_with_attachments": ctx.config.allow_auto_resending_failed_messages_with_attachments.get(),
            "auto_send_failed_messages_to_propagation_node": ctx.config.auto_send_failed_messages_to_propagation_node.get(),
            "delivery_helptips_enabled": ctx.config.delivery_helptips_enabled.get(),
            "show_suggested_community_interfaces": ctx.config.show_suggested_community_interfaces.get(),
            "lxmf_delivery_transfer_limit_in_bytes": ctx.config.lxmf_delivery_transfer_limit_in_bytes.get(),
            "lxmf_propagation_transfer_limit_in_bytes": ctx.config.lxmf_propagation_transfer_limit_in_bytes.get(),
            "lxmf_propagation_sync_limit_in_bytes": ctx.config.lxmf_propagation_sync_limit_in_bytes.get(),
            "lxmf_local_propagation_node_enabled": ctx.config.lxmf_local_propagation_node_enabled.get(),
            "lxmf_local_propagation_node_address_hash": ctx.message_router.propagation_destination.hexhash,
            "lxmf_preferred_propagation_node_destination_hash": ctx.config.lxmf_preferred_propagation_node_destination_hash.get(),
            "lxmf_preferred_propagation_node_auto_select": ctx.config.lxmf_preferred_propagation_node_auto_select.get(),
            "lxmf_preferred_propagation_node_auto_sync_interval_seconds": ctx.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get(),
            "lxmf_preferred_propagation_node_last_synced_at": ctx.config.lxmf_preferred_propagation_node_last_synced_at.get(),
            "lxmf_user_icon_name": ctx.config.lxmf_user_icon_name.get(),
            "lxmf_user_icon_foreground_colour": ctx.config.lxmf_user_icon_foreground_colour.get(),
            "lxmf_user_icon_background_colour": ctx.config.lxmf_user_icon_background_colour.get(),
            "lxmf_inbound_stamp_cost": ctx.config.lxmf_inbound_stamp_cost.get(),
            "lxmf_propagation_node_stamp_cost": ctx.config.lxmf_propagation_node_stamp_cost.get(),
            "lxmf_propagation_sequential_validation": ctx.config.lxmf_propagation_sequential_validation.get(),
            "lxmf_propagation_static_peers_bypass_sequential": ctx.config.lxmf_propagation_static_peers_bypass_sequential.get(),
            "lxmf_propagation_max_inbound_syncs": ctx.config.lxmf_propagation_max_inbound_syncs.get(),
            "lxmf_flood_protection_enabled": ctx.config.lxmf_flood_protection_enabled.get(),
            "lxmf_flood_threshold_per_minute": ctx.config.lxmf_flood_threshold_per_minute.get(),
            "lxmf_flood_max_stamp_cost": ctx.config.lxmf_flood_max_stamp_cost.get(),
            "lxmf_flood_cooldown_seconds": ctx.config.lxmf_flood_cooldown_seconds.get(),
            "page_archiver_enabled": ctx.config.page_archiver_enabled.get(),
            "page_archiver_max_versions": ctx.config.page_archiver_max_versions.get(),
            "archives_max_storage_gb": ctx.config.archives_max_storage_gb.get(),
            "backup_max_count": ctx.config.backup_max_count.get(),
            "crawler_enabled": ctx.config.crawler_enabled.get(),
            "crawler_max_retries": ctx.config.crawler_max_retries.get(),
            "crawler_retry_delay_seconds": ctx.config.crawler_retry_delay_seconds.get(),
            "crawler_max_concurrent": ctx.config.crawler_max_concurrent.get(),
            "crawler_max_hops": ctx.config.crawler_max_hops.get(),
            "crawler_max_rtt_ms": ctx.config.crawler_max_rtt_ms.get(),
            "crawler_max_depth": ctx.config.crawler_max_depth.get(),
            "crawler_max_pages_per_node": ctx.config.crawler_max_pages_per_node.get(),
            "crawler_requests_per_day_per_node": ctx.config.crawler_requests_per_day_per_node.get(),
            "crawler_refresh_days": ctx.config.crawler_refresh_days.get(),
            "auth_enabled": self.auth_enabled,
            "privacy_mode_enabled": ctx.config.privacy_mode_enabled.get(),
            "multi_session_warning_enabled": ctx.config.multi_session_warning_enabled.get(),
            "voicemail_enabled": ctx.config.voicemail_enabled.get(),
            "voicemail_greeting": ctx.config.voicemail_greeting.get(),
            "voicemail_auto_answer_delay_seconds": ctx.config.voicemail_auto_answer_delay_seconds.get(),
            "voicemail_max_recording_seconds": ctx.config.voicemail_max_recording_seconds.get(),
            "voicemail_tts_speed": ctx.config.voicemail_tts_speed.get(),
            "voicemail_tts_pitch": ctx.config.voicemail_tts_pitch.get(),
            "voicemail_tts_voice": ctx.config.voicemail_tts_voice.get(),
            "voicemail_tts_word_gap": ctx.config.voicemail_tts_word_gap.get(),
            "custom_ringtone_enabled": ctx.config.custom_ringtone_enabled.get(),
            "ringtone_filename": ctx.config.ringtone_filename.get(),
            "ringtone_preferred_id": ctx.config.ringtone_preferred_id.get(),
            "ringtone_volume": ctx.config.ringtone_volume.get(),
            "notification_sound_enabled": ctx.config.notification_sound_enabled.get(),
            "notification_sound_preferred_id": ctx.config.notification_sound_preferred_id.get(),
            "notification_sound_volume": ctx.config.notification_sound_volume.get(),
            "map_offline_enabled": ctx.config.map_offline_enabled.get(),
            "map_mbtiles_dir": ctx.config.map_mbtiles_dir.get(),
            "map_tile_cache_enabled": ctx.config.map_tile_cache_enabled.get(),
            "map_default_lat": ctx.config.map_default_lat.get(),
            "map_default_lon": ctx.config.map_default_lon.get(),
            "map_default_zoom": ctx.config.map_default_zoom.get(),
            "map_tile_server_url": ctx.config.map_tile_server_url.get(),
            "map_nominatim_api_url": ctx.config.map_nominatim_api_url.get(),
            "map_overlay_max_bytes": ctx.config.map_overlay_max_bytes.get(),
            "map_overlay_max_features": ctx.config.map_overlay_max_features.get(),
            "map_overlay_max_kmz_uncompressed_bytes": ctx.config.map_overlay_max_kmz_uncompressed_bytes.get(),
            "map_data_max_bytes": ctx.config.map_data_max_bytes.get(),
            "map_data_announce_enabled": ctx.config.map_data_announce_enabled.get(),
            "map_data_announce_interval": ctx.config.map_data_announce_interval.get(),
            "map_data_display_name": ctx.config.map_data_display_name.get(),
            "map_overlay_max_sources": ctx.config.map_overlay_max_sources.get(),
            "map_overlay_max_concurrent_jobs": ctx.config.map_overlay_max_concurrent_jobs.get(),
            "map_overlay_path_timeout_seconds": ctx.config.map_overlay_path_timeout_seconds.get(),
            "map_overlay_transfer_timeout_seconds": ctx.config.map_overlay_transfer_timeout_seconds.get(),
            "map_overlay_job_timeout_seconds": ctx.config.map_overlay_job_timeout_seconds.get(),
            "map_overlay_max_retries": ctx.config.map_overlay_max_retries.get(),
            "map_overlay_retry_delay_seconds": ctx.config.map_overlay_retry_delay_seconds.get(),
            "do_not_disturb_enabled": ctx.config.do_not_disturb_enabled.get(),
            "telephone_enabled": ctx.config.telephone_enabled.get(),
            "telephone_allow_calls_from_contacts_only": ctx.config.telephone_allow_calls_from_contacts_only.get(),
            "telephone_announce_enabled": ctx.config.telephone_announce_enabled.get(),
            "telephone_audio_profile_id": ctx.config.telephone_audio_profile_id.get(),
            "telephone_call_mode_id": ctx.config.telephone_call_mode_id.get(),
            "telephone_web_audio_enabled": ctx.config.telephone_web_audio_enabled.get(),
            "telephone_web_audio_allow_fallback": ctx.config.telephone_web_audio_allow_fallback.get(),
            "call_recording_enabled": ctx.config.call_recording_enabled.get(),
            "block_attachments_from_strangers": ctx.config.block_attachments_from_strangers.get(),
            "block_all_from_strangers": ctx.config.block_all_from_strangers.get(),
            "show_unknown_contact_banner": ctx.config.show_unknown_contact_banner.get(),
            "warn_on_stranger_links": ctx.config.warn_on_stranger_links.get(),
            "banished_effect_enabled": ctx.config.banished_effect_enabled.get(),
            "banished_text": ctx.config.banished_text.get(),
            "banished_color": ctx.config.banished_color.get(),
            "message_font_size": ctx.config.message_font_size.get(),
            "messages_sidebar_position": ctx.config.messages_sidebar_position.get(),
            "app_sidebar_layout": ctx.config.app_sidebar_layout.get(),
            "messages_multi_pane_enabled": ctx.config.messages_multi_pane_enabled.get(),
            "nomad_tabs_enabled": ctx.config.nomad_tabs_enabled.get(),
            "rrc_enabled": ctx.config.rrc_enabled.get(),
            "rrc_unread_badges_enabled": ctx.config.rrc_unread_badges_enabled.get(),
            "message_icon_size": ctx.config.message_icon_size.get(),
            "ui_transparency": ctx.config.ui_transparency.get(),
            "ui_glass_enabled": ctx.config.ui_glass_enabled.get(),
            "message_outbound_bubble_color": ctx.config.message_outbound_bubble_color.get(),
            "message_inbound_bubble_color": ctx.config.message_inbound_bubble_color.get(),
            "message_failed_bubble_color": ctx.config.message_failed_bubble_color.get(),
            "message_waiting_bubble_color": ctx.config.message_waiting_bubble_color.get(),
            "translator_argos_enabled": ctx.config.translator_argos_enabled.get(),
            "translator_libretranslate_enabled": ctx.config.translator_libretranslate_enabled.get(),
            "libretranslate_url": ctx.config.libretranslate_url.get(),
            "libretranslate_api_key": ctx.config.libretranslate_api_key.get(),
            "desktop_open_calls_in_separate_window": ctx.config.desktop_open_calls_in_separate_window.get(),
            "desktop_hardware_acceleration_enabled": ctx.config.desktop_hardware_acceleration_enabled.get(),
            "blackhole_integration_enabled": ctx.config.blackhole_integration_enabled.get(),
            "announce_store_lxmf_delivery": ctx.config.announce_store_lxmf_delivery.get(),
            "announce_store_lxst_telephony": ctx.config.announce_store_lxst_telephony.get(),
            "announce_store_nomadnetwork_node": ctx.config.announce_store_nomadnetwork_node.get(),
            "announce_store_lxmf_propagation": ctx.config.announce_store_lxmf_propagation.get(),
            "announce_store_map_data": ctx.config.announce_store_map_data.get(),
            "announce_max_stored_lxmf_delivery": ctx.config.announce_max_stored_lxmf_delivery.get(),
            "announce_max_stored_nomadnetwork_node": ctx.config.announce_max_stored_nomadnetwork_node.get(),
            "announce_max_stored_lxmf_propagation": ctx.config.announce_max_stored_lxmf_propagation.get(),
            "announce_max_stored_map_data": ctx.config.announce_max_stored_map_data.get(),
            "announce_fetch_limit_lxmf_delivery": ctx.config.announce_fetch_limit_lxmf_delivery.get(),
            "announce_fetch_limit_nomadnetwork_node": ctx.config.announce_fetch_limit_nomadnetwork_node.get(),
            "announce_fetch_limit_lxmf_propagation": ctx.config.announce_fetch_limit_lxmf_propagation.get(),
            "announce_fetch_limit_map_data": ctx.config.announce_fetch_limit_map_data.get(),
            "announce_search_max_fetch": ctx.config.announce_search_max_fetch.get(),
            "discovered_interfaces_max_return": ctx.config.discovered_interfaces_max_return.get(),
            "csp_extra_connect_src": ctx.config.csp_extra_connect_src.get(),
            "csp_extra_img_src": ctx.config.csp_extra_img_src.get(),
            "csp_extra_frame_src": ctx.config.csp_extra_frame_src.get(),
            "csp_extra_script_src": ctx.config.csp_extra_script_src.get(),
            "csp_extra_style_src": ctx.config.csp_extra_style_src.get(),
            "telephone_tone_generator_enabled": ctx.config.telephone_tone_generator_enabled.get(),
            "telephone_tone_generator_volume": ctx.config.telephone_tone_generator_volume.get(),
            "location_source": ctx.config.location_source.get(),
            "location_manual_lat": ctx.config.location_manual_lat.get(),
            "location_manual_lon": ctx.config.location_manual_lon.get(),
            "location_manual_alt": ctx.config.location_manual_alt.get(),
            "telemetry_enabled": ctx.config.telemetry_enabled.get(),
            "nomad_render_markdown_enabled": ctx.config.nomad_render_markdown_enabled.get(),
            "nomad_render_html_enabled": ctx.config.nomad_render_html_enabled.get(),
            "nomad_render_plaintext_enabled": ctx.config.nomad_render_plaintext_enabled.get(),
            "nomad_micron_wasm_enabled": ctx.config.nomad_micron_wasm_enabled.get(),
            "nomad_micron_default_engine": ctx.config.nomad_micron_default_engine.get()
            or "js",
            "nomad_default_page_path": ctx.config.nomad_default_page_path.get(),
            "local_message_auto_delete_enabled": ctx.config.local_message_auto_delete_enabled.get(),
            "local_message_auto_delete_value": ctx.config.local_message_auto_delete_value.get(),
            "local_message_auto_delete_unit": ctx.config.local_message_auto_delete_unit.get()
            or "days",
            "message_blocklist_enabled": ctx.config.message_blocklist_enabled.get(),
        }

    # try and get a name for the provided identity hash
    def get_name_for_identity_hash(self, identity_hash: str):
        id_norm = normalize_hex_identifier(identity_hash) if identity_hash else ""
        # 1. try recall identity and calculate lxmf destination hash
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            # get lxmf.delivery destination hash
            lxmf_destination_hash = RNS.Destination.hash(
                identity,
                "lxmf",
                "delivery",
            ).hex()

            # use custom name if available
            custom_name = self.database.announces.get_custom_display_name(
                lxmf_destination_hash,
            )
            if custom_name is not None:
                return custom_name

            # use lxmf name if available
            lxmf_name = self.get_lxmf_conversation_name(
                lxmf_destination_hash,
                default_name=None,
            )
            if lxmf_name is not None:
                return lxmf_name

        # 2. if identity recall failed, or we couldn't find a name for the calculated hash
        # try to look up an lxmf.delivery announce with this identity_hash in the database
        lookup_hash = id_norm or identity_hash
        announces = self.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            identity_hash=lookup_hash,
            limit=5,
        )
        if announces:
            for announce in announces:
                ann_id = announce.get("identity_hash") or ""
                if ann_id and normalize_hex_identifier(ann_id) == id_norm:
                    lxmf_destination_hash = announce["destination_hash"]

                    # check custom name for this hash
                    custom_name = self.database.announces.get_custom_display_name(
                        lxmf_destination_hash,
                    )
                    if custom_name is not None:
                        return custom_name

                    # check lxmf name from app_data
                    if announce["app_data"] is not None:
                        lxmf_name = parse_lxmf_display_name(
                            app_data_base64=announce["app_data"],
                            default_value=None,
                        )
                        if lxmf_name is not None:
                            return lxmf_name

        # couldn't find a name for this identity
        return None

    # recall identity from reticulum or database
    def get_lxmf_destination_hash_for_identity_hash(self, identity_hash: str):
        id_norm = normalize_hex_identifier(identity_hash) if identity_hash else ""
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            try:
                return RNS.Destination.hash(identity, "lxmf", "delivery").hex()
            except Exception:
                pass

        if self.database is None:
            return None

        # fallback to announces
        lookup_hash = id_norm or identity_hash
        announces = self.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            identity_hash=lookup_hash,
            limit=5,
        )
        if announces:
            for announce in announces:
                ann_id = announce.get("identity_hash") or ""
                if ann_id and normalize_hex_identifier(ann_id) == id_norm:
                    return announce["destination_hash"]
        return None

    def get_lxst_telephony_hash_for_identity_hash(self, identity_hash: str):
        id_norm = normalize_hex_identifier(identity_hash) if identity_hash else ""
        lookup_hash = id_norm or identity_hash

        if self.database is not None:
            announces = self.database.announces.get_filtered_announces(
                aspect="lxst.telephony",
                identity_hash=lookup_hash,
                limit=5,
            )
            if announces:
                for announce in announces:
                    ann_id = announce.get("identity_hash") or ""
                    if ann_id and normalize_hex_identifier(ann_id) == id_norm:
                        return announce.get("destination_hash")

        # Fallback: derive from identity if available (same identity, different aspect)
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            try:
                return RNS.Destination.hash(identity, "lxst", "telephony").hex()
            except Exception:
                return None
        return None

    def recall_identity(self, hash_hex: str) -> RNS.Identity | None:
        try:
            if not hash_hex or not isinstance(hash_hex, str):
                return None

            stripped = hash_hex.strip()
            canonical = normalize_hex_identifier(stripped)

            # 1. try reticulum recall (works for both identity and destination hashes)
            hash_bytes = hex_identifier_to_bytes(stripped)
            if hash_bytes:
                identity = RNS.Identity.recall(hash_bytes)
                if identity:
                    return identity

            # 2. try database lookup
            # lookup by destination hash first
            announce = self.database.announces.get_announce_by_hash(stripped)
            if not announce and canonical:
                announce = self.database.announces.get_announce_by_hash(canonical)
            if announce:
                announce = dict(announce)

            if not announce:
                # lookup by identity hash
                search_term = canonical if len(canonical) >= 8 else stripped
                results = self.database.announces.get_filtered_announces(
                    search_term=search_term,
                )
                if results:
                    # find first one with a public key
                    for res in results:
                        res_dict = dict(res)
                        if res_dict.get("identity_public_key"):
                            announce = res_dict
                            break

            if announce and announce.get("identity_public_key"):
                public_key = base64.b64decode(announce["identity_public_key"])
                identity = self._identity_from_public_key_bytes(public_key)
                if identity is not None:
                    return identity

        except Exception as e:
            print(f"Error recalling identity for {hash_hex}: {type(e).__name__}: {e!r}")

        return None

    @staticmethod
    def _identity_from_public_key_bytes(public_key: bytes) -> RNS.Identity | None:
        """Load an RNS Identity from raw public-key bytes.

        Identity.load_public_key is documented as returning True/False, but
        current RNS releases return None on both success and failure. Treat
        a non-None identity.pub (and a computed hash) as success.
        """
        if not public_key:
            return None
        identity = RNS.Identity(create_keys=False)
        try:
            identity.load_public_key(public_key)
        except Exception:
            return None
        if getattr(identity, "pub", None) is None:
            return None
        if not getattr(identity, "hash", None):
            return None
        return identity

    # convert an lxmf message to a dictionary, for sending over websocket

    # convert database announce to a dictionary
    def _batch_convert_announces_to_api_dicts(
        self,
        results,
        aspect=None,
        include_hops=True,
    ):
        """Batch-convert announce rows using prefetched icons and custom names."""
        if not results:
            return []

        other_user_hashes = [r["destination_hash"] for r in results]
        user_icons = {}
        if other_user_hashes:
            db_icons = self.database.misc.get_user_icons(other_user_hashes)
            for icon in db_icons:
                user_icons[icon["destination_hash"]] = {
                    "icon_name": icon["icon_name"],
                    "foreground_colour": icon["foreground_colour"],
                    "background_colour": icon["background_colour"],
                }

        custom_names = {}
        lxmf_names_for_telephony = {}
        if other_user_hashes:
            db_custom_names = self.database.provider.fetchall(
                f"SELECT destination_hash, display_name FROM custom_destination_display_names WHERE destination_hash IN ({','.join(['?'] * len(other_user_hashes))})",
                other_user_hashes,
            )
            for row in db_custom_names:
                custom_names[row["destination_hash"]] = row["display_name"]

            if aspect == "lxst.telephony":
                identity_hashes = list(
                    {r["identity_hash"] for r in results if r.get("identity_hash")},
                )
                if identity_hashes:
                    lxmf_results = self.database.announces.provider.fetchall(
                        f"SELECT identity_hash, app_data FROM announces WHERE aspect = 'lxmf.delivery' AND identity_hash IN ({','.join(['?'] * len(identity_hashes))})",
                        identity_hashes,
                    )
                    for row in lxmf_results:
                        lxmf_names_for_telephony[row["identity_hash"]] = (
                            parse_lxmf_display_name(row["app_data"])
                        )

        all_announces = []
        for announce in results:
            if not isinstance(announce, dict):
                announce = dict(announce)

            display_name = None
            is_local = (
                self.current_context
                and announce["identity_hash"] == self.current_context.identity_hash
            )

            if announce["aspect"] == "lxmf.delivery":
                display_name = parse_lxmf_display_name(announce["app_data"])
            elif announce["aspect"] == "nomadnetwork.node":
                display_name = parse_nomadnetwork_node_display_name(
                    announce["app_data"],
                )
            elif announce["aspect"] == "lxst.telephony":
                display_name = parse_lxmf_display_name(announce["app_data"])
                if not display_name or display_name == "Anonymous Peer":
                    display_name = lxmf_names_for_telephony.get(
                        announce["identity_hash"],
                    )
            elif announce["aspect"] == "rrc.hub":
                display_name = rrc_protocol.display_name_from_hub_app_data(
                    announce.get("app_data"),
                )

            if not display_name or display_name == "Anonymous Peer":
                if is_local and self.current_context:
                    display_name = self.current_context.config.display_name.get()
                else:
                    display_name = (
                        self.get_name_for_identity_hash(announce["identity_hash"])
                        or "Anonymous Peer"
                    )

            hops = None
            if include_hops:
                hops = RNS.Transport.hops_to(
                    bytes.fromhex(announce["destination_hash"]),
                )

            created_at = str(announce["created_at"])
            if created_at and "+" not in created_at and "Z" not in created_at:
                created_at += "Z"
            updated_at = str(announce["updated_at"])
            if updated_at and "+" not in updated_at and "Z" not in updated_at:
                updated_at += "Z"

            all_announces.append(
                {
                    "id": announce["id"],
                    "destination_hash": announce["destination_hash"],
                    "aspect": announce["aspect"],
                    "identity_hash": announce["identity_hash"],
                    "identity_public_key": announce["identity_public_key"],
                    "app_data": announce["app_data"],
                    "hops": hops,
                    "rssi": announce["rssi"],
                    "snr": announce["snr"],
                    "quality": announce["quality"],
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "display_name": display_name,
                    "custom_display_name": custom_names.get(
                        announce["destination_hash"],
                    ),
                    "lxmf_user_icon": user_icons.get(announce["destination_hash"]),
                    "contact_image": announce.get("contact_image"),
                },
            )
        return all_announces

    def convert_db_announce_to_dict(self, announce):
        # convert to dict if it's a sqlite3.Row
        if not isinstance(announce, dict):
            announce = dict(announce)

        # parse display name from announce
        display_name = None
        if announce["aspect"] == "lxmf.delivery":
            display_name = parse_lxmf_display_name(announce["app_data"])
        elif announce["aspect"] == "nomadnetwork.node":
            display_name = parse_nomadnetwork_node_display_name(
                announce["app_data"],
            )
        elif announce["aspect"] == "lxst.telephony":
            display_name = parse_lxmf_display_name(announce["app_data"])
        elif announce["aspect"] == "rrc.hub":
            display_name = rrc_protocol.display_name_from_hub_app_data(
                announce.get("app_data"),
            )

        # Try to find associated LXMF destination hash if this is a telephony announce
        lxmf_destination_hash = None
        if announce["aspect"] == "lxst.telephony" and announce.get("identity_hash"):
            # 1. Check if we already have an LXMF announce for this identity
            lxmf_announces = self.database.announces.get_filtered_announces(
                aspect="lxmf.delivery",
                search_term=announce["identity_hash"],
            )
            if lxmf_announces:
                for lxmf_a in lxmf_announces:
                    if lxmf_a["identity_hash"] == announce["identity_hash"]:
                        lxmf_destination_hash = lxmf_a["destination_hash"]
                        # Also update display name if telephony one was empty
                        if not display_name or display_name == "Anonymous Peer":
                            display_name = parse_lxmf_display_name(
                                lxmf_a["app_data"],
                            )
                        break

            # 2. If not found in announces, try to recall identity and calculate LXMF hash
            if not lxmf_destination_hash:
                try:
                    identity_hash_bytes = bytes.fromhex(announce["identity_hash"])
                    identity = RNS.Identity.recall(identity_hash_bytes)
                    if not identity and announce.get("identity_public_key"):
                        # Try to load from public key if recall failed
                        public_key = base64.b64decode(announce["identity_public_key"])
                        identity = self._identity_from_public_key_bytes(public_key)

                    if identity:
                        try:
                            lxmf_destination_hash = RNS.Destination.hash(
                                identity,
                                "lxmf",
                                "delivery",
                            ).hex()
                        except Exception:
                            pass
                except Exception:
                    pass

        if not display_name or display_name == "Anonymous Peer":
            is_local = (
                self.current_context
                and announce.get("identity_hash") == self.current_context.identity_hash
            )
            if is_local and self.current_context:
                display_name = self.current_context.config.display_name.get()
            elif announce.get("identity_hash"):
                display_name = (
                    self.get_name_for_identity_hash(announce["identity_hash"])
                    or "Anonymous Peer"
                )
            else:
                display_name = "Anonymous Peer"

        # find lxmf user icon from database
        lxmf_user_icon = None
        # Try multiple potential hashes for the icon
        icon_hashes_to_check = []
        if lxmf_destination_hash:
            icon_hashes_to_check.append(lxmf_destination_hash)
        icon_hashes_to_check.append(announce["destination_hash"])

        # ensure we don't return the user's own icon for peers
        local_hash = None
        if self.current_context and self.current_context.local_lxmf_destination:
            local_hash = self.current_context.local_lxmf_destination.hexhash

        db_lxmf_user_icon = None
        for icon_hash in icon_hashes_to_check:
            # skip if this is the user's own hash - don't return user's icon for peers
            if local_hash and icon_hash == local_hash:
                continue
            db_lxmf_user_icon = self.database.misc.get_user_icon(icon_hash)
            if db_lxmf_user_icon:
                break

        if db_lxmf_user_icon:
            lxmf_user_icon = {
                "icon_name": db_lxmf_user_icon["icon_name"],
                "foreground_colour": db_lxmf_user_icon["foreground_colour"],
                "background_colour": db_lxmf_user_icon["background_colour"],
            }

        # get current hops away
        hops = RNS.Transport.hops_to(bytes.fromhex(announce["destination_hash"]))

        # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
        created_at = str(announce["created_at"])
        if created_at and "+" not in created_at and "Z" not in created_at:
            created_at += "Z"

        updated_at = str(announce["updated_at"])
        if updated_at and "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        return {
            "id": announce["id"],
            "destination_hash": announce["destination_hash"],
            "aspect": announce["aspect"],
            "identity_hash": announce["identity_hash"],
            "identity_public_key": announce["identity_public_key"],
            "app_data": announce["app_data"],
            "hops": hops,
            "rssi": announce["rssi"],
            "snr": announce["snr"],
            "quality": announce["quality"],
            "display_name": display_name,
            "lxmf_destination_hash": lxmf_destination_hash,
            "custom_display_name": self.get_custom_destination_display_name(
                announce["destination_hash"],
            ),
            "lxmf_user_icon": lxmf_user_icon,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    # convert database lxmf message to a dictionary
    # updates the lxmf user icon for the provided destination hash
    def update_lxmf_user_icon(
        self,
        destination_hash: str,
        icon_name: str,
        foreground_colour: str,
        background_colour: str,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # ensure we're not storing the user's own icon with a peer's hash
        # only store icons for remote peers, not for the local user
        if (
            ctx.local_lxmf_destination
            and destination_hash == ctx.local_lxmf_destination.hexhash
        ):
            print(f"skipping icon update for local user's own hash: {destination_hash}")
            return

        # log
        print(
            f"updating lxmf user icon for {destination_hash} to icon_name={icon_name}, foreground_colour={foreground_colour}, background_colour={background_colour}",
        )

        ctx.database.misc.update_lxmf_user_icon(
            destination_hash,
            icon_name,
            foreground_colour,
            background_colour,
        )

    def _related_hashes_for_contact_lookup(self, source_hash: str, context=None):
        """Collect identity/LXMF/LXST hashes that may identify the same peer."""
        ctx = context or self.current_context
        related = []
        seen = set()

        def add(value):
            if not value or not isinstance(value, str):
                return
            normalized = normalize_hex_identifier(value)
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            related.append(normalized)

        add(source_hash)
        if not ctx or not ctx.database:
            return related

        try:
            announce = ctx.database.announces.get_announce_by_hash(source_hash)
            if announce:
                add(announce.get("identity_hash"))
                add(announce.get("destination_hash"))
                identity_hash = announce.get("identity_hash")
                if identity_hash:
                    for other in ctx.database.announces.get_announces_by_identity_hash(
                        identity_hash,
                    ):
                        add(other.get("destination_hash"))
                        add(other.get("identity_hash"))
            else:
                for other in ctx.database.announces.get_announces_by_identity_hash(
                    source_hash,
                ):
                    add(other.get("destination_hash"))
                    add(other.get("identity_hash"))
        except Exception:
            pass

        try:
            lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(source_hash)
            add(lxmf_hash)
        except Exception:
            pass

        try:
            lxst_hash = self.get_lxst_telephony_hash_for_identity_hash(source_hash)
            add(lxst_hash)
        except Exception:
            pass

        return related

    def _resolve_contact_for_hash(self, source_hash: str, context=None):
        """Resolve a contact for an identity or destination hash.

        Contacts are often saved with an LXMF destination hash as
        remote_identity_hash (from chat UI). Incoming calls provide the
        caller's identity hash. Bridge those forms via announces and derived
        destination hashes so contacts-only call policy works.
        """
        ctx = context or self.current_context
        if not ctx or not ctx.database or not source_hash:
            return None
        try:
            related = self._related_hashes_for_contact_lookup(source_hash, context=ctx)
            return ctx.database.contacts.get_contact_by_identity_hash(
                source_hash,
                related_hashes=related,
            )
        except Exception:
            return None

    def _collect_blocked_identity_hashes(self, context=None) -> list:
        """Identity-hash bytes for LXST set_blocked from the block list."""
        ctx = context or self.current_context
        out = []
        seen = set()
        if not ctx or not ctx.database:
            return out
        try:
            blocked = ctx.database.misc.get_blocked_destinations()
        except Exception:
            return out

        for row in blocked or []:
            dest_hex = row.get("destination_hash") if isinstance(row, dict) else None
            if not dest_hex:
                continue
            candidates = [dest_hex]
            try:
                announce = ctx.database.announces.get_announce_by_hash(dest_hex)
                if announce and announce.get("identity_hash"):
                    candidates.append(announce["identity_hash"])
            except Exception:
                pass
            for candidate in candidates:
                try:
                    raw = bytes.fromhex(str(candidate))
                except Exception:
                    continue
                if len(raw) != RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
                    continue
                if raw in seen:
                    continue
                seen.add(raw)
                out.append(raw)
        return out

    def sync_telephone_call_policy(self, context=None):
        """Push contacts-only / DND / block policy into LXST Telephone.set_allowed.

        This rejects unauthorized callers before RINGING instead of relying only
        on a delayed hangup after the ringing callback.
        """
        ctx = context or self.current_context
        if not ctx or not getattr(ctx, "telephone_manager", None):
            return

        def allowed(identity_hash: bytes, policy_ctx=ctx) -> bool:
            if not isinstance(identity_hash, (bytes, bytearray)):
                return False
            caller_hex = bytes(identity_hash).hex()
            try:
                if policy_ctx.config.do_not_disturb_enabled.get():
                    return False
                if self.is_destination_blocked(caller_hex, context=policy_ctx):
                    return False
                if (
                    policy_ctx.config.telephone_allow_calls_from_contacts_only.get()
                    or policy_ctx.config.block_all_from_strangers.get()
                ) and not self._is_contact(caller_hex, context=policy_ctx):
                    return False
                return True
            except Exception as e:
                print(f"sync_telephone_call_policy allowed() error: {e}")
                return False

        try:
            ctx.telephone_manager.set_call_policy(
                allowed_fn=allowed,
                blocked_identity_hashes=self._collect_blocked_identity_hashes(
                    context=ctx,
                ),
            )
        except Exception as e:
            print(f"sync_telephone_call_policy failed: {e}")

    def _is_contact(self, source_hash: str, context=None) -> bool:
        return self._resolve_contact_for_hash(source_hash, context=context) is not None

    def _encode_pcm_wav_to_ogg_opus(self, wav_bytes: bytes) -> bytes | None:
        """Encode a WAV/PCM payload into an OGG/Opus byte string.

        Thin compatibility wrapper around
        meshchatx.src.backend.audio_codec.encode_audio_bytes_to_ogg_opus
        kept for the existing test surface.
        """
        try:
            from meshchatx.src.backend import audio_codec

            return audio_codec.encode_audio_bytes_to_ogg_opus(wav_bytes)
        except Exception as e:
            print(f"PCM->OGG/Opus encoding via LXST failed: {e}")
            return None

    def _convert_webm_opus_to_ogg(self, audio_bytes: bytes) -> bytes:
        """Convert browser-recorded audio into LXMF-compatible OGG/Opus.

        Routes everything through
        meshchatx.src.backend.audio_codec, which decodes the input
        with miniaudio (WAV/MP3/FLAC/OGG-Vorbis) or LXST (OGG/Opus) and
        re-encodes it with LXST's voice-friendly Opus profile. If decoding
        fails the original bytes are returned unchanged so the caller can
        still try to send the message.
        """
        if audio_bytes[:4] == b"OggS":
            return audio_bytes
        try:
            from meshchatx.src.backend import audio_codec

            encoded = audio_codec.encode_audio_bytes_to_ogg_opus(audio_bytes)
        except Exception as e:
            print(f"audio conversion failed: {e}")
            return audio_bytes
        if encoded is None:
            return audio_bytes
        return encoded

    def incoming_call_is_policy_filtered(self, caller_hex, context=None) -> bool:
        """True when an inbound ring must not surface in the local UI.

        Covers DND, banishment, contacts-only, and block-strangers. Missing
        caller identity is treated as filtered when a contact gate is on.
        Unexpected errors fail closed.
        """
        ctx = context or self.current_context
        if not ctx or not getattr(ctx, "config", None):
            return True
        try:
            if ctx.config.do_not_disturb_enabled.get():
                return True
            if caller_hex and self.is_destination_blocked(caller_hex, context=ctx):
                return True
            if (
                ctx.config.telephone_allow_calls_from_contacts_only.get()
                or ctx.config.block_all_from_strangers.get()
            ) and (not caller_hex or not self._is_contact(caller_hex, context=ctx)):
                return True
            return False
        except Exception as e:
            print(f"incoming_call_is_policy_filtered: {e}")
            return True

    def is_destination_blocked(self, destination_hash: str, context=None) -> bool:
        """Return whether destination_hash is in the block list.

        Accepts either a destination hash or an identity hash. A block on the
        identity matches every known destination of that identity, and a block
        on any destination matches the identity. Unexpected database errors
        fail closed so inbound LXMF and LXST do not treat a broken ACL as open.
        """
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return False
        try:
            related = self._related_hashes_for_contact_lookup(
                destination_hash,
                context=ctx,
            )
            if destination_hash and destination_hash not in related:
                related = [destination_hash, *related]
            for peer_hash in related:
                if ctx.database.misc.is_destination_blocked(peer_hash):
                    return True
            return False
        except Exception:
            return True

    def _lxmf_reticulum_enforce_block(
        self,
        destination_hash: str,
        context=None,
    ) -> None:
        """Apply Reticulum blackhole or drop_path after a peer was added to the block list."""
        ctx = context or self.current_context
        try:
            if not hasattr(self, "reticulum") or not self.reticulum:
                return
            db = getattr(ctx, "database", None) if ctx is not None else None
            if db is None:
                db = self.database
            identity_hash = None
            if db is not None:
                announce = db.announces.get_announce_by_hash(destination_hash)
                if announce and announce.get("identity_hash"):
                    identity_hash = announce["identity_hash"]
                else:
                    by_ident = db.announces.get_announces_by_identity_hash(
                        destination_hash,
                    )
                    try:
                        by_ident = list(by_ident or [])
                    except TypeError:
                        by_ident = []
                    if by_ident:
                        identity_hash = destination_hash
            target_hash = identity_hash or destination_hash
            dest_bytes = bytes.fromhex(target_hash)
            use_blackhole = True
            cfg = getattr(ctx, "config", None) if ctx is not None else None
            if cfg is None:
                cfg = self.config
            if cfg is not None:
                try:
                    use_blackhole = bool(cfg.blackhole_integration_enabled.get())
                except Exception:
                    use_blackhole = True
            if use_blackhole and hasattr(self.reticulum, "blackhole_identity"):
                reason = (
                    f"Blocked in MeshChatX (from {destination_hash})"
                    if identity_hash
                    else "Blocked in MeshChatX"
                )
                self.reticulum.blackhole_identity(dest_bytes, reason=reason)
            else:
                self.reticulum.drop_path(dest_bytes)
        except Exception as e:
            print(f"_lxmf_reticulum_enforce_block: failed: {e}")

    def _delete_contact_and_stamp_ticket(
        self,
        destination_hash: str,
        context=None,
    ) -> None:
        """Remove contact and stamp/ticket state for a blocked destination."""
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return
        try:
            contact = self._resolve_contact_for_hash(destination_hash, context=ctx)
            if contact and contact.get("id"):
                ctx.database.contacts.delete_contact(contact["id"])
        except Exception as e:
            print(f"_delete_contact_and_stamp_ticket: contact delete failed: {e}")

        try:
            # Remove stamp costs and tickets from LXMRouter
            if ctx.message_router:
                dest_bytes = bytes.fromhex(destination_hash)
                # Remove outbound stamp cost
                if hasattr(ctx.message_router, "outbound_stamp_costs"):
                    ctx.message_router.outbound_stamp_costs.pop(dest_bytes, None)
                # Remove tickets
                if hasattr(ctx.message_router, "available_tickets"):
                    ctx.message_router.available_tickets["outbound"].pop(
                        dest_bytes,
                        None,
                    )
                    ctx.message_router.available_tickets["inbound"].pop(
                        dest_bytes,
                        None,
                    )
                    ctx.message_router.available_tickets["last_deliveries"].pop(
                        dest_bytes,
                        None,
                    )
                # Persist changes
                if hasattr(ctx.message_router, "save_outbound_stamp_costs"):
                    ctx.message_router.save_outbound_stamp_costs()
                if hasattr(ctx.message_router, "save_available_tickets"):
                    ctx.message_router.save_available_tickets()
        except Exception as e:
            print(f"_delete_contact_and_stamp_ticket: stamp/ticket cleanup failed: {e}")

    def _peer_hashes_for_banishment(self, destination_hash: str, context=None) -> list:
        """Identity and destination hashes that must be blocked or unblocked together."""
        destination_hash = normalize_hex_identifier(destination_hash)
        related = self._related_hashes_for_contact_lookup(
            destination_hash,
            context=context,
        )
        hashes = []
        seen = set()
        for peer_hash in (destination_hash, *related):
            if not peer_hash or peer_hash in seen:
                continue
            if len(peer_hash) != 32:
                continue
            seen.add(peer_hash)
            hashes.append(peer_hash)
        return hashes

    def banish_lxmf_peer(self, destination_hash: str, context=None) -> None:
        """Banish a peer by identity: persist every known dest, blackhole, wipe history."""
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return
        destination_hash = normalize_hex_identifier(destination_hash)
        if not destination_hash or len(destination_hash) != 32:
            return
        hashes = self._peer_hashes_for_banishment(destination_hash, context=ctx)
        try:
            for peer_hash in hashes:
                ctx.database.misc.add_blocked_destination(peer_hash)
                self._delete_contact_and_stamp_ticket(peer_hash, context=ctx)
        except Exception as e:
            print(f"banish_lxmf_peer: failed: {e}")
            return
        self._lxmf_reticulum_enforce_block(destination_hash, context=ctx)
        handler = getattr(ctx, "message_handler", None)
        local_dest = getattr(ctx, "local_lxmf_destination", None)
        if handler is not None and local_dest is not None:
            try:
                local_hash = local_dest.hash.hex()
                for peer_hash in hashes:
                    handler.delete_conversation(local_hash, peer_hash)
            except Exception as e:
                print(f"banish_lxmf_peer: conversation delete failed: {e}")
        AsyncUtils.run_async(self._broadcast_blocked_destinations())
        self.sync_telephone_call_policy(context=ctx)

    def lift_lxmf_peer_banishment(self, destination_hash: str, context=None) -> None:
        """Lift banishment for an identity and every known destination hash."""
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return
        destination_hash = normalize_hex_identifier(destination_hash)
        if not destination_hash or len(destination_hash) != 32:
            return
        hashes = self._peer_hashes_for_banishment(destination_hash, context=ctx)
        for peer_hash in hashes:
            try:
                ctx.database.misc.delete_blocked_destination(peer_hash)
            except Exception as e:
                print(f"lift_lxmf_peer_banishment: delete {peer_hash} failed: {e}")
        try:
            if (
                hasattr(self, "reticulum")
                and self.reticulum
                and hasattr(self.reticulum, "unblackhole_identity")
            ):
                seen = set()
                for peer_hash in hashes:
                    raw = hex_identifier_to_bytes(peer_hash)
                    if not raw or raw in seen:
                        continue
                    seen.add(raw)
                    try:
                        self.reticulum.unblackhole_identity(raw)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Failed to unblackhole identity in Reticulum: {e}")
        AsyncUtils.run_async(self._broadcast_blocked_destinations())
        self.sync_telephone_call_policy(context=ctx)

    def check_spam_keywords(self, title: str, content: str, context=None) -> bool:
        """Return whether title/content match configured spam keywords."""
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return False
        try:
            return ctx.database.misc.check_spam_keywords(title, content)
        except Exception:
            return False

    def _apply_lxmf_flood_stamp_cost(self, cost: int, context=None) -> None:
        """Apply the given inbound stamp cost for flood protection and re-announce."""
        ctx = context or self.current_context
        if not ctx or not ctx.message_router or not ctx.local_lxmf_destination:
            return
        cost = max(0, min(254, cost))
        if cost < 1:
            cost = 0
        ctx.config.lxmf_inbound_stamp_cost.set(cost)
        ctx.message_router.set_inbound_stamp_cost(
            ctx.local_lxmf_destination.hash,
            cost,
        )
        if cost > 0:
            ctx.message_router.enforce_stamps()
        elif hasattr(ctx.message_router, "ignore_stamps"):
            ctx.message_router.ignore_stamps()
        try:
            ctx.local_lxmf_destination.display_name = ctx.config.display_name.get()
            ctx.message_router.announce(
                destination_hash=ctx.local_lxmf_destination.hash,
            )
        except Exception as e:
            print(f"_apply_lxmf_flood_stamp_cost: re-announce failed: {e}")

    def _check_lxmf_flood_protection(self, context=None) -> None:
        """Check incoming LXMF message rate and auto-adjust stamp cost if flooding."""
        ctx = context or self.current_context
        if not ctx or not ctx.config:
            return
        if not ctx.config.lxmf_flood_protection_enabled.get():
            return
        # Do not interfere when block strangers is active (it uses max stamp)
        if ctx.config.block_all_from_strangers.get():
            return

        now = time.time()
        self._lxmf_incoming_timestamps = prune_lxmf_incoming_timestamps(
            self._lxmf_incoming_timestamps,
            now=now,
        )
        msgs_per_minute = len(
            [t for t in self._lxmf_incoming_timestamps if now - t <= 60.0],
        )

        threshold = ctx.config.lxmf_flood_threshold_per_minute.get()
        max_cost = ctx.config.lxmf_flood_max_stamp_cost.get()
        current_cost = ctx.config.lxmf_inbound_stamp_cost.get()
        current_cost = max(current_cost, 0)

        # Determine base cost (the normal non-flood cost)
        if self._flood_protection_current_cost is not None:
            base_cost = self._flood_protection_current_cost
        else:
            base_cost = current_cost

        if msgs_per_minute > threshold:
            # Flood detected: bump stamp cost
            new_cost = min(current_cost + 2, max_cost)
            if new_cost != current_cost:
                print(
                    f"LXMF flood detected: {msgs_per_minute} msg/min "
                    f"(threshold {threshold}). Raising stamp cost from "
                    f"{current_cost} to {new_cost}.",
                )
                if self._flood_protection_current_cost is None:
                    self._flood_protection_current_cost = base_cost
                self._flood_protection_last_bump_time = now
                self._apply_lxmf_flood_stamp_cost(new_cost, context=ctx)
        elif current_cost > base_cost:
            cooldown = ctx.config.lxmf_flood_cooldown_seconds.get()
            if now - self._flood_protection_last_bump_time > cooldown:
                # Step down by 1 toward base cost
                new_cost = max(current_cost - 1, base_cost)
                if new_cost != current_cost:
                    print(
                        f"LXMF flood subsided: {msgs_per_minute} msg/min. "
                        f"Lowering stamp cost from {current_cost} to {new_cost}.",
                    )
                    self._apply_lxmf_flood_stamp_cost(new_cost, context=ctx)
                if new_cost == base_cost:
                    self._flood_protection_current_cost = None
                    self._flood_protection_last_bump_time = 0

    async def lxmf_flood_protection_cooldown_loop(self, session_id, context=None):
        """Background loop to step down flood protection stamp cost during quiet periods."""
        ctx = context or self.current_context
        if not ctx:
            return
        await asyncio.sleep(60)
        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                self._check_lxmf_flood_protection(context=ctx)
            except Exception as e:
                print(f"lxmf_flood_protection_cooldown_loop error: {e}")
            await asyncio.sleep(30)

    def _collect_lxmf_sieve_peer_haystack(
        self,
        peer_hash: str,
        context=None,
        contact=None,
    ) -> str:
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return ""
        parts: list[str] = []
        nm = self.get_lxmf_conversation_name(peer_hash, default_name="")
        if nm:
            parts.append(str(nm))
        custom = self.get_custom_destination_display_name(peer_hash)
        if custom:
            parts.append(str(custom))
        if contact is None:
            contact = ctx.database.contacts.get_contact_by_identity_hash(peer_hash)
        if contact:
            if contact.get("name"):
                parts.append(str(contact["name"]))
            if contact.get("lxmf_address"):
                parts.append(str(contact["lxmf_address"]))
        return " ".join(parts)

    def _lxmf_sieve_message_haystack(
        self,
        message_title: str | bytes | None,
        message_content: str | bytes | None,
    ) -> str | None:
        if message_title is None and message_content is None:
            return None

        def norm(x):
            if x is None:
                return ""
            if isinstance(x, bytes):
                return x.decode("utf-8", errors="replace")
            return str(x)

        t = norm(message_title).strip()
        c = norm(message_content).strip()
        if not t and not c:
            return ""
        return f"{t} {c}".strip()

    def _evaluate_lxmf_sieve_for_peer(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.config:
            return None
        raw = ctx.config.lxmf_sieve_filters_json.get()
        rules = parse_lxmf_sieve_filters_json(raw)
        contact = ctx.database.contacts.get_contact_by_identity_hash(peer_hash)
        is_contact = bool(contact)
        haystack = self._collect_lxmf_sieve_peer_haystack(
            peer_hash,
            context=ctx,
            contact=contact,
        )
        msg_hs = self._lxmf_sieve_message_haystack(message_title, message_content)
        return first_matching_lxmf_sieve_rule(
            rules,
            haystack,
            is_contact=is_contact,
            message_haystack=msg_hs,
        )

    def _lxmf_sieve_suppresses_notifications(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ) -> bool:
        m = self._evaluate_lxmf_sieve_for_peer(
            peer_hash,
            context=context,
            message_title=message_title,
            message_content=message_content,
        )
        if not m:
            return False
        return m.get("action") in ("hide", "ignore", "banish")

    def _lxmf_sieve_hides_peer(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ) -> bool:
        m = self._evaluate_lxmf_sieve_for_peer(
            peer_hash,
            context=context,
            message_title=message_title,
            message_content=message_content,
        )
        return bool(m and m.get("action") == "hide")

    def _apply_lxmf_sieve_folder_rule(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ):
        m = self._evaluate_lxmf_sieve_for_peer(
            peer_hash,
            context=context,
            message_title=message_title,
            message_content=message_content,
        )
        if not m or m.get("action") != "folder":
            return
        fid = m.get("folder_id")
        if fid is None:
            return
        try:
            fid_int = int(fid)
        except (TypeError, ValueError):
            return
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return
        try:
            ctx.database.messages.move_conversation_to_folder(peer_hash, fid_int)
        except Exception:
            pass

    def _apply_lxmf_sieve_banish_rule(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ):
        m = self._evaluate_lxmf_sieve_for_peer(
            peer_hash,
            context=context,
            message_title=message_title,
            message_content=message_content,
        )
        if not m or m.get("action") != "banish":
            return
        self.banish_lxmf_peer(peer_hash, context=context)

    def _apply_message_blocklist_banish_rule(
        self,
        peer_hash: str,
        context=None,
        *,
        message_title=None,
        message_content=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.config:
            return
        if not ctx.config.message_blocklist_enabled.get():
            return
        raw = ctx.config.message_blocklist_json.get()
        blocklist = parse_message_blocklist_json(raw)
        contact = None
        is_contact = False
        if ctx.database:
            contact = ctx.database.contacts.get_contact_by_identity_hash(peer_hash)
            is_contact = bool(contact)
        haystack = self._collect_lxmf_sieve_peer_haystack(
            peer_hash,
            context=ctx,
            contact=contact,
        )
        msg_hs = self._lxmf_sieve_message_haystack(message_title, message_content)
        match = first_matching_blocklist_entry(
            blocklist,
            haystack,
            is_contact=is_contact,
            message_haystack=msg_hs,
        )
        if not match:
            return
        print(
            f"Message blocklist matched entry {match.get('entry_id')} for {peer_hash}; banishing",
        )
        self.banish_lxmf_peer(peer_hash, context=ctx)

    def on_lxmf_delivery(self, lxmf_message: LXMF.LXMessage, context=None):
        """Handle inbound LXMF delivery from Reticulum (synchronous callback)."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.database:
            logger.warning(
                "Dropping inbound LXMF delivery: context not ready "
                "(ctx=%s running=%s database=%s)",
                ctx is not None,
                getattr(ctx, "running", None) if ctx else None,
                ctx.database is not None if ctx else None,
            )
            return

        try:
            source_hash = lxmf_message.source_hash.hex()
            unverified_reason = getattr(lxmf_message, "unverified_reason", None)

            if unverified_reason == LXMF.LXMessage.SIGNATURE_INVALID:
                logger.warning("Invalid LXMF signature from %s, dropping", source_hash)
                return

            # check if source is blocked - reject immediately
            if self.is_destination_blocked(source_hash, context=ctx):
                print(f"Rejecting LXMF message from blocked source: {source_hash}")
                return

            # track incoming message timestamps for flood protection
            self._lxmf_incoming_timestamps.append(time.time())
            self._lxmf_incoming_timestamps = prune_lxmf_incoming_timestamps(
                self._lxmf_incoming_timestamps,
            )
            self._check_lxmf_flood_protection(context=ctx)

            if ctx.config.block_all_from_strangers.get() and not self._is_contact(
                source_hash,
                context=ctx,
            ):
                print(
                    f"Blocking entire message from stranger: {source_hash}",
                )
                return

            is_sideband_telemetry_request = False
            lxmf_fields = lxmf_message.get_fields()

            # FIELD_COMMANDS (9) is the LXMF-standard command slot.
            # Field 0x01 is FIELD_EMBEDDED_LXMS on the wire. Sideband also put
            # telemetry requests there historically, so only treat Sideband-shaped
            # entries as commands and leave packed embedded LXMs alone.
            commands = []
            if LXMF.FIELD_COMMANDS in lxmf_fields:
                commands.extend(
                    extract_sideband_command_entries(lxmf_fields[LXMF.FIELD_COMMANDS]),
                )
            embedded_field = getattr(LXMF, "FIELD_EMBEDDED_LXMS", 0x01)
            if embedded_field in lxmf_fields and embedded_field != LXMF.FIELD_COMMANDS:
                commands.extend(
                    extract_sideband_command_entries(lxmf_fields[embedded_field]),
                )

            if commands:
                for command in commands:
                    if (
                        (
                            isinstance(command, dict)
                            and (
                                SidebandCommands.TELEMETRY_REQUEST in command
                                or str(SidebandCommands.TELEMETRY_REQUEST) in command
                                or f"0x{SidebandCommands.TELEMETRY_REQUEST:02x}"
                                in command
                            )
                        )
                        or (
                            isinstance(command, (list, tuple))
                            and SidebandCommands.TELEMETRY_REQUEST in command
                        )
                        or command == SidebandCommands.TELEMETRY_REQUEST
                        or str(command) == str(SidebandCommands.TELEMETRY_REQUEST)
                    ):
                        is_sideband_telemetry_request = True
                    if (
                        isinstance(command, dict)
                        and SidebandCommands.PLUGIN_COMMAND in command
                        and lxmf_signature_validated(lxmf_message)
                    ):
                        plugin_command = command.get(SidebandCommands.PLUGIN_COMMAND)
                        if isinstance(plugin_command, bytes):
                            plugin_command = plugin_command.decode(
                                "utf-8",
                                errors="replace",
                            )
                        if isinstance(plugin_command, str) and plugin_command.strip():
                            try:
                                self.sideband_plugin_loader.handle_plugin_command(
                                    plugin_command,
                                    lxmf_message,
                                )
                            except Exception as exc:
                                print(f"Sideband plugin command failed: {exc}")

            # Respond to telemetry requests as a side effect. Do not return early:
            # spam, stranger-attachment, and drop policies must still run.
            if is_sideband_telemetry_request:
                if not ctx.config.telemetry_enabled.get():
                    print(f"Telemetry is disabled, ignoring request from {source_hash}")
                elif not lxmf_signature_validated(lxmf_message):
                    print(
                        f"Ignoring unsigned telemetry request from {source_hash}",
                    )
                else:
                    contact = ctx.database.contacts.get_contact_by_identity_hash(
                        source_hash,
                    )
                    if not contact or not contact.get("is_telemetry_trusted"):
                        print(
                            f"Telemetry request from untrusted peer {source_hash}, ignoring",
                        )
                    else:
                        lat, lon = self._resolve_location_for_telemetry()
                        if lat is not None and lon is not None:
                            print(f"Responding to telemetry request from {source_hash}")
                            self.handle_telemetry_request(source_hash)
                        else:
                            if not hasattr(self, "_telemetry_no_location_warned"):
                                self._telemetry_no_location_warned = set()
                            if source_hash not in self._telemetry_no_location_warned:
                                if len(self._telemetry_no_location_warned) >= 256:
                                    self._telemetry_no_location_warned.clear()
                                self._telemetry_no_location_warned.add(source_hash)
                                print(
                                    f"Cannot respond to telemetry request from {source_hash}: No location set. "
                                    "Set manual coordinates in Settings > Location to respond.",
                                )

            # check for spam keywords
            is_spam = False
            message_title = lxmf_message.title if hasattr(lxmf_message, "title") else ""
            message_content = (
                lxmf_message.content if hasattr(lxmf_message, "content") else ""
            )
            if isinstance(message_content, bytes):
                message_content = message_content.decode("utf-8", errors="replace")
            elif message_content is None:
                message_content = ""
            if isinstance(message_title, bytes):
                message_title = message_title.decode("utf-8", errors="replace")
            elif message_title is None:
                message_title = ""

            is_reaction_only = lxmf_is_reaction_only_delivery(
                lxmf_fields,
                message_title,
                message_content,
            )

            # check spam keywords (reaction+body must not skip spam)
            if not is_reaction_only and self.check_spam_keywords(
                message_title,
                message_content,
                context=ctx,
            ):
                is_spam = True
                print(
                    f"Marking LXMF message as spam due to keyword match: {source_hash}",
                )

            # reject attachments from blocked sources (already checked above, but double-check)
            attachments_stripped = False
            if has_attachments(lxmf_fields):
                if self.is_destination_blocked(source_hash, context=ctx):
                    print(
                        f"Rejecting LXMF message with attachments from blocked source: {source_hash}",
                    )
                    return
                # reject attachments from spam sources
                if is_spam:
                    print(
                        f"Rejecting LXMF message with attachments from spam source: {source_hash}",
                    )
                    return
                # strip attachments from strangers (non-contacts) if setting is enabled
                if (
                    ctx.config.block_attachments_from_strangers.get()
                    and not self._is_contact(source_hash, context=ctx)
                ):
                    for key in (
                        LXMF.FIELD_FILE_ATTACHMENTS,
                        LXMF.FIELD_IMAGE,
                        LXMF.FIELD_AUDIO,
                    ):
                        if key in lxmf_fields:
                            del lxmf_fields[key]
                    lxmf_message.fields = lxmf_fields
                    attachments_stripped = True
                    print(
                        f"Stripped attachments from stranger: {source_hash}",
                    )

            # upsert lxmf message to database with spam flag
            self.db_upsert_lxmf_message(
                lxmf_message,
                is_spam=is_spam,
                attachments_stripped=attachments_stripped,
                context=ctx,
            )
            self._maybe_store_path_at_send_for_lxmf(ctx, lxmf_message)

            # handle forwarding
            if lxmf_signature_validated(lxmf_message):
                self.handle_forwarding(lxmf_message, context=ctx)

            self._apply_lxmf_sieve_folder_rule(
                source_hash,
                context=ctx,
                message_title=message_title,
                message_content=message_content,
            )
            self._apply_lxmf_sieve_banish_rule(
                source_hash,
                context=ctx,
                message_title=message_title,
                message_content=message_content,
            )
            self._apply_message_blocklist_banish_rule(
                source_hash,
                context=ctx,
                message_title=message_title,
                message_content=message_content,
            )

            # handle telemetry
            try:
                if lxmf_signature_validated(lxmf_message):
                    message_fields = lxmf_message.get_fields()

                    # Single telemetry entry
                    if LXMF.FIELD_TELEMETRY in message_fields:
                        self.process_incoming_telemetry(
                            source_hash,
                            message_fields[LXMF.FIELD_TELEMETRY],
                            lxmf_message,
                            context=ctx,
                        )

                    # Telemetry stream (multiple entries)
                    if (
                        hasattr(LXMF, "FIELD_TELEMETRY_STREAM")
                        and LXMF.FIELD_TELEMETRY_STREAM in message_fields
                    ):
                        stream = message_fields[LXMF.FIELD_TELEMETRY_STREAM]
                        if isinstance(stream, (list, tuple)):
                            sender_trusted = False
                            contact = (
                                ctx.database.contacts.get_contact_by_identity_hash(
                                    source_hash,
                                )
                            )
                            if contact and contact.get("is_telemetry_trusted"):
                                sender_trusted = True
                            for entry in stream:
                                if (
                                    not isinstance(entry, (list, tuple))
                                    or len(entry) < 3
                                ):
                                    continue
                                entry_source = normalize_lxmf_destination_hash(entry[0])
                                if not entry_source:
                                    continue
                                if entry_source != source_hash and not sender_trusted:
                                    continue
                                entry_timestamp = _valid_number(entry[1])
                                if entry_timestamp is None:
                                    continue
                                entry_data = entry[2]
                                self.process_incoming_telemetry(
                                    entry_source,
                                    entry_data,
                                    lxmf_message,
                                    timestamp_override=int(entry_timestamp),
                                    context=ctx,
                                )
            except Exception as e:
                print(f"Failed to handle telemetry in LXMF message: {e}")

            # update lxmf user icon if icon appearance field is available
            try:
                if lxmf_signature_validated(lxmf_message):
                    message_fields = lxmf_message.get_fields()
                    icon_appearance = parse_lxmf_icon_appearance(
                        message_fields.get(LXMF.FIELD_ICON_APPEARANCE),
                    )
                    if icon_appearance:
                        icon_name, foreground_colour, background_colour = (
                            icon_appearance
                        )

                        local_hash = (
                            ctx.local_lxmf_destination.hexhash
                            if ctx.local_lxmf_destination
                            else None
                        )
                        source_hash = lxmf_message.source_hash.hex()

                        # ignore our own icon and empty payloads to avoid overwriting peers with our appearance
                        if (
                            source_hash and local_hash and source_hash == local_hash
                        ) or (
                            not icon_name
                            or not foreground_colour
                            or not background_colour
                        ):
                            pass
                        else:
                            local_icon_name = ctx.config.lxmf_user_icon_name.get()
                            local_icon_fg = (
                                ctx.config.lxmf_user_icon_foreground_colour.get()
                            )
                            local_icon_bg = (
                                ctx.config.lxmf_user_icon_background_colour.get()
                            )

                            # if incoming icon matches our own, skip storing and clear any mistaken stored copy
                            # for now, but this will need to be updated later if two users do have the same icon
                            if (
                                local_icon_name
                                and local_icon_fg
                                and local_icon_bg
                                and icon_name == local_icon_name
                                and foreground_colour == local_icon_fg
                                and background_colour == local_icon_bg
                            ):
                                ctx.database.misc.delete_user_icon(source_hash)
                            else:
                                self.update_lxmf_user_icon(
                                    source_hash,
                                    icon_name,
                                    foreground_colour,
                                    background_colour,
                                    context=ctx,
                                )
            except Exception as e:
                print("failed to update lxmf user icon from lxmf message")
                print(e)

            sender_name = ctx.database.announces.get_custom_display_name(source_hash)
            if not sender_name:
                announce = ctx.database.announces.get_announce_by_hash(source_hash)
                if announce and announce["app_data"]:
                    sender_name = parse_lxmf_display_name(
                        app_data_base64=announce["app_data"],
                        default_value=None,
                    )

            if not sender_name:
                sender_name = source_hash[:8]

            msg_dict = convert_lxmf_message_to_dict(
                lxmf_message,
                include_attachments=False,
                reticulum=self.reticulum,
            )
            self._merge_stored_path_fields_from_db(
                ctx,
                lxmf_message.hash.hex(),
                msg_dict,
            )

            suppress_notifications = self._lxmf_sieve_suppresses_notifications(
                source_hash,
                context=ctx,
                message_title=message_title,
                message_content=message_content,
            )

            AsyncUtils.run_async(
                self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf.delivery",
                            "remote_identity_name": sender_name,
                            "lxmf_message": msg_dict,
                            "sieve_suppress_notifications": suppress_notifications,
                        },
                    ),
                ),
            )

        except Exception as e:
            # do nothing on error
            print(f"lxmf_delivery error: {e}")

    # handles lxmf message forwarding logic
    def handle_forwarding(self, lxmf_message: LXMF.LXMessage, context=None):
        try:
            ctx = context or self.current_context
            if not ctx:
                return
            if not lxmf_signature_validated(lxmf_message):
                return

            source_hash = lxmf_message.source_hash.hex()
            destination_hash = lxmf_message.destination_hash.hex()

            # extract fields for potential forwarding
            lxmf_fields = lxmf_message.get_fields()
            image_field = None
            audio_field = None
            file_attachments_field = None

            if LXMF.FIELD_IMAGE in lxmf_fields:
                parsed_image = parse_lxmf_image_field_value(
                    lxmf_fields[LXMF.FIELD_IMAGE],
                )
                if parsed_image:
                    image_field = LxmfImageField(parsed_image[0], parsed_image[1])

            if LXMF.FIELD_AUDIO in lxmf_fields:
                parsed_audio = parse_lxmf_audio_field_value(
                    lxmf_fields[LXMF.FIELD_AUDIO],
                )
                if parsed_audio:
                    audio_field = LxmfAudioField(parsed_audio[0], parsed_audio[1])

            if LXMF.FIELD_FILE_ATTACHMENTS in lxmf_fields:
                parsed_files = parse_lxmf_file_attachments_field_value(
                    lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS],
                )
                if parsed_files:
                    attachments = [
                        LxmfFileAttachment(name, data) for name, data in parsed_files
                    ]
                    file_attachments_field = LxmfFileAttachmentsField(attachments)

            app_extensions = None
            if LXMF_APP_EXTENSIONS_FIELD in lxmf_fields and isinstance(
                lxmf_fields[LXMF_APP_EXTENSIONS_FIELD],
                dict,
            ):
                app_extensions = lxmf_fields[LXMF_APP_EXTENSIONS_FIELD]

            # check if this message is for an alias identity (REPLY PATH)
            mapping = ctx.database.messages.get_forwarding_mapping(
                alias_hash=destination_hash,
            )

            if mapping:
                # this is a reply from User C to User B (alias). Forward to User A.
                print(
                    f"Forwarding reply from {source_hash} back to original sender {mapping['original_sender_hash']}",
                )
                AsyncUtils.run_async(
                    self.send_message(
                        destination_hash=mapping["original_sender_hash"],
                        content=lxmf_message.content,
                        title=lxmf_message.title
                        if hasattr(lxmf_message, "title")
                        else "",
                        image_field=image_field,
                        audio_field=audio_field,
                        file_attachments_field=file_attachments_field,
                        app_extensions=app_extensions,
                        context=ctx,
                    ),
                )
                return

            # check if this message matches a forwarding rule (FORWARD PATH)
            # we check for rules that apply to the destination of this message
            rules = ctx.database.misc.get_forwarding_rules(
                identity_hash=destination_hash,
                active_only=True,
            )

            for rule in rules:
                # check source filter if set
                if (
                    rule["source_filter_hash"]
                    and rule["source_filter_hash"] != source_hash
                ):
                    continue

                # find or create mapping for this (Source, Final Recipient) pair
                mapping = ctx.forwarding_manager.get_or_create_mapping(
                    source_hash,
                    rule["forward_to_hash"],
                    destination_hash,
                )

                # forward to User C from Alias Identity
                print(
                    f"Forwarding message from {source_hash} to {rule['forward_to_hash']} via alias {mapping['alias_hash']}",
                )
                AsyncUtils.run_async(
                    self.send_message(
                        destination_hash=rule["forward_to_hash"],
                        content=lxmf_message.content,
                        title=lxmf_message.title
                        if hasattr(lxmf_message, "title")
                        else "",
                        sender_identity_hash=mapping["alias_hash"],
                        image_field=image_field,
                        audio_field=audio_field,
                        file_attachments_field=file_attachments_field,
                        app_extensions=app_extensions,
                        context=ctx,
                    ),
                )
        except Exception as e:
            print(f"Error in handle_forwarding: {e}")
            import traceback

            traceback.print_exc()

    def _merge_stored_path_fields_from_db(self, ctx, msg_hash_hex, msg_dict):
        try:
            row = ctx.database.messages.get_lxmf_message_by_hash(msg_hash_hex)
            if not row:
                return

            def _scalar_row_value(key):
                try:
                    if hasattr(row, "get"):
                        v = row.get(key)
                    elif hasattr(row, "keys") and key in row.keys():
                        v = row[key]
                    else:
                        return None
                except Exception:
                    return None
                if isinstance(v, (bool, int, float, str)):
                    return v
                return None

            hops = _scalar_row_value("path_hops_at_send")
            if hops is not None:
                msg_dict["path_hops_at_send"] = hops
            iface = _scalar_row_value("path_interface_at_send")
            if iface is not None:
                msg_dict["path_interface_at_send"] = iface
            pfm = _scalar_row_value("path_finding_measure")
            if pfm is not None:
                msg_dict["path_finding_measure"] = pfm
            prh = _scalar_row_value("path_row_hash_hex")
            if prh is not None:
                msg_dict["path_row_hash_hex"] = prh
        except Exception:
            pass

    def _reticulum_path_hops_and_interface_to_identity(self, ctx, identity_hash_bytes):
        if not identity_hash_bytes:
            return None, None
        try:
            destination_hash = (
                identity_hash_bytes
                if isinstance(identity_hash_bytes, (bytes, bytearray))
                else bytes.fromhex(str(identity_hash_bytes))
            )
        except Exception:
            return None, None
        destination_hash_hex = destination_hash.hex()
        local_hashes: set[str] = set()
        with contextlib.suppress(Exception):
            if ctx and ctx.identity:
                local_hashes.add(ctx.identity.hash.hex())
        with contextlib.suppress(Exception):
            if self.local_lxmf_destination is not None:
                local_hashes.add(self.local_lxmf_destination.hash.hex())
        with contextlib.suppress(Exception):
            if ctx and ctx.message_router:
                pdest = ctx.message_router.propagation_destination
                if pdest is not None and getattr(pdest, "hash", None):
                    local_hashes.add(pdest.hash.hex())

        if destination_hash_hex in local_hashes:
            return 0, "Local"
        if not RNS.Transport.has_path(destination_hash):
            return None, None
        hops = RNS.Transport.hops_to(destination_hash)
        next_hop_bytes = None
        if hasattr(self, "reticulum") and self.reticulum:
            next_hop_bytes = self.reticulum.get_next_hop(destination_hash)
        if next_hop_bytes is None:
            return None, None
        iface = (
            self.reticulum.get_next_hop_if_name(destination_hash)
            if hasattr(self, "reticulum") and self.reticulum
            else None
        )
        return hops, iface

    def _maybe_store_path_at_send_for_lxmf(self, ctx, lxmf_message):
        try:
            msg_hash = lxmf_message.hash.hex()
            row = ctx.database.messages.get_lxmf_message_by_hash(msg_hash)
            if not row or row.get("path_hops_at_send") is not None:
                return
            if getattr(lxmf_message, "incoming", False):
                dest_bytes = lxmf_message.source_hash
            else:
                dest_bytes = lxmf_message.destination_hash
            hops, iface = self._reticulum_path_hops_and_interface_to_identity(
                ctx,
                dest_bytes,
            )
            if hops is None:
                return
            ctx.database.messages.set_lxmf_message_path_at_send_if_unset(
                msg_hash,
                hops,
                iface,
            )
        except Exception:
            pass

    def on_lxmf_sending_state_updated(self, lxmf_message, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return

        progress_pct = round(lxmf_message.progress * 100, 2)
        rssi = lxmf_message.rssi
        snr = lxmf_message.snr
        quality = lxmf_message.q
        if self.reticulum:
            if rssi is None:
                rssi = self.reticulum.get_packet_rssi(lxmf_message.hash)
            if snr is None:
                snr = self.reticulum.get_packet_snr(lxmf_message.hash)
            if quality is None:
                quality = self.reticulum.get_packet_q(lxmf_message.hash)

        ctx.database.messages.update_lxmf_message_state(
            message_hash=lxmf_message.hash.hex(),
            state=convert_lxmf_state_to_string(lxmf_message),
            progress=progress_pct,
            delivery_attempts=lxmf_message.delivery_attempts,
            next_delivery_attempt_at=getattr(
                lxmf_message,
                "next_delivery_attempt",
                None,
            ),
            rssi=rssi,
            snr=snr,
            quality=quality,
            method=convert_lxmf_method_to_string(lxmf_message),
        )
        self._maybe_store_path_at_send_for_lxmf(ctx, lxmf_message)

        msg_dict = convert_lxmf_message_to_dict(
            lxmf_message,
            include_attachments=False,
            reticulum=self.reticulum,
            message_router=ctx.message_router,
        )
        self._merge_stored_path_fields_from_db(ctx, lxmf_message.hash.hex(), msg_dict)

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": msg_dict,
                    },
                ),
            ),
        )

    # handle delivery failed for an outbound lxmf message
    def on_lxmf_sending_failed(self, lxmf_message, context=None):
        ctx = context if context is not None else self.current_context
        # check if this failed message should fall back to sending via a propagation node
        if (
            lxmf_message.state == LXMF.LXMessage.FAILED
            and hasattr(lxmf_message, "try_propagation_on_fail")
            and lxmf_message.try_propagation_on_fail
        ):
            self.send_failed_message_via_propagation_node(lxmf_message, context=ctx)

        # update state
        self.on_lxmf_sending_state_updated(lxmf_message, context=ctx)

    # sends a previously failed message via a propagation node
    def send_failed_message_via_propagation_node(
        self,
        lxmf_message: LXMF.LXMessage,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # reset internal message state
        lxmf_message.packed = None
        lxmf_message.delivery_attempts = 0
        if hasattr(lxmf_message, "next_delivery_attempt"):
            del lxmf_message.next_delivery_attempt

        # this message should now be sent via a propagation node
        lxmf_message.desired_method = LXMF.LXMessage.PROPAGATED
        lxmf_message.try_propagation_on_fail = False

        # resend message
        source_hash = lxmf_message.source_hash.hex()
        router = ctx.message_router
        if (
            ctx.forwarding_manager
            and source_hash in ctx.forwarding_manager.forwarding_routers
        ):
            router = ctx.forwarding_manager.forwarding_routers[source_hash]
        router.handle_outbound(lxmf_message)

    # upserts the provided lxmf message to the database
    def _is_self_lxmf_destination(self, destination_hash: str, context=None) -> bool:
        """True when destination_hash refers to this identity's own LXMF peer."""
        ctx = context or self.current_context
        if not ctx or not ctx.local_lxmf_destination:
            return False
        norm_dest = normalize_hex_identifier(destination_hash)
        if not norm_dest:
            return False
        local_lxmf = normalize_hex_identifier(ctx.local_lxmf_destination.hexhash)
        if norm_dest == local_lxmf:
            return True
        if ctx.identity:
            local_id = normalize_hex_identifier(ctx.identity.hash.hex())
            if norm_dest == local_id:
                return True
        try:
            resolved = self.get_lxmf_destination_hash_for_identity_hash(norm_dest)
            if resolved and normalize_hex_identifier(resolved) == local_lxmf:
                return True
        except Exception:
            pass
        return False

    def db_upsert_lxmf_message(
        self,
        lxmf_message: LXMF.LXMessage,
        is_spam: bool = False,
        attachments_stripped: bool = False,
        context=None,
        path_finding_measure: str | None = None,
        path_row_hash_hex: str | None = None,
        state_override: str | None = None,
        method_override: str | None = None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # convert lxmf message to dict
        lxmf_message_dict = convert_lxmf_message_to_dict(
            lxmf_message,
            reticulum=self.reticulum,
            message_router=ctx.message_router,
        )
        if state_override is not None:
            lxmf_message_dict["state"] = state_override
        if method_override is not None:
            lxmf_message_dict["method"] = method_override
        lxmf_message_dict["is_spam"] = 1 if is_spam else 0
        lxmf_message_dict["attachments_stripped"] = 1 if attachments_stripped else 0
        if path_finding_measure is not None:
            lxmf_message_dict["path_finding_measure"] = path_finding_measure
        if path_row_hash_hex is not None:
            lxmf_message_dict["path_row_hash_hex"] = path_row_hash_hex

        # calculate peer hash
        local_hash = ctx.local_lxmf_destination.hexhash
        if lxmf_message_dict["source_hash"] == local_hash:
            lxmf_message_dict["peer_hash"] = lxmf_message_dict["destination_hash"]
        else:
            lxmf_message_dict["peer_hash"] = lxmf_message_dict["source_hash"]

        try:
            ctx.database.messages.upsert_lxmf_message(lxmf_message_dict)
        except Exception:
            message_hash = getattr(lxmf_message, "hash", None)
            hash_label = message_hash.hex() if message_hash is not None else "unknown"
            logger.exception(
                "Failed to persist inbound LXMF message %s from %s",
                hash_label,
                lxmf_message_dict.get("source_hash", "unknown"),
            )
            raise

    def _lxmf_path_wait_seconds(self):
        return reticulum_pathfinding.lxmf_path_wait_cap_seconds()

    async def _await_transport_path(self, destination_hash_bytes: bytes):
        r = self.reticulum if hasattr(self, "reticulum") else None
        return await reticulum_pathfinding.await_transport_path_for_outbound_lxmf(
            r,
            destination_hash_bytes,
        )

    # upserts the provided announce to the database
    # handle sending an lxmf message to reticulum
    async def send_message(
        self,
        destination_hash: str,
        content: str,
        image_field: LxmfImageField = None,
        audio_field: LxmfAudioField = None,
        file_attachments_field: LxmfFileAttachmentsField = None,
        telemetry_data: bytes | None = None,
        commands: list | None = None,
        delivery_method: str | None = None,
        title: str = "",
        sender_identity_hash: str | None = None,
        reply_to_hash: str | None = None,
        reply_quoted_content: str | None = None,
        reaction_to_hash: str | None = None,
        reaction_emoji: str | None = None,
        app_extensions: dict | None = None,
        no_display: bool = False,
        context=None,
    ) -> LXMF.LXMessage:
        ctx = context or self.current_context
        if not ctx:
            raise RuntimeError("No identity context available for sending message")

        if isinstance(content, bytes):
            content_str = content.decode("utf-8", errors="replace")
        else:
            content_str = content or ""
        quoted_str = reply_quoted_content or ""
        has_standard_reaction = (
            reaction_to_hash is not None and reaction_emoji is not None
        )
        is_reaction_only = bool(
            has_standard_reaction
            and not (content_str and content_str.strip())
            and image_field is None
            and audio_field is None
            and file_attachments_field is None
            and telemetry_data is None
            and commands is None
            and reply_to_hash is None
            and not (quoted_str and quoted_str.strip()),
        )

        # convert destination hash to bytes
        try:
            destination_hash_bytes = bytes.fromhex(destination_hash)
        except (TypeError, ValueError) as exc:
            msg = "Invalid destination hash."
            raise ValueError(msg) from exc

        wants_propagated = delivery_method == "propagated"
        is_local_self = self._is_self_lxmf_destination(destination_hash, ctx)
        if is_local_self and wants_propagated:
            msg = "Propagated delivery is not available for messages to yourself."
            raise ValueError(msg)

        destination_identity = self.recall_identity(destination_hash)
        if destination_identity is None and is_local_self and ctx.identity:
            destination_identity = ctx.identity
        if destination_identity is None:
            msg = (
                "Could not recall destination identity. "
                "Wait for an announce from this peer, then try again."
            )
            raise LookupError(msg)

        delivery_hash_bytes = reticulum_pathfinding.lxmf_delivery_hash_bytes(
            destination_identity,
            destination_hash_bytes,
        )

        # Direct/opportunistic need a live peer path. Propagated uses the
        # propagation node, so skip the peer path wait (still record outcome).
        if is_local_self:
            path_outcome = reticulum_pathfinding.OutboundPathOutcome(
                True,
                "local_self",
                False,
            )
        elif wants_propagated:
            path_outcome = reticulum_pathfinding.OutboundPathOutcome(
                False,
                "skipped_for_propagated",
                False,
            )
        else:
            # Reticulum keeps a live path table, and entries expire when peers move or links drop.
            # We cannot replay "old" paths from the app layer. Transport.request_path refreshes discovery.
            # Wait on lxmf.delivery, not an identity hash or some other aspect dest.
            path_outcome = await self._await_transport_path(delivery_hash_bytes)

        # Direct/opportunistic delivery needs a live transport path. Propagated
        # delivery can proceed without a peer path (it uses the propagation node).
        if (
            not is_local_self
            and not wants_propagated
            and not path_outcome.path_available
        ):
            msg = (
                "No path to destination. "
                "Use Path Finder or wait for a route, then try again."
            )
            raise TimeoutError(msg)

        # create destination for recipients lxmf delivery address
        lxmf_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        # determine how the user wants to send the message
        desired_delivery_method = None
        if delivery_method == "direct":
            desired_delivery_method = LXMF.LXMessage.DIRECT
        elif delivery_method == "opportunistic":
            desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC
        elif delivery_method == "propagated":
            desired_delivery_method = LXMF.LXMessage.PROPAGATED

        # determine how to send the message if the user didn't provide a method
        if desired_delivery_method is None:
            # send messages over a direct link by default
            desired_delivery_method = LXMF.LXMessage.DIRECT
            if (
                not ctx.message_router.delivery_link_available(delivery_hash_bytes)
                and RNS.Identity.current_ratchet_id(delivery_hash_bytes) is not None
            ):
                # since there's no link established to the destination, it's faster to send opportunistically
                # this is because it takes several packets to establish a link, and then we still have to send the message over it
                # oppotunistic mode will send the message in a single packet (if the message is small enough, otherwise it falls back to a direct link)
                # we will only do this if an encryption ratchet is available, so single packet delivery is more secure
                desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC

        # determine which identity to send from
        source_destination = ctx.local_lxmf_destination
        if sender_identity_hash is not None:
            if (
                ctx.forwarding_manager
                and sender_identity_hash
                in ctx.forwarding_manager.forwarding_destinations
            ):
                source_destination = ctx.forwarding_manager.forwarding_destinations[
                    sender_identity_hash
                ]
            else:
                print(
                    f"Warning: requested sender identity {sender_identity_hash} not found, using default.",
                )

        # create lxmf message
        lxmf_message = LXMF.LXMessage(
            lxmf_destination,
            source_destination,
            content,
            title=title,
            desired_method=desired_delivery_method,
        )
        lxmf_message.try_propagation_on_fail = (
            ctx.config.auto_send_failed_messages_to_propagation_node.get()
        )

        lxmf_message.fields = {}

        if not is_reaction_only:
            lxmf_message.fields[LXMF.FIELD_RENDERER] = LXMF.RENDERER_MARKDOWN

        if self._is_contact(destination_hash, context=ctx) and not is_reaction_only:
            lxmf_message.include_ticket = True

        # add file attachments field
        if file_attachments_field is not None:
            # create array of [[file_name, file_bytes], [file_name, file_bytes], ...]
            file_attachments = [
                [file_attachment.file_name, file_attachment.file_bytes]
                for file_attachment in file_attachments_field.file_attachments
            ]

            # set field attachments field
            lxmf_message.fields[LXMF.FIELD_FILE_ATTACHMENTS] = file_attachments

        # add image field
        if image_field is not None:
            lxmf_message.fields[LXMF.FIELD_IMAGE] = [
                image_field.image_type,
                image_field.image_bytes,
            ]

        # add audio field
        if audio_field is not None:
            audio_bytes = audio_field.audio_bytes
            if audio_field.audio_mode == LXMF.AM_OPUS_OGG:
                audio_bytes = self._convert_webm_opus_to_ogg(audio_bytes)
            lxmf_message.fields[LXMF.FIELD_AUDIO] = [
                audio_field.audio_mode,
                audio_bytes,
            ]

        # add telemetry field
        if telemetry_data is not None:
            lxmf_message.fields[LXMF.FIELD_TELEMETRY] = telemetry_data

        # add commands field
        if commands is not None:
            lxmf_message.fields[LXMF.FIELD_COMMANDS] = commands

        if reply_to_hash is not None:
            lxmf_message.fields[FIELD_REPLY_TO] = bytes.fromhex(reply_to_hash)
        if reply_quoted_content is not None and reply_quoted_content:
            lxmf_message.fields[FIELD_REPLY_QUOTE] = reply_quoted_content.encode(
                "utf-8",
            )

        if has_standard_reaction:
            lxmf_message.fields[FIELD_REACTION] = build_lxmf_reaction_field(
                reaction_to_hash,
                reaction_emoji or "",
            )
        elif app_extensions is not None:
            lxmf_message.fields[LXMF_APP_EXTENSIONS_FIELD] = app_extensions

        # add icon appearance if configured and not already sent to this destination
        current_icon_hash = self.get_current_icon_hash()
        if current_icon_hash is not None and not is_reaction_only:
            last_sent_icon_hash = self.database.misc.get_last_sent_icon_hash(
                destination_hash,
            )

            if last_sent_icon_hash != current_icon_hash:
                lxmf_user_icon_name = self.config.lxmf_user_icon_name.get()
                lxmf_user_icon_foreground_colour = (
                    self.config.lxmf_user_icon_foreground_colour.get()
                )
                lxmf_user_icon_background_colour = (
                    self.config.lxmf_user_icon_background_colour.get()
                )

                lxmf_message.fields[LXMF.FIELD_ICON_APPEARANCE] = [
                    lxmf_user_icon_name,
                    ColourUtils.hex_colour_to_byte_array(
                        lxmf_user_icon_foreground_colour,
                    ),
                    ColourUtils.hex_colour_to_byte_array(
                        lxmf_user_icon_background_colour,
                    ),
                ]

                # update last sent icon hash for this destination
                ctx.database.misc.update_last_sent_icon_hash(
                    destination_hash,
                    current_icon_hash,
                )

        if is_local_self:
            lxmf_message.pack()
            lxmf_message.state = LXMF.LXMessage.DELIVERED
            lxmf_message.progress = 1.0
            local_peer = ctx.local_lxmf_destination.hexhash
            if not no_display:
                self.db_upsert_lxmf_message(
                    lxmf_message,
                    context=ctx,
                    path_finding_measure=reticulum_pathfinding.format_outbound_path_finding_measure(
                        path_outcome,
                    ),
                    path_row_hash_hex=local_peer,
                    state_override="delivered",
                    method_override="local",
                )
                ws_payload = convert_lxmf_message_to_dict(
                    lxmf_message,
                    include_attachments=False,
                    reticulum=self.reticulum,
                    message_router=ctx.message_router,
                )
                ws_payload["state"] = "delivered"
                ws_payload["method"] = "local"
                ws_payload["progress"] = 100.0
                await self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf_message_created",
                            "lxmf_message": ws_payload,
                        },
                    ),
                )
            return lxmf_message

        # register delivery callbacks
        lxmf_message.register_delivery_callback(
            lambda msg: self.on_lxmf_sending_state_updated(msg, context=ctx),
        )
        lxmf_message.register_failed_callback(
            lambda msg: self.on_lxmf_sending_failed(msg, context=ctx),
        )

        # determine which router to use
        router = ctx.message_router
        if (
            sender_identity_hash is not None
            and ctx.forwarding_manager
            and sender_identity_hash in ctx.forwarding_manager.forwarding_routers
        ):
            router = ctx.forwarding_manager.forwarding_routers[sender_identity_hash]

        # send lxmf message to be routed to destination
        router.handle_outbound(lxmf_message)

        # upsert lxmf message to database
        if not no_display:
            self.db_upsert_lxmf_message(
                lxmf_message,
                context=ctx,
                path_finding_measure=reticulum_pathfinding.format_outbound_path_finding_measure(
                    path_outcome,
                ),
                path_row_hash_hex=delivery_hash_bytes.hex()
                if path_outcome.path_available
                else None,
            )

        # tell all websocket clients that old failed message was deleted so it can remove from ui
        if not no_display:
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_created",
                        "lxmf_message": convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                            reticulum=self.reticulum,
                            message_router=ctx.message_router,
                        ),
                    },
                ),
            )

        # handle lxmf message progress loop without blocking or awaiting
        # otherwise other incoming websocket packets will not be processed until sending is complete
        # which results in the next message not showing up until the first message is finished
        if not no_display:
            AsyncUtils.run_async(
                self.handle_lxmf_message_progress(lxmf_message, context=ctx),
            )

        return lxmf_message

    async def send_reaction(
        self,
        destination_hash: str,
        target_message_hash: str,
        emoji: str,
        context=None,
    ) -> LXMF.LXMessage:
        ctx = context or self.current_context
        if not ctx:
            raise RuntimeError("No identity context available for sending reaction")
        return await self.send_message(
            destination_hash=destination_hash,
            content="",
            delivery_method="opportunistic",
            reaction_to_hash=target_message_hash,
            reaction_emoji=emoji,
            context=context,
        )

    # get hash of current icon appearance configuration
    def get_current_icon_hash(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return None

        name = ctx.config.lxmf_user_icon_name.get()
        fg = ctx.config.lxmf_user_icon_foreground_colour.get()
        bg = ctx.config.lxmf_user_icon_background_colour.get()

        if not all([name, fg, bg]):
            return None

        data = f"{name}|{fg}|{bg}"
        return hashlib.sha256(data.encode()).hexdigest()

    def process_incoming_telemetry(
        self,
        source_hash,
        telemetry_data,
        lxmf_message,
        timestamp_override=None,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        try:
            unpacked = Telemeter.from_packed(telemetry_data)
            if unpacked:
                timestamp = timestamp_override or (
                    unpacked["time"]["utc"] if "time" in unpacked else int(time.time())
                )

                # physical link info
                physical_link = {
                    "rssi": self.reticulum.get_packet_rssi(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                    "snr": self.reticulum.get_packet_snr(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                    "q": self.reticulum.get_packet_q(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                }

                ctx.database.telemetry.upsert_telemetry(
                    destination_hash=source_hash,
                    timestamp=timestamp,
                    data=telemetry_data,
                    received_from=ctx.local_lxmf_destination.hexhash,
                    physical_link=physical_link,
                )

                # broadcast telemetry update via websocket
                AsyncUtils.run_async(
                    self.websocket_broadcast(
                        json.dumps(
                            {
                                "type": "lxmf.telemetry",
                                "destination_hash": source_hash,
                                "timestamp": timestamp,
                                "telemetry": unpacked,
                                "physical_link": physical_link,
                                "is_tracking": ctx.database.telemetry.is_tracking(
                                    source_hash,
                                ),
                            },
                        ),
                    ),
                )
        except Exception as e:
            print(f"Error processing incoming telemetry: {e}")

    def _resolve_location_for_telemetry(self):
        location_source = self.config.location_source.get()
        if location_source == "disabled":
            return None, None
        if location_source == "manual":
            lat = self.config.location_manual_lat.get()
            lon = self.config.location_manual_lon.get()
        else:
            lat = self.database.config.get("map_default_lat")
            lon = self.database.config.get("map_default_lon")
        return lat, lon

    def handle_telemetry_request(self, to_addr_hash: str):
        lat, lon = self._resolve_location_for_telemetry()

        if lat is None or lon is None:
            print(
                f"Cannot respond to telemetry request from {to_addr_hash}: No location set",
            )
            return

        try:
            location = {
                "latitude": float(lat),
                "longitude": float(lon),
                "altitude": 0,
                "speed": 0,
                "bearing": 0,
                "accuracy": 0,
                "last_update": int(time.time()),
            }

            telemetry_data = Telemeter.pack(location=location)

            AsyncUtils.run_async(
                self.send_message(
                    destination_hash=to_addr_hash,
                    content="",
                    telemetry_data=telemetry_data,
                    delivery_method="opportunistic",
                    no_display=False,
                ),
            )
        except Exception as e:
            print(f"Failed to respond to telemetry request: {e}")

    # updates lxmf message in database and broadcasts to websocket until it's delivered, or it fails
    async def handle_lxmf_message_progress(self, lxmf_message, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        should_update_message = True
        while should_update_message:
            progress_pct = round(lxmf_message.progress * 100, 2)
            ctx.database.messages.update_lxmf_message_state(
                message_hash=lxmf_message.hash.hex(),
                state=convert_lxmf_state_to_string(lxmf_message),
                progress=progress_pct,
                delivery_attempts=lxmf_message.delivery_attempts,
                next_delivery_attempt_at=getattr(
                    lxmf_message,
                    "next_delivery_attempt",
                    None,
                ),
                method=convert_lxmf_method_to_string(lxmf_message),
            )
            self._maybe_store_path_at_send_for_lxmf(ctx, lxmf_message)

            msg_dict = convert_lxmf_message_to_dict(
                lxmf_message,
                include_attachments=False,
                reticulum=self.reticulum,
                message_router=ctx.message_router,
            )
            self._merge_stored_path_fields_from_db(
                ctx,
                lxmf_message.hash.hex(),
                msg_dict,
            )

            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": msg_dict,
                    },
                ),
            )

            # check if we should stop updating
            if is_lxmf_outbound_progress_terminal(lxmf_message):
                should_update_message = False
            else:
                await asyncio.sleep(1)

    def _note_announce_timestamp(self) -> None:
        now = time.time()
        self.announce_timestamps.append(now)
        self.announce_timestamps = prune_announce_timestamps(
            self.announce_timestamps,
            now=now,
        )

    def on_telephone_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
        context=None,
    ):
        """Handle lxst.telephony announces (synchronous Reticulum callback)."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            logger.debug(
                "Dropping telephone announce from blocked source: %s",
                identity_hash,
            )
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return

        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return

        logger.debug(
            "Received an announce from %s for [lxst.telephony]",
            RNS.prettyhexrep(destination_hash),
        )

        # track announce timestamp
        self._note_announce_timestamp()

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
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
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

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
        ctx = context or self.current_context
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
        if self.is_destination_blocked(identity_hash, context=ctx):
            logger.debug(
                "Dropping announce from blocked source: %s",
                identity_hash,
            )
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return

        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return

        logger.debug(
            "Received an announce from %s for [lxmf.delivery]",
            RNS.prettyhexrep(destination_hash),
        )

        # track announce timestamp
        self._note_announce_timestamp()

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
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
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
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
                    self.resend_failed_messages_for_destination(
                        destination_hash.hex(),
                        context=ctx,
                    ),
                )

    def on_lxmf_propagation_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
        context=None,
    ):
        """Handle lxmf.propagation announces (synchronous Reticulum callback)."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return

        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return

        logger.debug(
            "Received an announce from %s for [lxmf.propagation]",
            RNS.prettyhexrep(destination_hash),
        )

        # track announce timestamp
        self._note_announce_timestamp()

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
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
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

    # resends all messages that previously failed to send to the provided destination hash
    async def resend_failed_messages_for_destination(
        self,
        destination_hash: str,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        identity_key = ""
        try:
            if ctx.identity is not None and getattr(ctx.identity, "hash", None):
                identity_key = ctx.identity.hash.hex()
        except Exception:
            identity_key = destination_hash

        lock = self._auto_resend_coordinator.lock_for(identity_key, destination_hash)
        async with lock:
            lookup_hash = destination_hash
            try:
                resolved = self.get_lxmf_destination_hash_for_identity_hash(
                    destination_hash,
                )
                if isinstance(resolved, str) and resolved.strip():
                    lookup_hash = resolved.strip()
            except Exception:
                lookup_hash = destination_hash

            failed_messages = ctx.database.messages.get_failed_messages_for_destination(
                lookup_hash,
            )
            now = time.time()

            for failed_message in failed_messages:
                try:
                    message_hash = failed_message.get("hash")
                    if not message_hash:
                        continue

                    if should_skip_for_budget(
                        failed_message.get("fields"),
                        max_attempts=MAX_AUTO_RESEND_ATTEMPTS,
                    ):
                        continue

                    if ctx.database.messages.has_recent_outbound_with_content(
                        destination_hash,
                        failed_message.get("content"),
                        within_seconds=RECENT_SAME_CONTENT_SECONDS,
                        now=now,
                    ):
                        continue

                    fields = parse_fields_dict(failed_message.get("fields"))
                    allow_attachments = ctx.config.allow_auto_resending_failed_messages_with_attachments.get()
                    if not allow_attachments and fields_have_attachments(fields):
                        print(
                            "Not resending failed message with attachments, as setting is disabled",
                        )
                        continue

                    claimed = (
                        ctx.database.messages.try_claim_failed_message_for_auto_resend(
                            message_hash,
                            cooldown_until=cooldown_until(
                                now,
                                seconds=AUTO_RESEND_COOLDOWN_SECONDS,
                            ),
                            now=now,
                        )
                    )
                    if not claimed:
                        continue

                    # parse image field
                    image_field = None
                    if "image" in fields and isinstance(fields.get("image"), dict):
                        image_field = LxmfImageField(
                            fields["image"]["image_type"],
                            base64.b64decode(fields["image"]["image_bytes"]),
                        )

                    # parse audio field
                    audio_field = None
                    if "audio" in fields and isinstance(fields.get("audio"), dict):
                        audio_field = LxmfAudioField(
                            fields["audio"]["audio_mode"],
                            base64.b64decode(fields["audio"]["audio_bytes"]),
                        )

                    # parse file attachments field
                    file_attachments_field = None
                    if "file_attachments" in fields and isinstance(
                        fields.get("file_attachments"),
                        list,
                    ):
                        file_attachments = [
                            LxmfFileAttachment(
                                file_attachment["file_name"],
                                base64.b64decode(file_attachment["file_bytes"]),
                            )
                            for file_attachment in fields["file_attachments"]
                            if isinstance(file_attachment, dict)
                        ]
                        file_attachments_field = LxmfFileAttachmentsField(
                            file_attachments,
                        )

                    attempt = next_attempt_count(failed_message.get("fields"))
                    ctx.database.messages.set_message_fields_json(
                        message_hash,
                        fields_with_auto_resend_count(
                            failed_message.get("fields"),
                            attempt,
                        ),
                    )

                    # send new message with failed message content
                    new_message = await self.send_message(
                        failed_message["destination_hash"],
                        failed_message["content"],
                        image_field=image_field,
                        audio_field=audio_field,
                        file_attachments_field=file_attachments_field,
                        context=ctx,
                    )

                    # Only drop the old failed row after a replacement was queued.
                    if (
                        new_message is None
                        or getattr(new_message, "hash", None) is None
                    ):
                        continue

                    new_hash = new_message.hash.hex()
                    ctx.database.messages.set_auto_resend_count_on_message(
                        new_hash,
                        attempt,
                    )

                    ctx.database.messages.delete_lxmf_message_by_hash(message_hash)

                    # tell all websocket clients that old failed message was deleted so it can remove from ui
                    await self.websocket_broadcast(
                        json.dumps(
                            {
                                "type": "lxmf_message_deleted",
                                "hash": message_hash,
                            },
                        ),
                    )

                except Exception as e:
                    print("Error resending failed message: " + str(e))

    def on_rrc_hub_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
        context=None,
    ):
        """Handle Relay Chat rrc.hub announces for hub discovery."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return
        if ctx.config and not ctx.config.rrc_enabled.get():
            return

        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            logger.debug(
                "Dropping rrc.hub announce from blocked source: %s",
                identity_hash,
            )
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return

        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return

        logger.debug(
            "Received an announce from %s for [rrc.hub]",
            RNS.prettyhexrep(destination_hash),
        )

        self._note_announce_timestamp()

        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
        if not announce:
            return

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

    def on_nomadnet_node_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
        context=None,
    ):
        """Handle nomadnetwork.node announces (synchronous Reticulum callback)."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return

        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            logger.debug(
                "Dropping announce from blocked source: %s",
                identity_hash,
            )
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return

        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return

        logger.debug(
            "Received an announce from %s for [nomadnetwork.node]",
            RNS.prettyhexrep(destination_hash),
        )

        # track announce timestamp
        self._note_announce_timestamp()

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
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
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

        self.queue_crawler_task(
            destination_hash.hex(),
            self.config.nomad_default_page_path.get() or "/page/index.mu",
        )

    def on_map_data_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
        context=None,
    ):
        """Handle map-data-v1 announces (synchronous Reticulum callback)."""
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return
        if not announced_identity or not announced_identity.hash:
            return
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return
        if not ctx.announce_manager.is_storing_announce_for_aspect(aspect):
            return
        logger.debug(
            "Received an announce from %s for [map-data-v1]",
            RNS.prettyhexrep(destination_hash),
        )
        self._note_announce_timestamp()
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
        if not announce:
            return
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

    def _try_serve_local_page_node(
        self,
        destination_hash,
        page_path,
        request_data=None,
        link_id=None,
        remote_identity=None,
    ):
        """Serve a page from disk when the hash matches a local page node.

        Returns the page content string, or None.
        """
        from meshchatx.src.backend.page_node import _safe_mesh_file_basename

        for node in self.page_node_manager.nodes.values():
            if not node.running or not node.destination:
                continue
            if node.destination.hash == destination_hash:
                page_name = page_path.lstrip("/")
                page_name = page_name.removeprefix("page/")
                try:
                    page_name = _safe_mesh_file_basename(page_name)
                except ValueError:
                    return None
                raw = node.serve_page_content(
                    page_name,
                    data=request_data,
                    link_id=link_id,
                    remote_identity=remote_identity,
                )
                if raw is None:
                    return None
                return raw.decode("utf-8", errors="replace")
        return None

    def _try_serve_local_page_node_file(self, destination_hash, file_path):
        """Serve a file from disk when the hash matches a local page node.

        Returns (file_name, file_bytes), or None.
        """
        from meshchatx.src.backend.page_node import _safe_mesh_file_basename

        for node in self.page_node_manager.nodes.values():
            if not node.running or not node.destination:
                continue
            if node.destination.hash == destination_hash:
                file_name = file_path.lstrip("/")
                file_name = file_name.removeprefix("file/")
                try:
                    file_name = _safe_mesh_file_basename(file_name)
                except ValueError:
                    return None
                return node.read_hosted_file(file_name)
        return None

    def _register_local_page_node_announce(self, node):
        """Insert a synthetic announce for a local page node into the database.

        Ensures the node appears in the NomadNet announce list without RNS loopback.
        """
        ctx = self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return
        if not node.destination or not node.identity:
            return
        destination_hash = node.destination.hash
        aspect = "nomadnetwork.node"
        app_data = node.name.encode("utf-8")
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            node.identity,
            destination_hash,
            aspect,
            app_data,
            None,
            force_store=True,
        )
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
        if announce:
            AsyncUtils.run_async(
                self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "announce",
                            "announce": self.convert_db_announce_to_dict(announce),
                        },
                    ),
                ),
            )

    # queues a crawler task for the provided destination and path
    def queue_crawler_task(
        self,
        destination_hash: str,
        page_path: str,
        context=None,
        force: bool = False,
    ):
        ctx = context or self.current_context
        if not ctx:
            return
        crawler = getattr(ctx, "crawler_manager", None)
        if crawler and not force and not ctx.config.crawler_enabled.get():
            return
        if crawler:
            crawler.queue_if_allowed(
                destination_hash,
                page_path,
                depth=0,
                announced_recently=True,
                force=force,
            )
            return
        ctx.database.misc.upsert_crawl_task(destination_hash, page_path)

    # gets the custom display name a user has set for the provided destination hash
    def get_custom_destination_display_name(self, destination_hash: str):
        db_destination_display_name = self.database.announces.get_custom_display_name(
            destination_hash,
        )
        if db_destination_display_name is not None:
            return db_destination_display_name

        return None

    # get name to show for an lxmf conversation (from most recent announce app data)
    def get_lxmf_conversation_name(
        self,
        destination_hash,
        default_name: str | None = "Anonymous Peer",
    ):
        # Optimized to fetch only the needed announce
        lxmf_announce = self.database.announces.get_announce_by_hash(destination_hash)

        # if app data is available in database, it should be base64 encoded text that was announced
        # we will return the parsed lxmf display name as the conversation name
        if lxmf_announce is not None and lxmf_announce["app_data"] is not None:
            return parse_lxmf_display_name(
                app_data_base64=lxmf_announce["app_data"],
            )

        # announce did not have app data, so provide a fallback name
        return default_name

    # reads the lxmf display name from the provided base64 app data

    # returns true if the conversation has messages newer than the last read at timestamp
    def is_lxmf_conversation_unread(self, destination_hash):
        return self.database.messages.is_conversation_unread(destination_hash)

    # returns number of messages that failed to send in a conversation
    def lxmf_conversation_failed_messages_count(self, destination_hash: str):
        return self.database.messages.get_failed_messages_count(destination_hash)

    # find an interface by name
    @staticmethod
    def find_interface_by_name(name: str):
        for interface in RNS.Transport.interfaces:
            interface_name = str(interface)
            if name == interface_name:
                return interface

        return None


def _maybe_run_embedded_module():
    """Re-enter a bundled Python module from a frozen MeshChatX executable.

    Desktop builds set sys.executable to MeshChatX itself, so
    python -m … cannot be used to start tools like rnsh. Callers pass
    --meshchatx-run-module <dotted.name> followed by that module's argv.
    """
    marker = "--meshchatx-run-module"
    if len(sys.argv) < 3 or sys.argv[1] != marker:
        return False
    module_name = sys.argv[2]
    if not module_name or module_name.startswith("-"):
        print(
            f"error: {marker} requires a module name",
            file=sys.stderr,
        )
        raise SystemExit(2)
    sys.argv = [sys.argv[0], *sys.argv[3:]]
    runpy.run_module(module_name, run_name="__main__", alter_sys=True)
    return True


# class to manage config stored in database
def main():
    if _maybe_run_embedded_module():
        return

    # Windows: mirror Linux Landlock by supervising the real process in an
    # AppContainer when requested. Electron already enters via the launcher
    # module. Skip when already inside the container or when this process is
    # the launcher supervisor (MESHCHAT_APPCONTAINER_LAUNCHER=1).
    # One-shot CLI diagnostics and backup tools run in-process so CI and
    # operators are not blocked on CreateProcess into an AppContainer.
    _oneshot_cli_flags = (
        "--self-check",
        "--reset-password",
        "--backup-db",
        "--restore-db",
        "--restore-from-snapshot",
        "--list-backups",
        "--export-backup",
        "--help",
        "-h",
        "--version",
    )
    if (
        sys.platform == "win32"
        and appcontainer_requested()
        and not is_appcontainer_child()
        and os.environ.get("MESHCHAT_APPCONTAINER_LAUNCHER", "").strip()
        not in (
            "1",
            "true",
            "yes",
            "on",
        )
        and not any(flag in sys.argv for flag in _oneshot_cli_flags)
    ):
        from meshchatx.src.backend.appcontainer_launcher import run_launcher

        os.environ["MESHCHAT_APPCONTAINER_LAUNCHER"] = "1"
        raise SystemExit(run_launcher(sys.argv[1:]))

    # Initialize crash recovery system early to catch startup errors
    recovery = CrashRecovery()
    recovery.install()
    raise_nofile_soft_limit()
    install_rns_panic_containment()
    install_bounded_ratchet_persist()

    parser = argparse.ArgumentParser(description="ReticulumMeshChat")
    parser.add_argument(
        "--host",
        nargs="?",
        default=os.environ.get("MESHCHAT_HOST", "127.0.0.1"),
        type=str,
        help="The address the web server should listen on. Can also be set via MESHCHAT_HOST environment variable.",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default=int(os.environ.get("MESHCHAT_PORT", "8000")),
        type=int,
        help="The port the web server should listen on. Can also be set via MESHCHAT_PORT environment variable.",
    )
    # If we are running from a frozen application (AppImage, EXE, etc),
    # we should default to headless mode unless explicitly requested.
    is_frozen = getattr(sys, "frozen", False)
    default_headless = env_bool("MESHCHAT_HEADLESS", is_frozen)

    parser.add_argument(
        "--headless",
        action="store_true",
        default=default_headless,
        help="Web browser will not automatically launch when this flag is passed. Can also be set via MESHCHAT_HEADLESS environment variable.",
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_FILE"),
        help="Path to a Reticulum Identity file to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_FILE environment variable.",
    )
    parser.add_argument(
        "--identity-base64",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_BASE64"),
        help="A base64 encoded Reticulum Identity to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_BASE64 environment variable.",
    )
    parser.add_argument(
        "--identity-base32",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_BASE32"),
        help="A base32 encoded Reticulum Identity to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_BASE32 environment variable.",
    )
    parser.add_argument(
        "--generate-identity-file",
        type=str,
        help="Generates and saves a new Reticulum Identity to the provided file path and then exits.",
    )
    parser.add_argument(
        "--generate-identity-base64",
        action="store_true",
        help="Outputs a randomly generated Reticulum Identity as base64 and then exits.",
    )
    parser.add_argument(
        "--auto-recover",
        action="store_true",
        default=env_bool("MESHCHAT_AUTO_RECOVER", False),
        help="Attempt to automatically recover the SQLite database on startup before serving the app. Can also be set via MESHCHAT_AUTO_RECOVER environment variable.",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        default=env_bool("MESHCHAT_AUTH", False),
        help="Enable basic authentication for the web interface. Can also be set via MESHCHAT_AUTH environment variable.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=env_bool("MESHCHAT_DEMO_MODE", False),
        help="Public demo mode: read-only mesh and blocked API mutations. Can also be set via MESHCHAT_DEMO_MODE environment variable.",
    )
    parser.add_argument(
        "--no-https",
        action="store_true",
        default=env_bool("MESHCHAT_NO_HTTPS", False),
        help="Disable HTTPS and use HTTP instead. Can also be set via MESHCHAT_NO_HTTPS environment variable.",
    )
    parser.add_argument(
        "--ssl-cert",
        type=str,
        default=os.environ.get("MESHCHAT_SSL_CERT"),
        metavar="PATH",
        help="Path to PEM TLS certificate. Use with --ssl-key (or MESHCHAT_SSL_KEY). Overrides the default identity storage ssl/cert.pem.",
    )
    parser.add_argument(
        "--ssl-key",
        type=str,
        default=os.environ.get("MESHCHAT_SSL_KEY"),
        metavar="PATH",
        help="Path to PEM TLS private key. Use with --ssl-cert (or MESHCHAT_SSL_CERT). Overrides the default identity storage ssl/key.pem.",
    )
    parser.add_argument(
        "--no-crash-recovery",
        action="store_true",
        default=env_bool("MESHCHAT_NO_CRASH_RECOVERY", False),
        help="Disable the crash recovery and diagnostic system. Can also be set via MESHCHAT_NO_CRASH_RECOVERY environment variable.",
    )
    parser.add_argument(
        "--backup-db",
        type=str,
        help="Create a database backup zip at the given path and exit.",
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List automatic database backups in storage (JSON) and exit.",
    )
    parser.add_argument(
        "--export-backup",
        nargs="*",
        default=None,
        metavar="ARG",
        help=(
            "Export a backup and exit. One argument: write a new zip to PATH. "
            "Two arguments: copy backup NAME from storage to DEST."
        ),
    )
    parser.add_argument(
        "--restore-db",
        type=str,
        help="Restore the database from the given path (zip or db file) and exit.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.environ.get("MESHCHAT_DATA_DIR"),
        help=(
            "Portable data root: uses <dir>/storage and <dir>/.reticulum when "
            "--storage-dir and --reticulum-config-dir are not set. "
            "Can also be set via MESHCHAT_DATA_DIR."
        ),
    )
    parser.add_argument(
        "--reticulum-config-dir",
        type=str,
        default=os.environ.get("MESHCHAT_RETICULUM_CONFIG_DIR"),
        help="Path to a Reticulum config directory for the RNS stack to use (e.g: ~/.reticulum). Can also be set via MESHCHAT_RETICULUM_CONFIG_DIR environment variable.",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        default=os.environ.get("MESHCHAT_STORAGE_DIR"),
        help="Path to a directory for storing databases and config files (default: ./storage). Can also be set via MESHCHAT_STORAGE_DIR environment variable.",
    )
    parser.add_argument(
        "--public-dir",
        type=str,
        default=os.environ.get("MESHCHAT_PUBLIC_DIR"),
        help="Path to the directory containing the frontend static files (default: bundled public folder). Can also be set via MESHCHAT_PUBLIC_DIR environment variable.",
    )
    parser.add_argument(
        "--gitea-base-url",
        type=str,
        default=os.environ.get("MESHCHAT_GITEA_BASE_URL"),
        help="Base URL for Gitea instance. Can also be set via MESHCHAT_GITEA_BASE_URL environment variable.",
    )
    parser.add_argument(
        "--test-exception-message",
        type=str,
        help="Throws an exception. Used for testing the electron error dialog",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
    )  # allow unknown command line args
    parser.add_argument(
        "--emergency",
        action="store_true",
        help="Start in emergency mode (no database, LXMF and peer announces only). Can also be set via MESHCHAT_EMERGENCY environment variable.",
        default=env_bool("MESHCHAT_EMERGENCY", False),
    )

    parser.add_argument(
        "--rns-log-level",
        type=str,
        default=None,
        metavar="LEVEL",
        help=(
            "Reticulum (RNS) stack log level: none, critical, error, warning, notice, "
            "verbose, debug, extreme, or a numeric level. "
            "When set, overrides MESHCHAT_RNS_LOG_LEVEL."
        ),
    )

    parser.add_argument(
        "--restore-from-snapshot",
        type=str,
        help="Restore the database from a specific snapshot name or path on startup.",
        default=os.environ.get("MESHCHAT_RESTORE_SNAPSHOT"),
    )

    parser.add_argument(
        "--reset-password",
        action="store_true",
        default=env_bool("MESHCHAT_RESET_PASSWORD", False),
        help="Clear the stored password hash on startup so a new password can be set via the web UI. Can also be set via MESHCHAT_RESET_PASSWORD environment variable.",
    )

    parser.add_argument(
        "--memory-diag",
        action="store_true",
        default=env_bool("MESHCHAT_MEMORY_DIAG", False),
        help="Enable tracemalloc-based memory diagnostics. Can also be set via MESHCHAT_MEMORY_DIAG environment variable.",
    )

    parser.add_argument(
        "--disable-plugins",
        action="store_true",
        default=env_bool("MESHCHAT_DISABLE_PLUGINS", False),
        help="Disable the plugin system entirely. Can also be set via MESHCHAT_DISABLE_PLUGINS environment variable.",
    )

    parser.add_argument(
        "--self-check",
        action="store_true",
        default=env_bool("MESHCHAT_SELF_CHECK", False),
        help="Run system self-check diagnostics on startup and then exit with 0 if all checks pass, or 1 if any fail. Can also be set via MESHCHAT_SELF_CHECK environment variable.",
    )

    args = parser.parse_args()

    ssl_cert = (args.ssl_cert or "").strip() or None
    ssl_key = (args.ssl_key or "").strip() or None
    if bool(ssl_cert) != bool(ssl_key):
        parser.error(
            "Both --ssl-cert and --ssl-key (or MESHCHAT_SSL_CERT and MESHCHAT_SSL_KEY) must be set together.",
        )

    # Disable crash recovery if requested via flag
    if args.no_crash_recovery:
        recovery.disable()

    args.storage_dir, args.reticulum_config_dir = resolve_meshchat_data_roots(
        data_dir=args.data_dir,
        storage_dir=args.storage_dir,
        reticulum_config_dir=args.reticulum_config_dir,
    )

    planned_storage_dir = args.storage_dir
    if not planned_storage_dir:
        # On Android, prefer user-accessible external storage
        android_external = _get_android_external_files_dir()
        if android_external:
            planned_storage_dir = android_external
        else:
            planned_storage_dir = os.path.join("storage")
    effective_storage_dir, migration_context = resolve_startup_storage(
        planned_storage_dir,
    )
    args.storage_dir = effective_storage_dir
    recovery.update_paths(
        storage_dir=effective_storage_dir,
        reticulum_config_dir=args.reticulum_config_dir,
    )

    # check if we want to test exception messages
    if args.test_exception_message is not None:
        raise Exception(args.test_exception_message)

    # util to generate reticulum identity and save to file without using rnid
    if args.generate_identity_file is not None:
        # do not overwrite existing files, otherwise user could lose existing keys
        if os.path.exists(args.generate_identity_file):
            print(
                "DANGER: the provided identity file path already exists, not overwriting!",
            )
            return

        # generate a new identity and save to provided file path
        identity = RNS.Identity(create_keys=True)
        with open(args.generate_identity_file, "wb") as file:
            file.write(identity.get_private_key())

        print(
            f"A new Reticulum Identity has been saved to: {args.generate_identity_file}",
        )
        return

    # util to generate reticulum identity as base64 without using rnid
    if args.generate_identity_base64 is True:
        identity = RNS.Identity(create_keys=True)
        print(base64.b64encode(identity.get_private_key()).decode("utf-8"))
        return

    identity_file_path = None

    # use provided identity, or fallback to a random one
    if args.identity_file is not None:
        identity = RNS.Identity(create_keys=False)
        identity.load(args.identity_file)
        identity_file_path = args.identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from file {args.identity_file}.",
        )
    elif args.identity_base64 is not None or args.identity_base32 is not None:
        identity = RNS.Identity(create_keys=False)
        if args.identity_base64 is not None:
            identity.load_private_key(base64.b64decode(args.identity_base64))
        else:
            try:
                identity.load_private_key(
                    base64.b32decode(args.identity_base32, casefold=True),
                )
            except Exception as exc:
                msg = f"Invalid base32 identity: {exc}"
                raise ValueError(msg) from exc
        base_storage_dir = args.storage_dir or os.path.join("storage")
        os.makedirs(base_storage_dir, exist_ok=True)
        default_identity_file = os.path.join(base_storage_dir, "identity")
        if not os.path.exists(default_identity_file):
            with open(default_identity_file, "wb") as file:
                file.write(identity.get_private_key())
        identity_file_path = default_identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from provided key.",
        )
    else:
        # ensure provided storage dir exists, or the default storage dir exists
        base_storage_dir = args.storage_dir or os.path.join("storage")
        os.makedirs(base_storage_dir, exist_ok=True)

        # configure path to default identity file
        default_identity_file = os.path.join(base_storage_dir, "identity")

        # if default identity file does not exist, generate a new identity and save it
        if not os.path.exists(default_identity_file):
            identity = RNS.Identity(create_keys=True)
            with open(default_identity_file, "wb") as file:
                file.write(identity.get_private_key())
            print(
                f"Reticulum Identity <{identity.hash.hex()}> has been randomly generated and saved to {default_identity_file}.",
            )

        # default identity file exists, load it
        identity = RNS.Identity(create_keys=False)
        identity.load(default_identity_file)
        identity_file_path = default_identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from file {default_identity_file}.",
        )

    # init app (allow optional one-shot backup/restore before running)
    rns_log_cli = (args.rns_log_level or "").strip() or None

    mem_check = evaluate_startup_memory(args.emergency)
    print(format_memory_log_line(mem_check), flush=True)
    if mem_check.get("message"):
        print(mem_check["message"], flush=True)
    if mem_check["action"] == "abort":
        print(
            "Startup aborted due to critically low memory. "
            "Free RAM or relaunch with --emergency.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    needs_immediate_network = bool(
        args.self_check
        or args.reset_password
        or args.backup_db
        or args.list_backups
        or args.export_backup is not None
        or args.restore_db
        or args.restore_from_snapshot,
    )
    if auth_bypass_from_env():
        print(
            "WARNING: MESHCHAT_AUTH_BYPASS=1 disables web UI authentication",
            file=sys.stderr,
            flush=True,
        )

    demo_mode = bool(args.demo)
    altcha_on = altcha_enabled_from_env()

    reticulum_meshchat = ReticulumMeshChat(
        identity,
        args.storage_dir,
        args.reticulum_config_dir,
        auto_recover=args.auto_recover,
        identity_file_path=identity_file_path,
        auth_enabled=args.auth,
        public_dir=args.public_dir,
        emergency=args.emergency,
        gitea_base_url=args.gitea_base_url,
        ssl_cert_path=ssl_cert,
        ssl_key_path=ssl_key,
        rns_loglevel=rns_log_cli,
        migration_context=migration_context,
        memory_diag_enabled=args.memory_diag,
        plugins_enabled=(not args.disable_plugins) and not demo_mode,
        defer_network_setup=not needs_immediate_network,
        headless=bool(args.headless),
        demo_mode=demo_mode,
        altcha_enabled=altcha_on,
    )

    # store recovery on app for wiring with identity context
    reticulum_meshchat._crash_recovery = recovery
    recovery.app = reticulum_meshchat

    # update recovery with known paths (database_path may be unset until identity setup)
    recovery.update_paths(
        storage_dir=reticulum_meshchat.storage_dir,
        database_path=reticulum_meshchat.database_path,
        public_dir=reticulum_meshchat.public_dir_override or get_file_path("public"),
        reticulum_config_dir=reticulum_meshchat.reticulum_config_dir,
    )

    if args.self_check:
        results = reticulum_meshchat.run_self_test()
        print("\n================================", flush=True)
        print("   System Self-Check Results", flush=True)
        print("================================", flush=True)

        all_passed = True
        from meshchatx.src.backend.self_check import SELF_CHECK_LABELS

        for key, name in SELF_CHECK_LABELS.items():
            check = results.get(key, {"status": "failed", "reason": "No result"})
            if check["status"] == "ok":
                print(f"[OK]     {name}", flush=True)
            else:
                all_passed = False
                reason = check.get("reason") or "Unknown error"
                print(f"[FAILED] {name} - Reason: {reason}", flush=True)

        print("================================", flush=True)
        if all_passed:
            print("Status: SUCCESS (All checks passed)", flush=True)
            print("================================\n", flush=True)
            sys.exit(0)
        else:
            print("Status: FAILED", flush=True)
            print("================================\n", flush=True)
            sys.exit(1)

    if args.reset_password:
        if reticulum_meshchat.reset_password():
            print("Password has been reset. Set a new password via the web UI.")
        else:
            print("No password was set; nothing to reset.")

    if args.backup_db:
        result = reticulum_meshchat.backup_database(args.backup_db)
        print(f"Backup written to {result['path']} ({result['size']} bytes)")
        return

    if args.list_backups:
        backups = reticulum_meshchat.list_database_backups()
        print(json.dumps({"backups": backups, "total": len(backups)}, indent=2))
        return

    if args.export_backup is not None:
        parts = args.export_backup
        if len(parts) == 1:
            result = reticulum_meshchat.backup_database(parts[0])
            print(f"Backup written to {result['path']} ({result['size']} bytes)")
        elif len(parts) == 2:
            result = reticulum_meshchat.export_database_backup(parts[0], parts[1])
            print(
                f"Exported {result['name']} to {result['path']} ({result['size']} bytes)",
            )
        else:
            print(
                "Usage: --export-backup PATH | --export-backup NAME DEST",
                file=sys.stderr,
            )
            sys.exit(2)
        return

    if args.restore_db:
        result = reticulum_meshchat.restore_database(args.restore_db)
        print(f"Restored database from {args.restore_db}")
        print(f"Integrity check: {result['integrity_check']}")
        return

    if args.restore_from_snapshot:
        snapshot_path = args.restore_from_snapshot
        if not os.path.exists(snapshot_path):
            # Try in identity storage snapshots
            potential_path = os.path.join(
                reticulum_meshchat.storage_path,
                "snapshots",
                snapshot_path,
            )
            if os.path.exists(potential_path):
                snapshot_path = potential_path
            elif os.path.exists(potential_path + ".zip"):
                snapshot_path = potential_path + ".zip"

        if os.path.exists(snapshot_path):
            print(f"Restoring database from snapshot: {snapshot_path}")
            result = reticulum_meshchat.restore_database(snapshot_path)
            print(
                f"Snapshot restoration complete. Integrity check: {result['integrity_check']}",
            )
            reticulum_meshchat.setup_identity(identity)
            reticulum_meshchat._mark_network_ready()
            reticulum_meshchat._finish_deferred_startup_services()
        else:
            print(f"Error: Snapshot not found at {snapshot_path}")

    enable_https = not args.no_https
    reticulum_meshchat.appcontainer_active = is_appcontainer_child()
    if reticulum_meshchat.appcontainer_active:
        apply_windows_process_mitigations()
    reticulum_meshchat.landlock_active = apply_landlock_sandbox(
        storage_dir=reticulum_meshchat.storage_dir,
        reticulum_config_dir=reticulum_meshchat.reticulum_config_dir,
        public_dir=reticulum_meshchat.public_dir_override or get_file_path("public"),
        log_dir=resolve_log_dir(),
        extra_read_roots=extra_read_roots_from_app(reticulum_meshchat),
        extra_rw_roots=collect_external_filesync_rw_roots(
            reticulum_meshchat.storage_dir,
        ),
    )
    # Apply after Landlock so landlock_* syscalls are not blocked by the filter.
    reticulum_meshchat.seccomp_active = apply_seccomp_sandbox()
    reticulum_meshchat.run(
        args.host,
        args.port,
        launch_browser=args.headless is False,
        enable_https=enable_https,
    )


if __name__ == "__main__":
    main()
