# SPDX-License-Identifier: 0BSD

"""Additional JSON Schema definitions for broad HTTP API contract tests."""

from __future__ import annotations

_OBJECT = {"type": "object", "additionalProperties": True}
_ARRAY = {"type": "array"}
_STRING = {"type": "string"}
_INTEGER = {"type": "integer"}
_BOOLEAN = {"type": "boolean"}
_NUMBER = {"type": "number"}

ERROR_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["error"],
    "properties": {"error": _STRING},
    "additionalProperties": True,
}

MESSAGE_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["message"],
    "properties": {"message": _STRING},
    "additionalProperties": True,
}

MAINTENANCE_MESSAGES_PURGE_PREVIEW_SCHEMA: dict = {
    "type": "object",
    "required": ["count", "cutoff"],
    "properties": {
        "count": {"type": "integer", "minimum": 0},
        "cutoff": _NUMBER,
    },
    "additionalProperties": False,
}

MAINTENANCE_MESSAGES_DUPLICATES_SCHEMA: dict = {
    "type": "object",
    "required": ["count"],
    "properties": {
        "count": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

CONFIG_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["config"],
    "properties": {"config": _OBJECT},
    "additionalProperties": False,
}

BLOCKED_DESTINATIONS_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["blocked_destinations"],
    "properties": {
        "blocked_destinations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["destination_hash", "created_at"],
                "properties": {
                    "destination_hash": _STRING,
                    "created_at": _STRING,
                },
                "additionalProperties": True,
            },
        },
    },
    "additionalProperties": False,
}

SERVER_SECURITY_SCHEMA: dict = {
    "type": "object",
    "required": [
        "listen_host",
        "listen_port",
        "https_enabled",
        "is_loopback_bind",
        "web_ui_ip_allowlist",
        "privacy_mode_enabled",
        "auth_enabled",
    ],
    "properties": {
        "listen_host": {"type": ["string", "null"]},
        "listen_port": {"type": ["integer", "null"]},
        "https_enabled": _BOOLEAN,
        "is_loopback_bind": _BOOLEAN,
        "web_ui_ip_allowlist": _STRING,
        "privacy_mode_enabled": _BOOLEAN,
        "auth_enabled": _BOOLEAN,
    },
    "additionalProperties": True,
}

CSRF_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["csrf_token"],
    "properties": {"csrf_token": _STRING},
    "additionalProperties": False,
}

COMPORTS_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["comports"],
    "properties": {"comports": _ARRAY},
    "additionalProperties": False,
}

INTERFACES_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["interfaces"],
    "properties": {"interfaces": {"type": ["object", "array"]}},
    "additionalProperties": True,
}

COMMUNITY_INTERFACES_SCHEMA: dict = {
    "type": "object",
    "required": ["interfaces"],
    "properties": {"interfaces": _ARRAY},
    "additionalProperties": True,
}

IDENTITIES_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["identities"],
    "properties": {"identities": _ARRAY},
    "additionalProperties": True,
}

LICENSES_ENVELOPE_SCHEMA: dict = {
    "type": "object",
    "required": ["backend", "frontend", "meta"],
    "properties": {
        "backend": _ARRAY,
        "frontend": _ARRAY,
        "meta": _OBJECT,
    },
    "additionalProperties": True,
}

DOCS_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["status"],
    "properties": {"status": _STRING},
    "additionalProperties": True,
}

DOCS_SEARCH_SCHEMA: dict = {
    "type": "object",
    "required": ["results"],
    "properties": {"results": _ARRAY},
    "additionalProperties": True,
}

MESHCHATX_DOCS_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["docs"],
    "properties": {"docs": _ARRAY},
    "additionalProperties": True,
}

MESHCHATX_DOCS_CONTENT_SCHEMA: dict = {
    "type": "object",
    "required": ["content"],
    "properties": {"content": _STRING},
    "additionalProperties": True,
}

DATABASE_HEALTH_SCHEMA: dict = {
    "type": "object",
    "required": ["database"],
    "properties": {"database": _OBJECT},
    "additionalProperties": True,
}

