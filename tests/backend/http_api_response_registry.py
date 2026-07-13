# SPDX-License-Identifier: 0BSD

"""Registry of HTTP JSON response contracts for GET /api/v1 routes."""

from __future__ import annotations

import re

from tests.backend.api_json_contract_schemas import (
    API_V1_APP_INFO_ENVELOPE_SCHEMA,
    API_V1_STATUS_SCHEMA,
    SELF_TEST_SCHEMA,
    AUTH_STATUS_SCHEMA,
    TELEPHONE_CONTACT_CHECK_SCHEMA,
    TELEPHONE_CONTACTS_LIST_SCHEMA,
    TELEPHONE_RINGTONE_STATUS_SCHEMA,
    TELEPHONE_RINGTONES_LIST_SCHEMA,
    TELEPHONE_VOICEMAIL_STATUS_SCHEMA,
    TELEPHONE_VOICEMAILS_ENVELOPE_SCHEMA,
)
from tests.backend.http_api_contract_runtime import HttpJsonContract
from tests.backend.http_api_response_schemas import (
    ACCESS_ATTEMPTS_SCHEMA,
    ANNOUNCE_SINGLE_SCHEMA,
    ANNOUNCES_LIST_SCHEMA,
    BLACKHOLE_STATUS_SCHEMA,
    BLOCKED_DESTINATIONS_ENVELOPE_SCHEMA,
    BOTS_STATUS_SCHEMA,
    BOTS_SUBPROCESS_LOG_SCHEMA,
    CHANGELOG_SCHEMA,
    COMPORTS_ENVELOPE_SCHEMA,
    COMMUNITY_INTERFACES_SCHEMA,
    CONFIG_ENVELOPE_SCHEMA,
    CSRF_ENVELOPE_SCHEMA,
    DATABASE_BACKUPS_SCHEMA,
    DATABASE_HEALTH_SCHEMA,
    DATABASE_SNAPSHOTS_SCHEMA,
    DEBUG_LOGS_SCHEMA,
    DESTINATION_DISPLAY_NAME_SCHEMA,
    DESTINATION_PATH_SCHEMA,
    DESTINATION_SIGNAL_METRICS_SCHEMA,
    DESTINATION_STAMP_INFO_SCHEMA,
    DISCOVERED_INTERFACES_SCHEMA,
    DISCOVERY_CONFIG_SCHEMA,
    RETICULUM_INSTANCE_SCHEMA,
    DOCS_SEARCH_SCHEMA,
    DOCS_STATUS_SCHEMA,
    ERROR_ENVELOPE_SCHEMA,
    FAVOURITES_SCHEMA,
    GIFS_LIST_SCHEMA,
    IDENTITIES_LIST_SCHEMA,
    IDENTITY_BACKUP_BASE32_SCHEMA,
    INTERFACE_STATS_SCHEMA,
    INTERFACES_LIST_SCHEMA,
    LICENSES_ENVELOPE_SCHEMA,
    LXMF_CONVERSATION_MESSAGES_SCHEMA,
    LXMF_CONVERSATION_PINS_SCHEMA,
    LXMF_CONVERSATIONS_SCHEMA,
    LXMF_FOLDERS_SCHEMA,
    LXMF_MESSAGE_BLOCKLIST_SCHEMA,
    LXMF_MESSAGE_URI_SCHEMA,
    LXMF_PROPAGATION_NODES_SCHEMA,
    LXMF_PROPAGATION_STATUS_SCHEMA,
    LXMF_SIEVE_FILTERS_SCHEMA,
    MAP_DRAWINGS_SCHEMA,
    MAP_MBTILES_SCHEMA,
    MAP_OFFLINE_SCHEMA,
    MEMORY_DIAGNOSTICS_SCHEMA,
    MEMORY_DIAGNOSTICS_DISABLED_SCHEMA,
    MESHCHATX_DOCS_CONTENT_SCHEMA,
    MESHCHATX_DOCS_LIST_SCHEMA,
    MESSAGE_ENVELOPE_SCHEMA,
    NOMADNET_ARCHIVES_SCHEMA,
    NOTIFICATIONS_SCHEMA,
    PAGE_NODE_DETAIL_SCHEMA,
    PAGE_NODE_FILES_SCHEMA,
    PAGE_NODE_PAGES_SCHEMA,
    PAGE_NODES_LIST_SCHEMA,
    PATH_TABLE_SCHEMA,
    REPOSITORY_SERVER_LIST_SCHEMA,
    REPOSITORY_SERVER_STATUS_SCHEMA,
    RETICULUM_CONFIG_RAW_SCHEMA,
    RNCP_STATUS_SCHEMA,
    RNCP_TRANSFER_SCHEMA,
    RNPATH_RATES_SCHEMA,
    RNPATH_TABLE_SCHEMA,
    RNPATH_TRACE_SCHEMA,
    RNSH_OUTPUT_SCHEMA,
    RNSH_SESSIONS_SCHEMA,
    RNSTATUS_SCHEMA,
    RRC_ACTIVITY_SCHEMA,
    RRC_HUBS_SCHEMA,
    RRC_MEMBERS_SCHEMA,
    RRC_MESSAGES_SCHEMA,
    RRC_SERVERS_SCHEMA,
    SERVER_SECURITY_SCHEMA,
    SPAM_KEYWORDS_SCHEMA,
    STICKER_PACK_DETAIL_SCHEMA,
    STICKER_PACKS_LIST_SCHEMA,
    STICKERS_LIST_SCHEMA,
    SYSTEM_NETWORK_INTERFACES_SCHEMA,
    TELEMETRY_HISTORY_SCHEMA,
    TELEMETRY_LATEST_SCHEMA,
    TELEMETRY_PEERS_SCHEMA,
    TELEMETRY_TRACKING_SCHEMA,
    TELEMETRY_TRUSTED_PEERS_SCHEMA,
    TELEPHONE_AUDIO_PROFILES_SCHEMA,
    TELEPHONE_CALL_SCHEMA,
    TELEPHONE_CODEC2_STATUS_SCHEMA,
    TELEPHONE_HISTORY_SCHEMA,
    TELEPHONE_RECORDINGS_SCHEMA,
    TELEPHONE_STATUS_SCHEMA,
    TOOLS_RNODE_LATEST_RELEASE_SCHEMA,
    TRANSLATOR_LANGUAGES_SCHEMA,
)

