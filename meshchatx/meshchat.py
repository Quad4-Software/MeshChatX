#!/usr/bin/env python
# SPDX-License-Identifier: 0BSD

import argparse
import asyncio
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
import math
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
from datetime import UTC, datetime
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
    AutoResendCoordinator,
)
from meshchatx.src.backend.cli_identity import resolve_startup_identity
from meshchatx.src.backend.constants import API_V1_PREFIX
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
from meshchatx.src.backend.host_interfaces import list_host_network_interfaces
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
    landlock_abi_version,
    landlock_auto_enabled,
    landlock_disabled_by_env,
    landlock_kernel_supported,
    landlock_requested,
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
    compute_lxmf_conversation_unread_from_latest_row,
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
    convert_lxmf_method_to_string,
    convert_lxmf_state_to_string,
    is_lxmf_outbound_progress_terminal,
    is_user_facing_lxmf_payload,
    lxmf_sidebar_preview_for_conversation_latest_row,
)
from meshchatx.src.backend.map_geo_validator import GeoValidationError
from meshchatx.src.backend.map_manager import (
    MAX_EXPORT_TILES,
    TRANSPARENT_TILE,
    is_mbtiles_filename,
)
from meshchatx.src.backend.map_overlay_export import OverlayExportError
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
    hex_identifier_to_bytes,
    interval_action_due,
    message_fields_have_attachments,
    normalize_hex_identifier,
    normalize_identity_storage_hash,
    parse_bool_query_param,
    parse_lxmf_display_name,
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
from meshchatx.src.backend.persistent_log_handler import memory_log_handler
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
from meshchatx.src.backend.rns_filesync_handler import (
    collect_external_filesync_rw_roots,
)
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
from meshchatx.src.backend.telemetry_utils import Telemeter
from meshchatx.src.backend.web_audio_bridge import WebAudioBridge
from meshchatx.src.backend.websocket_config_guard import (
    sanitize_websocket_config_update,
    websocket_type_requires_auth,
)
from meshchatx.src.env_config import MeshchatEnv
from meshchatx.src.env_utils import env_bool, env_str
from meshchatx.src.path_utils import (
    get_file_path,
    is_loopback_bind_host,
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

from meshchatx.meshchat_shared import _create_reticulum_instance, _install_reticulum_signal_handlers, _parse_rns_loglevel_value, _resolve_rns_logdest, _resolve_rns_loglevel, _restore_rns_console_logging_after_reticulum_init, _rns_bridge_logger, _rns_log_to_python_logging, log_dir, logger
from meshchatx.meshchat_parts.probe import ProbeMixin
from meshchatx.meshchat_parts.on import OnMixin
from meshchatx.meshchat_parts.get import GetMixin
from meshchatx.meshchat_parts.mark import MarkMixin
from meshchatx.meshchat_parts.check import CheckMixin
from meshchatx.meshchat_parts.disable import DisableMixin
from meshchatx.meshchat_parts.schedule import ScheduleMixin
from meshchatx.meshchat_parts.force import ForceMixin
from meshchatx.meshchat_parts.get_2 import Get2Mixin
from meshchatx.meshchat_parts.apply import ApplyMixin
from meshchatx.meshchat_parts.process import ProcessMixin
from meshchatx.meshchat_parts.get_3 import Get3Mixin
from meshchatx.meshchat_parts.parse import ParseMixin
from meshchatx.meshchat_parts.build import BuildMixin
from meshchatx.meshchat_parts.on_2 import On2Mixin
from meshchatx.meshchat_parts.on_3 import On3Mixin
from meshchatx.meshchat_parts.exit import ExitMixin
from meshchatx.meshchat_parts.define import DefineMixin
from meshchatx.meshchat_parts.coerce import CoerceMixin
from meshchatx.meshchat_parts.flush import FlushMixin
from meshchatx.meshchat_parts.handle import HandleMixin
from meshchatx.meshchat_parts.on_4 import On4Mixin
from meshchatx.meshchat_parts.on_5 import On5Mixin
from meshchatx.meshchat_parts.convert import ConvertMixin
from meshchatx.meshchat_parts.peer import PeerMixin
from meshchatx.meshchat_parts.lxmf import LxmfMixin
from meshchatx.meshchat_parts.lxmf_2 import Lxmf2Mixin
from meshchatx.meshchat_parts.apply_2 import Apply2Mixin
from meshchatx.meshchat_parts.try_kw import TryKwMixin


def _truncated_hash32_hex_ok(value: str | None) -> bool:
    """32 lowercase hex chars (Reticulum truncated hash) without relying on live RNS constants."""
    return bool(normalize_identity_storage_hash(value))


# Global log handler (singleton lives in persistent_log_handler)
handlers = [memory_log_handler]

if log_dir:
    file_handler = SafeRotatingFileHandler(
        os.path.join(log_dir, "meshchatx.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handlers.append(file_handler)

# Always tee to stdout when one exists. Containers log to /config/logs only,
# which hides aiohttp.server request-handler tracebacks from docker logs and
# kubectl logs. Frozen GUI builds may have no console stream; skip then.
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(level=logging.INFO, handlers=handlers)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


















def _csrf_exempt_path(path: str) -> bool:
    return path == f"{API_V1_PREFIX}/auth/csrf"


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
    NomadnetPageDownloader,
    list_host_network_interfaces,
    LxmfFileAttachment,
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


class ReticulumMeshChat(ProbeMixin, OnMixin, GetMixin, MarkMixin, CheckMixin, DisableMixin, ScheduleMixin, ForceMixin, Get2Mixin, ApplyMixin, ProcessMixin, Get3Mixin, ParseMixin, BuildMixin, On2Mixin, On3Mixin, ExitMixin, DefineMixin, CoerceMixin, FlushMixin, HandleMixin, On4Mixin, On5Mixin, ConvertMixin, PeerMixin, LxmfMixin, Lxmf2Mixin, Apply2Mixin, TryKwMixin):
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
    ):
        self.running = True
        self.plugins_enabled = plugins_enabled
        self.demo_mode = bool(demo_mode)
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
        skip_storage_lock = env_bool("MESHCHAT_SKIP_STORAGE_LOCK")
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
        from meshchatx.src.backend.webtransport_sidecar import WebTransportSidecarState

        self.webtransport_state = WebTransportSidecarState()
        self._identity_hotswap_lock = asyncio.Lock()
        # Serializes reload_reticulum: concurrent admin requests would
        # otherwise interleave teardown and rebuild of the RNS stack.
        self._reticulum_reload_lock = asyncio.Lock()
        self.listen_host: str | None = None
        self.listen_port: int | None = None
        self.use_https: bool = True
        self.landlock_active: bool = False
        self.appcontainer_active: bool = False
        self.seccomp_active: bool = False
        self._pending_identity = identity
        self._restore_lock = threading.Lock()
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
        # on_lxmf_delivery runs on RNS threads and the cooldown loop on the
        # event loop, so every mutation of this state goes through the lock.
        self._lxmf_incoming_timestamps = []
        self._lxmf_flood_lock = threading.RLock()
        self._flood_protection_current_cost = None
        self._flood_protection_last_bump_time = 0

        # track download speeds for nomadnetwork files
        self.download_speeds = []

        # track active downloads
        self.active_downloads = {}
        self.download_id_counter = 0
        self.download_id_lock = asyncio.Lock()

        # page -> file grants for local anti-deep-linking
        self._page_file_grants: dict[int, dict] = {}

        self.identity_manager = IdentityManager(self.storage_dir, identity_file_path)
        from meshchatx.src.backend.translation_pack_manager import (
            TranslationPackManager,
        )

        self.translation_pack_manager = TranslationPackManager(self.storage_dir)
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
        # Keep strong refs to fire-and-forget propagation request tasks so the
        # event loop cannot garbage-collect them mid-flight.
        self._propagation_node_request_tasks: set[asyncio.Task] = set()
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
        if env_bool("MESHCHAT_FORCE_WEB_AUDIO"):
            return True
        cached = getattr(self, "_host_audio_unavailable_cached", None)
        if cached is not None:
            return cached
        unavailable = self._probe_host_audio_unavailable()
        self._host_audio_unavailable_cached = unavailable
        return unavailable
























































































    def _rebaseline_integrity_after_restore(self, db_path, restored_identity_hash):
        """Re-baseline file integrity over the restored identity dir.

        The backup's signed manifest is install-local state and is excluded
        from restore, so the manifest on disk still describes the pre-restore
        tree. Without a fresh baseline the next boot flags every restored
        file. Restore is an explicit user action, so blessing the restored
        state here matches the acknowledge flow.
        """
        try:
            from meshchatx.src.backend.integrity_manager import IntegrityManager

            identity_dir = os.path.dirname(db_path)
            identity_hash = restored_identity_hash
            if identity_hash is None:
                current = getattr(self, "identity", None)
                if current is not None:
                    identity_hash = current.hash.hex()
            app_version = None
            with contextlib.suppress(Exception):
                version = self.get_app_version()
                if isinstance(version, str):
                    app_version = version
            manager = IntegrityManager(
                identity_dir,
                db_path,
                identity_hash=identity_hash,
                trust_dir=os.path.join(self.storage_dir, "integrity"),
                app_version=app_version,
            )
            if identity_hash is None:
                # Without an identity to bind to, a saved manifest would only
                # raise a mismatch next boot. Drop the stale baseline so the
                # next run rebuilds it.
                manager.clear_baseline()
            else:
                manager.save_manifest(reason="acknowledge")
        except Exception as exc:
            print(f"Failed to refresh integrity baseline after restore: {exc}")





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
        if not os.path.isfile(config_path):
            if not os.path.isdir(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            self._write_rns_reticulum_default_config_file(config_path)
        else:
            # Try to load the existing file. If it is readable, preserve the
            # user content and only add missing top-level sections. If it is
            # not readable, fall through to the backup-and-default repair path.
            from RNS.vendor.configobj import ConfigObj

            try:
                cfg = ConfigObj(config_path)
            except Exception:
                repair_unparseable_reticulum_config(
                    config_path,
                    write_default=self._write_rns_reticulum_default_config_file,
                )
                if not reticulum_config_has_required_sections(config_path):
                    self._write_rns_reticulum_default_config_file(config_path)
            else:
                changed = False
                for section in ("reticulum", "interfaces"):
                    if section not in cfg:
                        cfg[section] = {}
                        changed = True
                if changed:
                    try:
                        cfg.write()
                    except Exception as exc:
                        logger.warning(
                            "Failed to ensure required sections in %s: %s",
                            config_path,
                            exc,
                        )
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
            normalize_rnode_bluetooth_in_config,
            normalize_rnode_tcp_host_in_config,
        )

        normalize_rnode_tcp_host_in_config(config_path)
        normalize_rnode_bluetooth_in_config(config_path)
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






    def _webtransport_status_dict(self) -> dict:
        state = getattr(self, "webtransport_state", None)
        if state is None:
            from meshchatx.src.backend.webtransport_sidecar import (
                WebTransportSidecarState,
            )

            state = WebTransportSidecarState()
            self.webtransport_state = state
        return state.status_dict()



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






    _reload_instance_suffix_re = re.compile(r"-reload-(\d+)-(\d+)$")
    _meshchat_reload_pid_max = 4_194_304
    _meshchat_reload_epoch_min = 1_577_836_800
    _meshchat_reload_epoch_max = 4_102_444_800


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
                # Teardown waits on setup events and sleeps; run it on a
                # worker thread so the web loop is not frozen.
                await asyncio.to_thread(self.teardown_identity)
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
            "is_shared_instance": bool(
                reticulum is not None
                and getattr(reticulum, "is_shared_instance", False),
            ),
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
        propagation_task = asyncio.create_task(
            self._request_propagation_node_messages(context=ctx)
        )
        tasks = getattr(self, "_propagation_node_request_tasks", None)
        if tasks is None:
            tasks = self._propagation_node_request_tasks = set()
        tasks.add(propagation_task)
        propagation_task.add_done_callback(tasks.discard)

        await self.send_config_to_websocket_clients(context=ctx)
        return True


























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











    # convert an lxmf message to a dictionary, for sending over websocket



    def build_pending_announce_dict(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ):
        """Slim announce payload for background-ingested peers.

        Matches convert_db_announce_to_dict's output for strangers without
        any SQLite lookups: unknown peers have no contact, custom name, or
        icon by definition, so those fields are always empty here.
        """
        from meshchatx.src.backend.announce_manager import (
            MAX_ANNOUNCE_APP_DATA_BYTES,
        )

        dh_hex = (
            destination_hash.hex()
            if isinstance(destination_hash, (bytes, bytearray, memoryview))
            else destination_hash
        )
        identity_hash = None
        identity_public_key = None
        if announced_identity is not None and getattr(
            announced_identity,
            "hash",
            None,
        ):
            identity_hash = announced_identity.hash.hex()
            try:
                identity_public_key = base64.b64encode(
                    announced_identity.get_public_key(),
                ).decode("utf-8")
            except Exception:
                identity_public_key = None

        app_data_b64 = None
        if (
            app_data is not None
            and isinstance(
                app_data,
                (bytes, bytearray, memoryview),
            )
            and len(app_data) <= MAX_ANNOUNCE_APP_DATA_BYTES
        ):
            app_data_b64 = base64.b64encode(bytes(app_data)).decode("utf-8")

        display_name = None
        if aspect in ("lxmf.delivery", "lxst.telephony"):
            display_name = parse_lxmf_display_name(app_data_b64)
        elif aspect == "nomadnetwork.node":
            display_name = parse_nomadnetwork_node_display_name(app_data_b64)
        elif aspect == "rrc.hub":
            display_name = rrc_protocol.display_name_from_hub_app_data(app_data_b64)

        rssi = snr = quality = None
        if announce_packet_hash and getattr(self, "reticulum", None):
            rssi = self.reticulum.get_packet_rssi(announce_packet_hash)
            snr = self.reticulum.get_packet_snr(announce_packet_hash)
            quality = self.reticulum.get_packet_q(announce_packet_hash)

        hops = None
        try:
            hops = RNS.Transport.hops_to(bytes.fromhex(dh_hex))
        except Exception:
            pass

        now = datetime.now(UTC).isoformat()
        return {
            "id": None,
            "destination_hash": dh_hex,
            "aspect": aspect,
            "identity_hash": identity_hash,
            "identity_public_key": identity_public_key,
            "app_data": app_data_b64,
            "hops": hops,
            "rssi": rssi,
            "snr": snr,
            "quality": quality,
            "display_name": display_name,
            "lxmf_destination_hash": None,
            "custom_display_name": None,
            "lxmf_user_icon": None,
            "created_at": now,
            "updated_at": now,
        }



































































    # reads the lxmf display name from the provided base64 app data





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


# Process entrypoint for MeshChatX (CLI, identity resolve, then web server).
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
        and (env_str("MESHCHAT_APPCONTAINER_LAUNCHER") or "").strip()
        not in (
            "1",
            "true",
            "yes",
            "on",
        )
        and not any(flag in sys.argv for flag in _oneshot_cli_flags)
    ):
        from meshchatx.src.backend.appcontainer_launcher import run_launcher

        os.environ.update({"MESHCHAT_APPCONTAINER_LAUNCHER": "1"})
        raise SystemExit(run_launcher(sys.argv[1:]))

    # Initialize crash recovery system early to catch startup errors
    recovery = CrashRecovery()
    recovery.install()
    raise_nofile_soft_limit()
    install_rns_panic_containment()
    install_bounded_ratchet_persist()

    env = MeshchatEnv.load()

    parser = argparse.ArgumentParser(description="MeshChatX")
    parser.add_argument(
        "--host",
        nargs="?",
        default=env.host,
        type=str,
        help="The address the web server should listen on. Can also be set via MESHCHAT_HOST environment variable.",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default=env.port,
        type=int,
        help="The port the web server should listen on. Can also be set via MESHCHAT_PORT environment variable.",
    )
    # If we are running from a frozen application (AppImage, EXE, etc),
    # we should default to headless mode unless explicitly requested.
    is_frozen = getattr(sys, "frozen", False)
    # env_bool keeps MESHCHAT_HEADLESS=0 able to override the frozen default.
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
        default=env.identity_file,
        help="Path to a Reticulum Identity file to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_FILE environment variable.",
    )
    parser.add_argument(
        "--identity-base64",
        type=str,
        default=env.identity_base64,
        help="A base64 encoded Reticulum Identity to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_BASE64 environment variable.",
    )
    parser.add_argument(
        "--identity-base32",
        type=str,
        default=env.identity_base32,
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
        default=env.auto_recover,
        help="Attempt to automatically recover the SQLite database on startup before serving the app. Can also be set via MESHCHAT_AUTO_RECOVER environment variable.",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        default=env.auth,
        help="Enable basic authentication for the web interface. Can also be set via MESHCHAT_AUTH environment variable.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=env.demo_mode,
        help="Public demo mode: read-only mesh and blocked API mutations. Can also be set via MESHCHAT_DEMO_MODE environment variable.",
    )
    parser.add_argument(
        "--no-https",
        action="store_true",
        default=env.no_https,
        help="Disable HTTPS and use HTTP instead. Can also be set via MESHCHAT_NO_HTTPS environment variable.",
    )
    parser.add_argument(
        "--ssl-cert",
        type=str,
        default=env.ssl_cert,
        metavar="PATH",
        help="Path to PEM TLS certificate. Use with --ssl-key (or MESHCHAT_SSL_KEY). Overrides the default identity storage ssl/cert.pem.",
    )
    parser.add_argument(
        "--ssl-key",
        type=str,
        default=env.ssl_key,
        metavar="PATH",
        help="Path to PEM TLS private key. Use with --ssl-cert (or MESHCHAT_SSL_CERT). Overrides the default identity storage ssl/key.pem.",
    )
    parser.add_argument(
        "--no-crash-recovery",
        action="store_true",
        default=env.no_crash_recovery,
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
        default=env.data_dir,
        help=(
            "Portable data root: uses <dir>/storage and <dir>/.reticulum when "
            "--storage-dir and --reticulum-config-dir are not set. "
            "Can also be set via MESHCHAT_DATA_DIR."
        ),
    )
    parser.add_argument(
        "--reticulum-config-dir",
        type=str,
        default=env.reticulum_config_dir,
        help="Path to a Reticulum config directory for the RNS stack to use (e.g: ~/.reticulum). Can also be set via MESHCHAT_RETICULUM_CONFIG_DIR environment variable.",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        default=env.storage_dir,
        help="Path to a directory for storing databases and config files (default: ./storage). Can also be set via MESHCHAT_STORAGE_DIR environment variable.",
    )
    parser.add_argument(
        "--public-dir",
        type=str,
        default=env.public_dir,
        help="Path to the directory containing the frontend static files (default: bundled public folder). Can also be set via MESHCHAT_PUBLIC_DIR environment variable.",
    )
    parser.add_argument(
        "--gitea-base-url",
        type=str,
        default=env.gitea_base_url,
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
        default=env.emergency,
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
        default=env.restore_snapshot,
    )

    parser.add_argument(
        "--reset-password",
        action="store_true",
        default=env.reset_password,
        help="Clear the stored password hash on startup so a new password can be set via the web UI. Can also be set via MESHCHAT_RESET_PASSWORD environment variable.",
    )

    parser.add_argument(
        "--memory-diag",
        action="store_true",
        default=env.memory_diag,
        help="Enable tracemalloc-based memory diagnostics. Can also be set via MESHCHAT_MEMORY_DIAG environment variable.",
    )

    parser.add_argument(
        "--disable-plugins",
        action="store_true",
        default=env.disable_plugins,
        help="Disable the plugin system entirely. Can also be set via MESHCHAT_DISABLE_PLUGINS environment variable.",
    )

    parser.add_argument(
        "--self-check",
        action="store_true",
        default=env.self_check,
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

    identity, identity_file_path = resolve_startup_identity(args)
    if identity is None:
        return

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
            elif check["status"] == "skipped":
                reason = check.get("reason") or "unavailable"
                print(f"[SKIP]   {name} - Reason: {reason}", flush=True)
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
    landlock_extra_read_roots = extra_read_roots_from_app(reticulum_meshchat)
    # Custom TLS cert/key may live outside the standard roots (for example a
    # mounted Kubernetes Secret at /tls). Grant read access to their parent
    # directories so the sandboxed process can load them in run().
    for tls_path in (
        reticulum_meshchat.ssl_cert_path,
        reticulum_meshchat.ssl_key_path,
    ):
        if tls_path:
            tls_dir = os.path.dirname(os.path.abspath(str(tls_path)))
            if tls_dir and tls_dir not in landlock_extra_read_roots:
                landlock_extra_read_roots.append(tls_dir)
    reticulum_meshchat.landlock_active = apply_landlock_sandbox(
        storage_dir=reticulum_meshchat.storage_dir,
        reticulum_config_dir=reticulum_meshchat.reticulum_config_dir,
        public_dir=reticulum_meshchat.public_dir_override or get_file_path("public"),
        log_dir=resolve_log_dir(),
        extra_read_roots=landlock_extra_read_roots,
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


# Methods extracted to the mixin classes are rebound so this module stays
# their global namespace: patch("meshchatx.meshchat.<name>") targets still reach
# moved code, which would otherwise resolve names in its part module.
# Helpers in the shared module get the same treatment. __globals__ is
# read-only on functions, so each is rebuilt via types.FunctionType and
# assigned back onto its mixin.
def _rebind_moved_globals_to_this_module():
    import sys as _sys
    import types as _types

    this_globals = globals()
    mixin_mod_prefix = "meshchatx.meshchat_parts."

    def rebuild(fn):
        if not hasattr(fn, "__code__"):
            return fn
        new_fn = _types.FunctionType(
            fn.__code__, this_globals, fn.__name__, fn.__defaults__, fn.__closure__
        )
        new_fn.__kwdefaults__ = fn.__kwdefaults__
        new_fn.__dict__.update(fn.__dict__)
        new_fn.__module__ = fn.__module__
        new_fn.__qualname__ = fn.__qualname__
        new_fn.__doc__ = fn.__doc__
        new_fn.__annotations__ = getattr(fn, "__annotations__", {})
        new_fn.__type_params__ = getattr(fn, "__type_params__", ())
        return new_fn

    for mixin in ReticulumMeshChat.__mro__[1:-1]:
        if not mixin.__module__.startswith(mixin_mod_prefix):
            continue
        for name, member in list(vars(mixin).items()):
            if isinstance(member, staticmethod):
                setattr(mixin, name, staticmethod(rebuild(member.__func__)))
            elif isinstance(member, classmethod):
                setattr(mixin, name, classmethod(rebuild(member.__func__)))
            elif isinstance(member, property):
                setattr(
                    mixin,
                    name,
                    property(
                        rebuild(member.fget) if member.fget else None,
                        rebuild(member.fset) if member.fset else None,
                        rebuild(member.fdel) if member.fdel else None,
                        member.__doc__,
                    ),
                )
            elif hasattr(member, "__code__") and getattr(
                member, "__module__", None
            ) == mixin.__module__:
                setattr(mixin, name, rebuild(member))
    shared_mod = _sys.modules.get("meshchatx.meshchat_shared")
    if shared_mod is not None:
        for name, fn in list(vars(shared_mod).items()):
            if getattr(fn, "__module__", None) == "meshchatx.meshchat_shared" and hasattr(
                fn, "__code__"
            ):
                new_fn = rebuild(fn)
                setattr(shared_mod, name, new_fn)
                # The from-import above bound the pre-rebind object into this
                # module, so rebind this module's name to the rebuilt function
                # or patch targets here would not reach moved code.
                if name in this_globals:
                    this_globals[name] = new_fn


_rebind_moved_globals_to_this_module()
del _rebind_moved_globals_to_this_module