DATABASE_SNAPSHOTS_SCHEMA: dict = {
    "type": "object",
    "required": ["snapshots"],
    "properties": {"snapshots": _ARRAY},
    "additionalProperties": True,
}

DATABASE_BACKUPS_SCHEMA: dict = {
    "type": "object",
    "required": ["backups"],
    "properties": {"backups": _ARRAY},
    "additionalProperties": True,
}

DEBUG_LOGS_SCHEMA: dict = {
    "type": "object",
    "required": ["logs"],
    "properties": {"logs": _ARRAY},
    "additionalProperties": True,
}

ACCESS_ATTEMPTS_SCHEMA: dict = {
    "type": "object",
    "required": ["attempts"],
    "properties": {"attempts": _ARRAY},
    "additionalProperties": True,
}

MEMORY_DIAGNOSTICS_SCHEMA: dict = {
    "type": "object",
    "required": ["rss_bytes"],
    "properties": {"rss_bytes": _INTEGER},
    "additionalProperties": True,
}

MEMORY_DIAGNOSTICS_DISABLED_SCHEMA: dict = {
    "type": "object",
    "required": ["enabled"],
    "properties": {
        "enabled": _BOOLEAN,
        "message": _STRING,
    },
    "additionalProperties": True,
}

DISCOVERY_CONFIG_SCHEMA: dict = {
    "type": "object",
    "required": ["discovery"],
    "properties": {"discovery": _OBJECT},
    "additionalProperties": True,
}