_HEX32 = "a" * 32
_HEX16 = "b" * 16
_HEX64 = "b" * 64
_NODE_ID = "1"
_ROOM = "lobby"
_HUB_ID = "1"
_SESSION_ID = "1"
_TRANSFER_ID = "1"
_PAGE_NAME = "index.mu"

HTTP_JSON_GET_CONTRACTS: tuple[HttpJsonContract, ...] = (
    HttpJsonContract("GET", "/api/v1/status", API_V1_STATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/self-test", SELF_TEST_SCHEMA),
    HttpJsonContract("GET", "/api/v1/app/info", API_V1_APP_INFO_ENVELOPE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/app/changelog", CHANGELOG_SCHEMA),
    HttpJsonContract("GET", "/api/v1/auth/status", AUTH_STATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/auth/csrf", CSRF_ENVELOPE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/server/security", SERVER_SECURITY_SCHEMA),
    HttpJsonContract("GET", "/api/v1/config", CONFIG_ENVELOPE_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/blocked-destinations", BLOCKED_DESTINATIONS_ENVELOPE_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/comports", COMPORTS_ENVELOPE_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/system/network-interfaces", SYSTEM_NETWORK_INTERFACES_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/reticulum/interfaces", INTERFACES_LIST_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/community-interfaces", COMMUNITY_INTERFACES_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/reticulum/discovery", DISCOVERY_CONFIG_SCHEMA),
    HttpJsonContract("GET", "/api/v1/reticulum/instance", RETICULUM_INSTANCE_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/reticulum/discovered-interfaces", DISCOVERED_INTERFACES_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/reticulum/config/raw", RETICULUM_CONFIG_RAW_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/reticulum/blackhole", BLACKHOLE_STATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/interface-stats", INTERFACE_STATS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/path-table", PATH_TABLE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/licenses", LICENSES_ENVELOPE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/docs/status", DOCS_STATUS_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/docs/search", DOCS_SEARCH_SCHEMA, query={"q": "reticulum"}
    ),
    HttpJsonContract("GET", "/api/v1/meshchatx-docs/list", MESHCHATX_DOCS_LIST_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/meshchatx-docs/content",
        MESHCHATX_DOCS_CONTENT_SCHEMA,
        query={"path": "en/getting-started.md"},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/repository-server/status",
        REPOSITORY_SERVER_STATUS_SCHEMA,
        allow_statuses=(200, 503),
        alt_schemas=(ERROR_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/repository-server/list",
        REPOSITORY_SERVER_LIST_SCHEMA,
        allow_statuses=(200, 503),
        alt_schemas=(ERROR_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract("GET", "/api/v1/database/health", DATABASE_HEALTH_SCHEMA),
    HttpJsonContract("GET", "/api/v1/database/snapshots", DATABASE_SNAPSHOTS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/database/backups", DATABASE_BACKUPS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/debug/logs", DEBUG_LOGS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/debug/access-attempts", ACCESS_ATTEMPTS_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/diagnostics/memory",
        MEMORY_DIAGNOSTICS_SCHEMA,
        alt_schemas=(MEMORY_DIAGNOSTICS_DISABLED_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/diagnostics/memory/heap",
        MEMORY_DIAGNOSTICS_SCHEMA,
        allow_statuses=(200, 400),
        alt_schemas=(ERROR_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/diagnostics/memory/gc",
        MEMORY_DIAGNOSTICS_SCHEMA,
        alt_schemas=(MEMORY_DIAGNOSTICS_DISABLED_SCHEMA, MESSAGE_ENVELOPE_SCHEMA),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/diagnostics/memory/referrers",
        MEMORY_DIAGNOSTICS_SCHEMA,
        allow_statuses=(200, 400),
        alt_schemas=(ERROR_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract("GET", "/api/v1/identities", IDENTITIES_LIST_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/identity/backup/base32", IDENTITY_BACKUP_BASE32_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/announce",
        ANNOUNCE_SINGLE_SCHEMA,
        query={"aspect": "lxmf.delivery"},
    ),
    HttpJsonContract("GET", "/api/v1/announces", ANNOUNCES_LIST_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/destination/{destination_hash}/path",
        DESTINATION_PATH_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/destination/{destination_hash}/custom-display-name",
        DESTINATION_DISPLAY_NAME_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/destination/{destination_hash}/lxmf-stamp-info",
        DESTINATION_STAMP_INFO_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/destination/{destination_hash}/signal-metrics",
        DESTINATION_SIGNAL_METRICS_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract("GET", "/api/v1/notifications", NOTIFICATIONS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/favourites", FAVOURITES_SCHEMA),
    HttpJsonContract("GET", "/api/v1/nomadnet/archives", NOMADNET_ARCHIVES_SCHEMA),
    HttpJsonContract("GET", "/api/v1/page-nodes", PAGE_NODES_LIST_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/page-nodes/{node_id}",
        PAGE_NODE_DETAIL_SCHEMA,
        match_info={"node_id": _NODE_ID},
        allow_statuses=(200, 404),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/page-nodes/{node_id}/files",
        PAGE_NODE_FILES_SCHEMA,
        match_info={"node_id": _NODE_ID},
        allow_statuses=(200, 404),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/page-nodes/{node_id}/pages",
        PAGE_NODE_PAGES_SCHEMA,
        match_info={"node_id": _NODE_ID},
        allow_statuses=(200, 404),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/page-nodes/{node_id}/pages/{page_name}",
        PAGE_NODE_DETAIL_SCHEMA,
        match_info={"node_id": _NODE_ID, "page_name": _PAGE_NAME},
        allow_statuses=(200, 404),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract("GET", "/api/v1/lxmf/conversations", LXMF_CONVERSATIONS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/lxmf/folders", LXMF_FOLDERS_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/lxmf/conversation-pins", LXMF_CONVERSATION_PINS_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/lxmf/sieve-filters", LXMF_SIEVE_FILTERS_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/lxmf/message-blocklist", LXMF_MESSAGE_BLOCKLIST_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/lxmf/propagation-nodes", LXMF_PROPAGATION_NODES_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/lxmf/propagation-node/status", LXMF_PROPAGATION_STATUS_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/lxmf-messages/conversation/{destination_hash}",
        LXMF_CONVERSATION_MESSAGES_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/lxmf-messages/{message_hash}/uri",
        LXMF_MESSAGE_URI_SCHEMA,
        match_info={"message_hash": _HEX64},
        allow_statuses=(200, 404, 422),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract("GET", "/api/v1/gifs", GIFS_LIST_SCHEMA),
    HttpJsonContract("GET", "/api/v1/stickers", STICKERS_LIST_SCHEMA),
    HttpJsonContract("GET", "/api/v1/sticker-packs", STICKER_PACKS_LIST_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/sticker-packs/{pack_id}",
        STICKER_PACK_DETAIL_SCHEMA,
        match_info={"pack_id": _NODE_ID},
    ),
    HttpJsonContract("GET", "/api/v1/map/drawings", MAP_DRAWINGS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/map/offline", MAP_OFFLINE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/map/mbtiles", MAP_MBTILES_SCHEMA),
    HttpJsonContract("GET", "/api/v1/telemetry/peers", TELEMETRY_PEERS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/telemetry/tracking", TELEMETRY_TRACKING_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/telemetry/trusted-peers", TELEMETRY_TRUSTED_PEERS_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telemetry/latest/{destination_hash}",
        TELEMETRY_LATEST_SCHEMA,
        match_info={"destination_hash": _HEX32},
        allow_statuses=(200, 404),
        alt_schemas=(ERROR_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telemetry/history/{destination_hash}",
        TELEMETRY_HISTORY_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract("GET", "/api/v1/rrc/hubs", RRC_HUBS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/rrc/servers", RRC_SERVERS_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/rrc/hubs/{hub_hash}/rooms/{room}/messages",
        RRC_MESSAGES_SCHEMA,
        match_info={"hub_hash": _HEX32, "room": _ROOM},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/rrc/servers/{hub_id}/members",
        RRC_MEMBERS_SCHEMA,
        match_info={"hub_id": _HUB_ID},
        allow_statuses=(200, 404),
        alt_schemas=(MESSAGE_ENVELOPE_SCHEMA,),
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/rrc/servers/{hub_id}/activity",
        RRC_ACTIVITY_SCHEMA,
        match_info={"hub_id": _HUB_ID},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/rrc/servers/{hub_id}/messages",
        RRC_MESSAGES_SCHEMA,
        match_info={"hub_id": _HUB_ID},
    ),
    HttpJsonContract("GET", "/api/v1/rncp/status", RNCP_STATUS_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/rncp/transfer/{transfer_id}",
        RNCP_TRANSFER_SCHEMA,
        match_info={"transfer_id": _TRANSFER_ID},
    ),
    HttpJsonContract("GET", "/api/v1/rnpath/table", RNPATH_TABLE_SCHEMA),
    HttpJsonContract("GET", "/api/v1/rnpath/rates", RNPATH_RATES_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/rnpath/trace/{destination_hash}",
        RNPATH_TRACE_SCHEMA,
        match_info={"destination_hash": _HEX32},
    ),
    HttpJsonContract("GET", "/api/v1/rnsh/sessions", RNSH_SESSIONS_SCHEMA),
    HttpJsonContract(
        "GET",
        "/api/v1/rnsh/sessions/{session_id}/output",
        RNSH_OUTPUT_SCHEMA,
        match_info={"session_id": _SESSION_ID},
    ),
    HttpJsonContract("GET", "/api/v1/rnstatus", RNSTATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/bots/status", BOTS_STATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/bots/subprocess-log", BOTS_SUBPROCESS_LOG_SCHEMA),
    HttpJsonContract("GET", "/api/v1/spam-keywords", SPAM_KEYWORDS_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/translator/languages", TRANSLATOR_LANGUAGES_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/tools/rnode/latest_release", TOOLS_RNODE_LATEST_RELEASE_SCHEMA
    ),
    HttpJsonContract("GET", "/api/v1/telephone/status", TELEPHONE_STATUS_SCHEMA),
    HttpJsonContract("GET", "/api/v1/telephone/history", TELEPHONE_HISTORY_SCHEMA),
    HttpJsonContract(
        "GET", "/api/v1/telephone/recordings", TELEPHONE_RECORDINGS_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/telephone/audio-profiles", TELEPHONE_AUDIO_PROFILES_SCHEMA
    ),
    HttpJsonContract(
        "GET", "/api/v1/telephone/codec2/status", TELEPHONE_CODEC2_STATUS_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telephone/call/{identity_hash}",
        TELEPHONE_CALL_SCHEMA,
        match_info={"identity_hash": _HEX32},
    ),
    HttpJsonContract(
        "GET", "/api/v1/telephone/voicemail/status", TELEPHONE_VOICEMAIL_STATUS_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telephone/voicemails",
        TELEPHONE_VOICEMAILS_ENVELOPE_SCHEMA,
        query={"limit": "50", "offset": "0"},
    ),
    HttpJsonContract(
        "GET", "/api/v1/telephone/ringtones", TELEPHONE_RINGTONES_LIST_SCHEMA
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telephone/ringtones/status",
        TELEPHONE_RINGTONE_STATUS_SCHEMA,
        query={},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telephone/contacts",
        TELEPHONE_CONTACTS_LIST_SCHEMA,
        query={"limit": "100", "offset": "0"},
    ),
    HttpJsonContract(
        "GET",
        "/api/v1/telephone/contacts/check/{identity_hash}",
        TELEPHONE_CONTACT_CHECK_SCHEMA,
        match_info={"identity_hash": _HEX16},
    ),
)

HTTP_JSON_GET_CONTRACT_EXCLUDED: tuple[str, ...] = (
    "/api/v1/database/backup/download",
    "/api/v1/database/backups/{filename}/download",
    "/api/v1/database/snapshots/{filename}/download",
    "/api/v1/docs/export",
    "/api/v1/docs/export/reticulum",
    "/api/v1/identity/backup/download",
    "/api/v1/identities/export-all",
    "/api/v1/maintenance/messages/export",
    "/api/v1/bots/export",
    "/api/v1/gifs/export",
    "/api/v1/lxmf/folders/export",
    "/api/v1/lxmf/message-blocklist/export",
    "/api/v1/stickers/export",
    "/api/v1/sticker-packs/{pack_id}/export",
    "/api/v1/telephone/contacts/export",
    "/api/v1/tools/rnode/download_firmware",
    "/api/v1/tools/micron-parser-go-release",
    "/api/v1/lxmf-messages/attachment/{message_hash}/{attachment_type}",
    "/api/v1/gifs/{gif_id}/image",
    "/api/v1/stickers/{sticker_id}/image",
    "/api/v1/map/tiles/{z}/{x}/{y}",
    "/api/v1/map/export/{export_id}",
    "/api/v1/map/export/{export_id}/download",
    "/api/v1/telephone/recordings/{id}/audio/{side}",
    "/api/v1/telephone/ringtones/{id}/audio",
    "/api/v1/telephone/voicemail/greeting/audio",
    "/api/v1/telephone/voicemails/{id}/audio",
    "/api/v1/telephone/answer",
    "/api/v1/telephone/hangup",
    "/api/v1/telephone/send-to-voicemail",
    "/api/v1/telephone/mute-transmit",
    "/api/v1/telephone/mute-receive",
    "/api/v1/telephone/unmute-transmit",
    "/api/v1/telephone/unmute-receive",
    "/api/v1/telephone/switch-audio-profile/{profile_id}",
    "/api/v1/lxmf/propagation-node/sync",
    "/api/v1/lxmf/propagation-node/stop-sync",
    "/api/v1/ping/{destination_hash}/lxmf.delivery",
)

_HTTP_JSON_GET_EXCLUDED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/download$"),
    re.compile(r"/export$"),
    re.compile(r"/image$"),
    re.compile(r"/audio"),
    re.compile(r"/tiles/"),
)


def is_excluded_json_get_route(path: str) -> bool:
    if path in HTTP_JSON_GET_CONTRACT_EXCLUDED:
        return True
    return any(pattern.search(path) for pattern in _HTTP_JSON_GET_EXCLUDED_PATTERNS)


def registered_get_paths() -> set[str]:
    return {contract.path for contract in HTTP_JSON_GET_CONTRACTS}