RETICULUM_INSTANCE_SCHEMA: dict = {
    "type": "object",
    "required": ["instance"],
    "properties": {
        "instance": {
            "type": "object",
            "required": [
                "share_instance",
                "local_hops_delta",
                "is_connected_to_shared_instance",
            ],
            "properties": {
                "share_instance": _BOOLEAN,
                "local_hops_delta": _BOOLEAN,
                "respond_to_probes": _BOOLEAN,
                "enable_remote_management": _BOOLEAN,
                "remote_management_allowed": _ARRAY,
                "shared_instance_type": {},
                "instance_name": {},
                "rpc_key": {},
                "rpc_config_snippet": {},
                "is_connected_to_shared_instance": _BOOLEAN,
                "enable_transport": _BOOLEAN,
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

DISCOVERED_INTERFACES_SCHEMA: dict = {
    "type": "object",
    "required": ["interfaces"],
    "properties": {"interfaces": _ARRAY},
    "additionalProperties": True,
}

RETICULUM_CONFIG_RAW_SCHEMA: dict = {
    "type": "object",
    "required": ["content"],
    "properties": {
        "content": _STRING,
        "path": _STRING,
    },
    "additionalProperties": True,
}

BLACKHOLE_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["blackholed_identities"],
    "properties": {
        "blackholed_identities": {"type": ["object", "array"]},
        "enabled": _BOOLEAN,
    },
    "additionalProperties": True,
}

INTERFACE_STATS_SCHEMA: dict = {
    "type": "object",
    "required": ["interface_stats"],
    "properties": {"interface_stats": _OBJECT},
    "additionalProperties": True,
}

PATH_TABLE_SCHEMA: dict = {
    "type": "object",
    "required": ["path_table"],
    "properties": {
        "path_table": _ARRAY,
        "total_count": _INTEGER,
    },
    "additionalProperties": True,
}

LXMF_CONVERSATIONS_SCHEMA: dict = {
    "type": "object",
    "required": ["conversations"],
    "properties": {"conversations": _ARRAY},
    "additionalProperties": True,
}

LXMF_FOLDERS_SCHEMA: dict = {
    "type": "array",
    "items": _OBJECT,
}

LXMF_CONVERSATION_PINS_SCHEMA: dict = {
    "type": "object",
    "required": ["peer_hashes"],
    "properties": {"peer_hashes": _ARRAY, "pins": _ARRAY},
    "additionalProperties": True,
}

LXMF_SIEVE_FILTERS_SCHEMA: dict = {
    "type": "object",
    "required": ["filters"],
    "properties": {"filters": _ARRAY},
    "additionalProperties": True,
}

LXMF_MESSAGE_BLOCKLIST_SCHEMA: dict = {
    "type": "object",
    "required": ["enabled", "blocklist"],
    "properties": {
        "enabled": _BOOLEAN,
        "blocklist": {
            "type": "object",
            "required": ["entries"],
            "properties": {
                "entries": _ARRAY,
                "scope": _STRING,
                "match_peer_fields": _BOOLEAN,
                "match_message": _BOOLEAN,
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

LXMF_PROPAGATION_NODES_SCHEMA: dict = {
    "type": "object",
    "required": ["lxmf_propagation_nodes"],
    "properties": {"lxmf_propagation_nodes": _ARRAY, "nodes": _ARRAY},
    "additionalProperties": True,
}

LXMF_PROPAGATION_STATUS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

NOTIFICATIONS_SCHEMA: dict = {
    "type": "object",
    "required": ["notifications"],
    "properties": {"notifications": _ARRAY},
    "additionalProperties": True,
}

FAVOURITES_SCHEMA: dict = {
    "type": "object",
    "required": ["favourites"],
    "properties": {"favourites": _ARRAY},
    "additionalProperties": True,
}

PAGE_NODES_LIST_SCHEMA: dict = {
    "type": "array",
    "items": _OBJECT,
}

PAGE_NODE_DETAIL_SCHEMA: dict = {
    "type": "object",
    "required": ["node"],
    "properties": {"node": _OBJECT},
    "additionalProperties": True,
}

PAGE_NODE_FILES_SCHEMA: dict = {
    "type": "object",
    "required": ["files"],
    "properties": {"files": _ARRAY},
    "additionalProperties": True,
}

PAGE_NODE_PAGES_SCHEMA: dict = {
    "type": "object",
    "required": ["pages"],
    "properties": {"pages": _ARRAY},
    "additionalProperties": True,
}

NOMADNET_ARCHIVES_SCHEMA: dict = {
    "type": "object",
    "required": ["archives"],
    "properties": {"archives": _ARRAY},
    "additionalProperties": True,
}

GIFS_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["gifs"],
    "properties": {"gifs": _ARRAY},
    "additionalProperties": True,
}

STICKERS_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["stickers"],
    "properties": {"stickers": _ARRAY},
    "additionalProperties": True,
}

STICKER_PACKS_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["packs"],
    "properties": {"packs": _ARRAY},
    "additionalProperties": True,
}

STICKER_PACK_DETAIL_SCHEMA: dict = {
    "type": "object",
    "required": ["pack"],
    "properties": {"pack": _OBJECT},
    "additionalProperties": True,
}

MAP_DRAWINGS_SCHEMA: dict = {
    "type": "object",
    "required": ["drawings"],
    "properties": {"drawings": _ARRAY},
    "additionalProperties": True,
}

MAP_OFFLINE_SCHEMA: dict = {
    "type": "object",
    "required": ["loaded"],
    "properties": {"loaded": _BOOLEAN, "tiles": _ARRAY},
    "additionalProperties": True,
}

MAP_MBTILES_SCHEMA: dict = {
    "type": "array",
    "items": _OBJECT,
}

MAP_DATA_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": [
        "aspect",
        "running",
        "destination_hash",
        "display_name",
        "announce_enabled",
        "announce_interval",
        "max_bytes",
        "published_count",
    ],
    "properties": {
        "aspect": _STRING,
        "running": _BOOLEAN,
        "destination_hash": {"type": ["string", "null"]},
        "display_name": _STRING,
        "announce_enabled": _BOOLEAN,
        "announce_interval": _INTEGER,
        "max_bytes": _INTEGER,
        "published_count": _INTEGER,
    },
    "additionalProperties": True,
}

MAP_DATA_PUBLISHED_SCHEMA: dict = {
    "type": "object",
    "required": ["maps"],
    "properties": {"maps": _ARRAY},
    "additionalProperties": True,
}

MAP_DATA_HEARD_SCHEMA: dict = {
    "type": "object",
    "required": ["announces"],
    "properties": {"announces": _ARRAY},
    "additionalProperties": True,
}

TELEMETRY_PEERS_SCHEMA: dict = {
    "type": "object",
    "required": ["telemetry"],
    "properties": {"telemetry": _ARRAY, "peers": _ARRAY},
    "additionalProperties": True,
}

TELEMETRY_TRACKING_SCHEMA: dict = {
    "type": "object",
    "required": ["tracked_peers"],
    "properties": {"tracked_peers": _ARRAY, "tracking": _ARRAY},
    "additionalProperties": True,
}

TELEMETRY_TRUSTED_PEERS_SCHEMA: dict = {
    "type": "object",
    "required": ["trusted_peers"],
    "properties": {"trusted_peers": _ARRAY},
    "additionalProperties": True,
}

TELEMETRY_LATEST_SCHEMA: dict = {
    "type": "object",
    "required": ["telemetry"],
    "properties": {"telemetry": {"type": ["object", "null"]}},
    "additionalProperties": True,
}

TELEMETRY_HISTORY_SCHEMA: dict = {
    "type": "object",
    "required": ["telemetry"],
    "properties": {"telemetry": _ARRAY, "history": _ARRAY},
    "additionalProperties": True,
}

RRC_HUBS_SCHEMA: dict = {
    "type": "object",
    "required": ["hubs"],
    "properties": {"hubs": _ARRAY},
    "additionalProperties": True,
}

RRC_SERVERS_SCHEMA: dict = {
    "type": "object",
    "required": ["hubs"],
    "properties": {"hubs": _ARRAY},
    "additionalProperties": True,
}

RRC_MESSAGES_SCHEMA: dict = {
    "type": "object",
    "required": ["messages"],
    "properties": {"messages": _ARRAY},
    "additionalProperties": True,
}

RRC_MEMBERS_SCHEMA: dict = {
    "type": "object",
    "required": ["members"],
    "properties": {"members": _ARRAY},
    "additionalProperties": True,
}

RRC_ACTIVITY_SCHEMA: dict = {
    "type": "object",
    "required": ["activity"],
    "properties": {"activity": _ARRAY},
    "additionalProperties": True,
}

RRC_ROOM_KEYS_SCHEMA: dict = {
    "type": "object",
    "required": ["keys"],
    "properties": {"keys": _ARRAY},
    "additionalProperties": True,
}

RNCP_STATUS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

FILESYNC_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["running", "sync_directory"],
    "properties": {
        "running": _BOOLEAN,
        "sync_directory": _STRING,
        "identity_hash": {"type": ["string", "null"]},
        "destination_hash": {"type": ["string", "null"]},
        "peers": _INTEGER,
        "files": _INTEGER,
        "whitelist": _BOOLEAN,
        "monitor": _BOOLEAN,
        "announce_interval": _INTEGER,
        "config_directory": _STRING,
        "storage_directory": _STRING,
    },
    "additionalProperties": True,
}

FILESYNC_PEERS_SCHEMA: dict = {
    "type": "object",
    "required": ["peers"],
    "properties": {"peers": _ARRAY},
    "additionalProperties": True,
}

FILESYNC_FILES_SCHEMA: dict = {
    "type": "object",
    "required": ["files"],
    "properties": {"files": _ARRAY},
    "additionalProperties": True,
}

FILESYNC_DIRECTORIES_SCHEMA: dict = {
    "type": "object",
    "required": ["ok", "root", "current", "directories"],
    "properties": {
        "ok": _BOOLEAN,
        "root": _STRING,
        "current": _STRING,
        "parent": {"type": ["string", "null"]},
        "directories": _ARRAY,
    },
    "additionalProperties": True,
}

FILESYNC_TREE_SCHEMA: dict = {
    "type": "object",
    "required": ["ok", "root", "current", "entries"],
    "properties": {
        "ok": _BOOLEAN,
        "root": _STRING,
        "current": _STRING,
        "parent": {"type": ["string", "null"]},
        "entries": _ARRAY,
    },
    "additionalProperties": True,
}

FILESYNC_ACL_SCHEMA: dict = {
    "type": "object",
    "required": ["enforce", "rules"],
    "properties": {
        "enforce": _BOOLEAN,
        "rules": _OBJECT,
    },
    "additionalProperties": True,
}

RNCP_TRANSFER_SCHEMA: dict = {
    "type": "object",
    "required": ["transfer"],
    "properties": {"transfer": {"type": ["object", "null"]}},
    "additionalProperties": True,
}

RNPATH_TABLE_SCHEMA: dict = {
    "type": "object",
    "required": ["table"],
    "properties": {"table": _ARRAY},
    "additionalProperties": True,
}

RNPATH_RATES_SCHEMA: dict = {
    "type": "object",
    "required": ["rates"],
    "properties": {"rates": _ARRAY},
    "additionalProperties": True,
}

RNPATH_TRACE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

RNSH_SESSIONS_SCHEMA: dict = {
    "type": "object",
    "required": ["sessions"],
    "properties": {"sessions": _ARRAY},
    "additionalProperties": True,
}

RNSH_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["output"],
    "properties": {"output": _STRING},
    "additionalProperties": True,
}

RNX_SESSIONS_SCHEMA: dict = {
    "type": "object",
    "required": ["sessions"],
    "properties": {"sessions": _ARRAY},
    "additionalProperties": True,
}

RNX_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["chunks", "next_cursor"],
    "properties": {
        "chunks": _ARRAY,
        "next_cursor": {"type": "integer"},
    },
    "additionalProperties": True,
}

RNSTATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["interfaces"],
    "properties": {"interfaces": _ARRAY},
    "additionalProperties": True,
}

BOTS_STATUS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

BOTS_SUBPROCESS_LOG_SCHEMA: dict = {
    "type": "object",
    "required": ["log"],
    "properties": {"log": _STRING},
    "additionalProperties": True,
}

SPAM_KEYWORDS_SCHEMA: dict = {
    "type": "object",
    "required": ["spam_keywords"],
    "properties": {"spam_keywords": _ARRAY, "keywords": _ARRAY},
    "additionalProperties": True,
}

SYSTEM_NETWORK_INTERFACES_SCHEMA: dict = {
    "type": "object",
    "required": ["interfaces"],
    "properties": {"interfaces": _ARRAY},
    "additionalProperties": True,
}

TRANSLATOR_LANGUAGES_SCHEMA: dict = {
    "type": "object",
    "required": ["languages"],
    "properties": {"languages": _ARRAY},
    "additionalProperties": True,
}

TOOLS_MICRON_PARSER_RELEASE_SCHEMA: dict = {
    "type": "object",
    "required": ["release"],
    "properties": {"release": _STRING},
    "additionalProperties": True,
}

TOOLS_RNODE_LATEST_RELEASE_SCHEMA: dict = {
    "type": "object",
    "required": ["release"],
    "properties": {"release": _OBJECT},
    "additionalProperties": True,
}

REPOSITORY_SERVER_STATUS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

REPOSITORY_SERVER_LIST_SCHEMA: dict = {
    "type": "array",
    "items": _OBJECT,
}

ANNOUNCE_SINGLE_SCHEMA: dict = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": _STRING,
        "announce": {"type": ["object", "null"]},
    },
    "additionalProperties": True,
}

ANNOUNCES_LIST_SCHEMA: dict = {
    "type": "object",
    "required": ["announces"],
    "properties": {"announces": _ARRAY},
    "additionalProperties": True,
}

DESTINATION_PATH_SCHEMA: dict = {
    "type": "object",
    "required": ["path"],
    "properties": {"path": {"type": ["object", "null"]}},
    "additionalProperties": True,
}

DESTINATION_DISPLAY_NAME_SCHEMA: dict = {
    "type": "object",
    "required": ["custom_display_name"],
    "properties": {"custom_display_name": {"type": ["string", "null"]}},
    "additionalProperties": True,
}

DESTINATION_STAMP_INFO_SCHEMA: dict = {
    "type": "object",
    "required": ["lxmf_stamp_info"],
    "properties": {
        "lxmf_stamp_info": {
            "type": "object",
            "required": ["stamp_cost", "outbound_ticket_expiry"],
            "properties": {
                "stamp_cost": {"type": ["integer", "null"]},
                "outbound_ticket_expiry": {"type": ["number", "null"]},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}

DESTINATION_SIGNAL_METRICS_SCHEMA: dict = {
    "type": "object",
    "required": ["signal_metrics"],
    "properties": {
        "signal_metrics": {"type": ["object", "null"]},
        "metrics": {"type": ["object", "null"]},
    },
    "additionalProperties": True,
}

LXMF_CONVERSATION_MESSAGES_SCHEMA: dict = {
    "type": "object",
    "required": ["lxmf_messages"],
    "properties": {"lxmf_messages": _ARRAY, "messages": _ARRAY},
    "additionalProperties": True,
}

LXMF_MESSAGE_URI_SCHEMA: dict = {
    "type": "object",
    "required": ["uri"],
    "properties": {"uri": _STRING},
    "additionalProperties": True,
}

IDENTITY_BACKUP_BASE32_SCHEMA: dict = {
    "type": "object",
    "required": ["identity_base32"],
    "properties": {"identity_base32": _STRING},
    "additionalProperties": True,
}

CHANGELOG_SCHEMA: dict = {
    "type": "object",
    "required": ["changelog"],
    "properties": {"changelog": _STRING},
    "additionalProperties": True,
}

ACTIVE_SESSIONS_SCHEMA: dict = {
    "type": "object",
    "required": ["count", "sessions", "warning", "warning_enabled"],
    "properties": {
        "count": {"type": "integer", "minimum": 0},
        "sessions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "ip", "user_agent", "connected_at"],
                "properties": {
                    "id": _STRING,
                    "ip": _STRING,
                    "user_agent": _STRING,
                    "connected_at": _NUMBER,
                },
                "additionalProperties": True,
            },
        },
        "warning": _BOOLEAN,
        "warning_enabled": _BOOLEAN,
    },
    "additionalProperties": False,
}

TELEPHONE_STATUS_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}

TELEPHONE_HISTORY_SCHEMA: dict = {
    "type": "object",
    "required": ["call_history"],
    "properties": {"call_history": _ARRAY, "history": _ARRAY},
    "additionalProperties": True,
}

TELEPHONE_RECORDINGS_SCHEMA: dict = {
    "type": "object",
    "required": ["recordings"],
    "properties": {"recordings": _ARRAY},
    "additionalProperties": True,
}

TELEPHONE_AUDIO_PROFILES_SCHEMA: dict = {
    "type": "object",
    "required": ["audio_profiles"],
    "properties": {
        "audio_profiles": _ARRAY,
        "default_audio_profile_id": _INTEGER,
    },
    "additionalProperties": True,
}

TELEPHONE_CALL_MODES_SCHEMA: dict = {
    "type": "object",
    "required": ["call_modes"],
    "properties": {
        "call_modes": _ARRAY,
        "default_call_mode_id": _INTEGER,
    },
    "additionalProperties": True,
}

TELEPHONE_CODEC2_STATUS_SCHEMA: dict = {
    "type": "object",
    "required": ["codec2_available"],
    "properties": {
        "codec2_available": {"type": "boolean"},
        "preload_error": {"type": ["string", "null"]},
        "probe_error": {"type": ["string", "null"]},
        "platform": {"type": "string"},
        "preferred_profile_id": {"type": ["integer", "null"]},
        "resolved_profile_id": {"type": ["integer", "null"]},
    },
    "additionalProperties": True,
}

TELEPHONE_CALL_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
}
